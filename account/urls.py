from django.urls import path # type: ignore
from django.conf import settings # type: ignore
from django.conf.urls.static import static # type: ignore
from django.shortcuts import redirect # type: ignore
from . import views
from django.contrib.auth import views as auth_views # type: ignore
from .views import CustomPasswordResetView


urlpatterns = [
    path('', lambda request: redirect('login/'), name='home_redirect'),  # Redirect root URL to login
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logoutUser, name='logout'),
    path('dashboard/', views.faculty_required(views.faculty), name='dashboard'),
    path('password-reset/', CustomPasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
]

# Add the following line to serve media files during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


