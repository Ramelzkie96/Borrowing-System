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
    path('admin-update-user-status/', views.update_user_status, name='admin-update-user-status'),
    path('admin-return-item/', views.return_item, name='admin-return-item'),
    path('admin-update-borrower-status/', views.update_borrower_status, name='admin-update_borrower_status'),
    path('admin-update-borrower-status-dash/', views.update_borrower_status_dashboard, name='admin-update_borrower_status_dashboard'),
    path('admin-send-email/', views.send_email_notification, name='admin-send_email'),
    path('admin-add-item/', views.add_item, name='admin-add-item'),
    path('admin-item-record/', views.item_record, name='admin-item-record'),
    path('admin-edit', views.update_item, name="admin-update_item"),
    path('admin-delete-item/<int:item_id>/', views.delete_item, name='admin-delete_item'),
    path('admin-borrowers', views.borrowers, name='admin-borrowers'),
    path('admin-search-borrow-request/', views.search_borrow_request, name='admin-search_borrow_request'),
    path('admin-proceed-borrow/<int:reservation_id>/', views.proceed_borrow, name='admin-proceed-borrow'),
    path('admin-save-reservation-request/', views.save_reservation_request, name='admin-save_reservation_request'),
    
    path('admin-borrow-record/', views.borrow_record, name='admin-borrow-record'),
    path('admin-borrower-details/', views.borrower_details, name='admin-borrower-details'),
    path('admin-borrower-details-dash/', views.borrower_details_dashboard, name='admin-borrower-details-dashboard'),
    path('admin-update-borrower/', views.fetch_borrow_request, name='admin-update-borrower'),
    path('admin-save-borrower-update/', views.save_borrow_update, name='admin-save-borrower-update'),
    path('admin-get-unreturned-items/<int:borrow_id>/', views.get_unreturned_items, name='admin-get-unreturned-items'),
    path('admin-borrower-report/<str:id>/', views.generate_report, name='admin-borrower-report'),
    path('admin-fetch_borrow_request_items/', views.fetch_borrow_request_items, name='admin-fetch_borrow_request_items'),
    path('admin-student-reservation/', views.admin_student_reservation, name='admin-student-reservation'),
    path('admin-change-profile', views.change_profile, name='admin-change-profile'),
    path('admin-change-password', views.change_password, name='admin-change-password'),
    path('admin-get-available-quantity/<int:item_id>/', views.get_available_quantity, name='admin-get_available_quantity'),
    path('admin-update-reservation-status/<int:reservation_id>/', views.status_update, name='admin-update-reservation-status'),
    path('admin-update-reservation-item-status/', views.update_reservation_item_status, name='admin-update_reservation_item_status'),
    
    
    path('delete-borrow-request/<int:borrow_request_id>/', views.delete_borrow_request, name='delete-borrow-request'),
    
    path('delete-reservation/<int:reservation_id>/', views.delete_reservation, name='delete_reservation'),
    
    
    path('aa-update-student-reservation/', views.aa_update_student_reservation, name='aa-update_student_reservation'),
    path('get_property_ids/<int:item_id>/', views.get_property_ids, name='get_property_ids'),
    path('update-property-status/', views.update_property_status, name='update-property-status'),
    
] 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


