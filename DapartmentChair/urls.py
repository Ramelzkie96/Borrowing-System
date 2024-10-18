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
    path('update-user-status/', views.update_user_status, name='update-user-status'),
    path('admin-return-item/', views.return_item, name='admin-return-item'),
    path('admin-send-email/', views.send_email_notification, name='admin-send_email'),
    path('admin-add-item/', views.add_item, name='admin-add-item'),
    path('admin-item-record/', views.item_record, name='admin-item-record'),
    path('admin-edit', views.update_item, name="admin-update_item"),
    path('admin-delete-item/<int:item_id>/', views.delete_item, name='admin-delete_item'),
    path('admin-borrowers', views.borrowers, name='admin-borrowers'),
    path('admin-borrow-record', views.borrow_record, name='admin-borrow-record'),
    path('admin-borrow-more-item/', views.borrow_more_item, name='admin-borrow_more_item'),
    path('admin-borrower-report/<str:student_id>/', views.generate_report, name='admin-borrower-report'),
    path('admin-returned-record/', views.returned_record, name="admin-returned-record"),
    path('admin-student-reservation/', views.admin_student_reservation, name='admin-student-reservation'),
    path('admin-update-reservation-status/', views.update_reservation_status, name='admin-update_reservation_status'),
    path('admin-change-profile', views.change_profile, name='admin-change-profile'),
    path('admin-change-password', views.change_password, name='admin-change-password'),
] 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


