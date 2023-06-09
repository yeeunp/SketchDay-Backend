from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenRefreshView, # refresh 토큰으로 access 토큰을 재발급하는 뷰
)

urlpatterns = [
    path('login', views.UserLoginAPI.as_view(), name='login_view'),
    path('logout', views.UserLogoutAPI.as_view(), name='logout_view'),
    path('signup', views.signup_view, name='signup_view'),
    path('sendEmail', views.signup_send_verification_code, name='send_verification_code'),
    path('verifyEmail', views.signup_verify_code, name='verify_code'),
    path('help/findPW/checkEmail', views.find_password_send_verification_code, name='find_pw_send_verification_code'),
    path('help/findPW/verifyEmail', views.find_password_verify_code, name='find_pw_verify_code'),
    path('help/resetPW/verifyPW', views.reset_password_verify, name='reset_password_verify'),
    path('help/resetPW', views.reset_password, name='reset_password'),
    path('deleteUser', views.delete_user, name='delete_user'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
