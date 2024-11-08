from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('reservation-dashboard', views.reservation_dashboard, name='reservation-dashboard'),
    path('reservation-login', views.reservation_login, name='reservation-login'),
    path('reservation-register', views.reservation_register, name='reservation-register'),
    path('reservation-logout/', views.logout, name='reservation-logout'),
    path('submit-reservation/', views.submit_reservation, name='submit_reservation'),
    path('reservation-status/', views.reservation_status, name='reservation-status'),
    path('mark-notifications-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('reservation-change-profile/', views.changeprofile, name='reservation-change-profile'),
    path('reservation-change-password/', views.changepassword, name='reservation-change-password'),
    path('delete-notification/', views.delete_notification, name='delete_notification'),
    path('reservation-forgot-password/', views.reservation_forgot_password, name='reservation-forgot-password'),
    path('reservation-reset-password/<uidb64>/<token>/', views.reset_password, name='reservation-reset_password'),
    path('get-faculty-items/', views.get_faculty_items, name='get_faculty_items'),
    path('api/reservation-items/<str:reserve_date>/', views.reservation_items, name='reservation-items'),
    path('reservation-edit/<int:reservation_id>/', views.reservation_edit, name='reservation-edit'),
    path('get-available-stock/<int:item_id>/', views.get_available_stock, name='get-available-stock'),
    path('reservation-update/', views.reservation_update, name='reservation-update')
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
