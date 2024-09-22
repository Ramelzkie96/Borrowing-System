from django.urls import path # type: ignore
from . import views

urlpatterns = [
   path('add-item', views.add_item, name="add-item"),
   path('items-record', views.item_record, name="item-record"),
   path('edit', views.update_item, name="update_item"),
   path('delete-item/<int:item_id>/', views.delete_item, name='delete_item'),
   path('borrowers', views.borrowers, name='borrowers'),
   path('borrow-record', views.borrow_record, name='borrow-record'),
   path('borrow-more-item/', views.borrow_more_item, name='borrow_more_item'),
   path('update-borrow-request/', views.update_borrow_request, name='update_borrow_request'),
   path('return-item/', views.return_item, name='return-item'),
   path('send-email/', views.send_email_notification, name='send_email'),
   path('returned-record', views.returned_record, name="returned-record"),
   path('change-profile', views.change_profile, name='change-profile'),
   path('change-password', views.change_password, name='change-password'),
   path('student-reservation', views.student_reservation, name='student-reservation'),
   path('update-reservation-status/', views.update_reservation_status, name='update_reservation_status'),
   path('borrower-report/<str:student_id>/', views.generate_report, name='borrower-report'),
]
