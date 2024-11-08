from django.urls import path # type: ignore
from . import views

urlpatterns = [
   path('add-item', views.add_item, name="add-item"),
   path('items-record', views.item_record, name="item-record"),
   path('edit', views.update_item, name="update_item"),
   path('delete-item/<int:item_id>/', views.delete_item, name='delete_item'),
   path('borrowers', views.borrowers, name='borrowers'),
   path('borrow-record', views.borrow_record, name='borrow-record'),
   path('send-email/', views.send_email_notification, name='send_email'),

   path('change-profile', views.change_profile, name='change-profile'),
   path('change-password', views.change_password, name='change-password'),
   path('student-reservation', views.student_reservation, name='student-reservation'),
   path('update-reservation-status/', views.update_reservation_status, name='update_reservation_status'),
   path('borrower-report/<str:id>/', views.generate_report, name='borrower-report'),
   
   path('borrower-details/', views.borrower_details, name='borrower-details'),
  path('fetch_borrow_request_items/', views.fetch_borrow_request_items, name='fetch_borrow_request_items'),
    path('update-borrower/', views.fetch_borrow_request, name='update-borrower'),
    path('update-borrower-status/', views.update_borrower_status, name='update_borrower_status'),
    path('return-item/', views.return_item, name='return-item'),
    path('save-borrower-update/', views.save_borrow_update, name='save-borrower-update'),
    path('get-unreturned-items/<int:borrow_id>/', views.get_unreturned_items, name='get-unreturned-items'),
    path('get-available-quantity/<int:item_id>/', views.get_available_quantity, name='get_available_quantity'),
    path('search-borrow-request/', views.search_borrow_request, name='search_borrow_request'),
]
