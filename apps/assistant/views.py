from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
import requests
from .models import AssistantSession, AssistantMessage, ChatMessage, DifyConfig
from .serializers import (
    AssistantSessionSerializer, 
    AssistantSessionCreateSerializer,
    AssistantMessageSerializer,
    ChatMessageSerializer
)


class AssistantSessionViewSet(viewsets.ModelViewSet):
    """智能助手会话视图集"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AssistantSessionCreateSerializer
        return AssistantSessionSerializer
    
    def get_queryset(self):
        return AssistantSession.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """添加消息到会话"""
        session = self.get_object()
        serializer = AssistantMessageSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(session=session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """获取会话的聊天消息"""
        session = self.get_object()
        messages = session.chat_messages.all()
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)


class ChatViewSet(viewsets.ViewSet):
    """聊天功能ViewSet"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def send_message(self, request):
        """发送消息到Dify API"""
        session_id = request.data.get('session_id')
        message = request.data.get('message')
        
        if not session_id or not message:
            return Response(
                {'error': 'session_id和message都是必填项'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取会话
        try:
            session = AssistantSession.objects.get(
                session_id=session_id,
                user=request.user
            )
        except AssistantSession.DoesNotExist:
            return Response(
                {'error': '会话不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 保存用户消息
        user_message = ChatMessage.objects.create(
            session=session,
            role='user',
            content=message,
            conversation_id=session.conversation_id
        )

        # 优先使用 requirement_analysis 的活跃 AI 模型配置（OpenAI 兼容，支持本地/在线模型）
        try:
            from apps.requirement_analysis.models import AIModelConfig, AIModelService
            active_config = AIModelConfig.objects.filter(is_active=True).order_by('-id').first()
        except Exception:
            active_config = None
        if active_config:
            try:
                headers = AIModelService.get_openai_compatible_headers(active_config.api_key)
                url = AIModelService.build_openai_compatible_url(active_config.base_url, '/chat/completions')
                payload = {
                    'model': active_config.model_name,
                    'messages': [
                        {'role': 'system', 'content': '你是TestHub的AI测试测评师，请专业、准确、简洁地回答软件测试相关问题。'},
                        {'role': 'user', 'content': message}
                    ],
                    'max_tokens': active_config.max_tokens,
                    'temperature': active_config.temperature,
                    'top_p': active_config.top_p,
                    'stream': False
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    content = ''
                    try:
                        content = data['choices'][0]['message']['content']
                    except Exception:
                        content = data.get('answer', '')
                    assistant_message = ChatMessage.objects.create(
                        session=session,
                        role='assistant',
                        content=content or '',
                        conversation_id=session.conversation_id
                    )
                    return Response({
                        'user_message': ChatMessageSerializer(user_message).data,
                        'assistant_message': ChatMessageSerializer(assistant_message).data,
                        'conversation_id': session.conversation_id
                    })
                return Response({'error': f'AI模型API错误: {resp.status_code}', 'detail': resp.text},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except requests.exceptions.Timeout:
                return Response({'error': 'AI模型API请求超时'}, status=status.HTTP_408_REQUEST_TIMEOUT)
            except requests.exceptions.RequestException as e:
                return Response({'error': f'AI模型API请求失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({'error': f'AI模型调用失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 回退：Dify 协议
        dify_config = DifyConfig.get_active_config()
        if not dify_config:
            return Response(
                {'error': '未配置Dify API，且未启用AI模型配置，请在配置中心配置'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 调用Dify API
            headers = {
                'Authorization': f'Bearer {dify_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'inputs': {},
                'query': message,
                'user': str(request.user.id),
                'response_mode': 'blocking'
            }
            
            # 如果有conversation_id，添加到请求中以保持会话连续性
            if session.conversation_id:
                payload['conversation_id'] = session.conversation_id
            
            # 去除URL末尾的斜杠
            api_url = dify_config.api_url.rstrip('/')
            
            response = requests.post(
                f'{api_url}/chat-messages',
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 更新会话的conversation_id
                if 'conversation_id' in data and not session.conversation_id:
                    session.conversation_id = data['conversation_id']
                    session.save()
                
                # 保存助手回复
                assistant_message = ChatMessage.objects.create(
                    session=session,
                    role='assistant',
                    content=data.get('answer', ''),
                    conversation_id=data.get('conversation_id'),
                    message_id=data.get('message_id')
                )
                
                return Response({
                    'user_message': ChatMessageSerializer(user_message).data,
                    'assistant_message': ChatMessageSerializer(assistant_message).data,
                    'conversation_id': data.get('conversation_id')
                })
            else:
                return Response({
                    'error': f'Dify API错误: {response.status_code}',
                    'detail': response.text
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except requests.exceptions.Timeout:
            return Response({
                'error': 'API请求超时'
            }, status=status.HTTP_408_REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({
                'error': f'API请求失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def assistant_view(request):
    """智能助手页面视图 - 用于iframe内嵌"""
    return render(request, 'assistant/assistant.html')
