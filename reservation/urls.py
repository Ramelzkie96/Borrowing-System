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
    # path('mark-as-read/<int:reservation_id>/', views.mark_as_read, name='mark_as_read'),
 
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
