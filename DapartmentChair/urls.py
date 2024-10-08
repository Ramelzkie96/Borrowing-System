from django.urls import path 
from django.conf import settings 
from django.conf.urls.static import static 
from django.shortcuts import redirect 
from . import views
from django.contrib.auth import views as auth_views 
from .views import CustomPasswordResetView


urlpatterns = [
    path('', lambda request: redirect('login/'), name='home_redirect'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logoutUser, name='logout'),
    path('admin-logout/', views.adminlogout, name='admin-logout'),
    path('dashboard/', views.faculty_required(views.faculty), name='dashboard'),
    path('password-reset/', CustomPasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('admin-dashboard/', views.admin_dashboard, name='admin-dashboard'),
    path('admin-users/', views.admin_users, name='admin-users'),
    path('admin-addusers/', views.create_user, name='add-users'),
    path('edit-user/', views.edit_user, name='edit-user'),
    path('delete-user/', views.delete_user, name='delete_user'),
    path('admin-return-item/', views.return_item, name='admin-return-item'),
    path('admin-send-email/', views.send_email_notification, name='admin-send_email'),
    path('admin-add-item/', views.add_item, name='admin-add-item'),
    path('admin-item-record/', views.item_record, name='admin-item-record'),
    path('admin-edit', views.update_item, name="admin-update_item"),
    path('admin-delete-item/<int:item_id>/', views.delete_item, name='admin-delete_item'),
] 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


