from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import User
from .serializers import UserSerializer, UserCreateSerializer, LoginSerializer

# JWT 相关导入
from rest_framework_simplejwt.tokens import RefreshToken

# 图形验证码 & 短信验证码
from .captcha import create_captcha
from .sms import send_register_verify_code, validate_verify_code
from .redis_client import get_redis
import re
import uuid

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 安全地创建token
        try:
            from rest_framework.authtoken.models import Token
            token, created = Token.objects.get_or_create(user=user)
            token_key = token.key
        except ImportError:
            token_key = f"temp_token_{user.id}"
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token_key
        }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    login(request, user)

    # JWT Token (优先使用JWT)
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    return Response({
        'user': UserSerializer(user).data,
        'access': access_token,       # JWT access token
        'refresh': refresh_token,     # JWT refresh token
        'message': '登录成功'
    })

@api_view(['POST'])
@csrf_exempt
def logout_view(request):
    """用户退出登录，将refresh token加入黑名单"""
    if request.user.is_authenticated:
        # 将 refresh token 加入黑名单
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken
                JWTRefreshToken(refresh_token).blacklist()
            except Exception:
                pass

        logout(request)

    return Response({'message': '退出成功'})

@api_view(['GET'])
def profile_view(request):
    if not request.user.is_authenticated:
        return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
    
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

class UserListView(generics.ListCreateAPIView):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


