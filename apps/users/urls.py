from django.urls import path
from . import views, test_views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # /api/users/ 直接作为用户列表入口：该 urls 模块同时挂在 api/auth/ 与 api/users/ 下，
    # 列表原位于 users/ 子路径，导致 /api/users/ 返回 404，故补充根路由别名
    path('', views.UserListView.as_view()),
    path('me/', views.get_current_user, name='get_current_user'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('test-register/', test_views.test_register, name='test-register'),  # 测试注册接口
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('manage/', views.admin_user_manage, name='admin-user-manage'),
    path('manage/<int:user_id>/', views.admin_user_update, name='admin-user-update'),
    path('manage/<int:user_id>/reset-password/', views.admin_reset_password, name='admin-reset-password'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # JWT token刷新
    path('captcha/', views.get_captcha, name='get_captcha'),                    # 图形验证码
    path('send-register-code/', views.send_register_code, name='send_register_code'),  # 发送注册验证码
    path('sms-login/', views.sms_login_view, name='sms_login'),                 # 短信验证码登录
    path('exchange-token/', views.exchange_token_view, name='exchange_token'),  # SSO 授权码交换
]