# ========== 超级管理员：用户与权限管理 ==========

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_user_manage(request):
    """用户与权限管理：仅超级管理员。

    - GET  : 用户列表（含角色、启禁用状态）。
    - POST : 新增用户（可指定是否超管）。
    """
    if not request.user.is_superuser:
        return Response({'error': '仅超级管理员可管理用户'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'POST':
        from .serializers import AdminUserCreateSerializer
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(_admin_user_payload(user), status=status.HTTP_201_CREATED)

    users = User.objects.all().order_by('-is_superuser', 'username')
    return Response([_admin_user_payload(u) for u in users])


@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def admin_user_update(request, user_id):
    """更新用户资料 / 系统角色 / 启禁用。仅超级管理员。"""
    if not request.user.is_superuser:
        return Response({'error': '仅超级管理员可管理用户'}, status=status.HTTP_403_FORBIDDEN)

    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data

    # 保护：不能取消自己的超管权限
    if target.pk == request.user.pk and data.get('is_superuser') is False:
        return Response({'error': '不能取消自己的超级管理员权限'}, status=status.HTTP_400_BAD_REQUEST)
    # 保护：不能禁用自己
    if target.pk == request.user.pk and data.get('is_active') is False:
        return Response({'error': '不能禁用当前登录账号'}, status=status.HTTP_400_BAD_REQUEST)
    # 保护：至少保留一个超管
    if target.is_superuser and data.get('is_superuser') is False:
        if User.objects.filter(is_superuser=True).count() <= 1:
            return Response({'error': '至少保留一个超级管理员'}, status=status.HTTP_400_BAD_REQUEST)

    from .serializers import AdminUserUpdateSerializer
    serializer = AdminUserUpdateSerializer(
        target,
        data=data,
        partial=True
    )
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(_admin_user_payload(user))


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_reset_password(request, user_id):
    """重置用户密码。仅超级管理员。"""
    if not request.user.is_superuser:
        return Response({'error': '仅超级管理员可重置密码'}, status=status.HTTP_403_FORBIDDEN)

    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

    password = request.data.get('password')
    if not password or len(str(password)) < 6:
        return Response({'error': '新密码至少6位'}, status=status.HTTP_400_BAD_REQUEST)

    target.set_password(str(password))
    target.save(update_fields=['password'])
    return Response({'message': '密码已重置'})


def _admin_user_payload(user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone': user.phone,
        'department': user.department,
        'position': user.position,
        'is_active': user.is_active,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
    }


# ========== 图形验证码 & 短信验证码 ==========

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_captcha(request):
    """获取图形验证码"""
    result = create_captcha()
    return Response(result)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def send_register_code(request):
    """发送短信验证码（注册/登录通用）"""
    phone = request.data.get('phone', '').strip()
    captcha_token = request.data.get('captcha_token', '')
    captcha_code = request.data.get('captcha_code', '')
    mode = request.data.get('mode', 'register')  # 'register' 或 'login'

    if not phone:
        return Response({'success': False, 'error': '请输入手机号'}, status=status.HTTP_400_BAD_REQUEST)
    if not captcha_token or not captcha_code:
        return Response({'success': False, 'error': '请输入图形验证码'}, status=status.HTTP_400_BAD_REQUEST)

    # 登录模式：校验手机号是否已注册
    if mode == 'login':
        if not User.objects.filter(phone=phone).exists():
            return Response({'success': False, 'error': '该手机号未注册，请先注册'}, status=status.HTTP_400_BAD_REQUEST)

    # 注册模式：校验手机号未被注册
    if mode == 'register':
        if User.objects.filter(phone=phone).exists():
            return Response({'success': False, 'error': '该手机号已被注册'}, status=status.HTTP_400_BAD_REQUEST)

    result = send_register_verify_code(phone, captcha_token, captcha_code)

    if result.get('success'):
        return Response(result)
    else:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def sms_login_view(request):
    """短信验证码登录：校验短信码 → 返回 JWT（未注册提示用户先注册）"""
    phone = request.data.get('phone', '').strip()
    verify_code = request.data.get('verify_code', '').strip()
    verify_code_token = request.data.get('verify_code_token', '').strip()

    # 校验手机号
    if not phone:
        return Response({'error': '请输入手机号'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.match(r'^1[3-9]\d{9}$', phone):
        return Response({'error': '手机号格式不正确'}, status=status.HTTP_400_BAD_REQUEST)

    # 校验短信验证码
    if not verify_code or not verify_code_token:
        return Response({'error': '请输入短信验证码'}, status=status.HTTP_400_BAD_REQUEST)

    valid, error = validate_verify_code(phone, verify_code_token, verify_code)
    if not valid:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

    # 查找用户
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response({'error': '该手机号未注册，请先注册'}, status=status.HTTP_400_BAD_REQUEST)

    if not user.is_active:
        return Response({'error': '用户已被禁用'}, status=status.HTTP_400_BAD_REQUEST)

    # 生成 JWT
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    return Response({
        'user': UserSerializer(user).data,
        'access': access_token,
        'refresh': refresh_token,
        'message': '登录成功',
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def exchange_token_view(request):
    """
    一次性授权码交换
    action=create:  用当前 JWT 换取一次性 code（需登录），60 秒有效
    action=redeem:  用 code 换取 JWT（无需登录），一次性使用
    """
    action = request.data.get('action', '')
    redis_client = get_redis()

    if action == 'create':
        if not request.user.is_authenticated:
            return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
        code = str(uuid.uuid4()).replace('-', '')[:8]
        redis_client.setex(f"exchange:{code}", 60, request.user.id)
        return Response({'code': code})

    elif action == 'redeem':
        code = request.data.get('code', '').strip()
        if not code:
            return Response({'error': '缺少授权码'}, status=status.HTTP_400_BAD_REQUEST)

        user_id = redis_client.get(f"exchange:{code}")
        if user_id is None:
            return Response({'error': '授权码无效或已过期'}, status=status.HTTP_400_BAD_REQUEST)

        # 立即删除，保证一次性使用
        redis_client.delete(f"exchange:{code}")

        try:
            user = User.objects.get(id=int(user_id))
        except User.DoesNotExist:
            return Response({'error': '用户不存在'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            return Response({'error': '用户已被禁用'}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })

    else:
        return Response({'error': '无效的 action'}, status=status.HTTP_400_BAD_REQUEST)