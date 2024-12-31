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
   path('borrower-report/<str:id>/', views.generate_report, name='borrower-report'),
   
   path('borrower-details/', views.borrower_details, name='borrower-details'),
  path('fetch_borrow_request_items/', views.fetch_borrow_request_items, name='fetch_borrow_request_items'),
  path('fetch_borrow_request_items_record/', views.fetch_borrow_request_items_record, name='fetch_borrow_request_items_record'),
    path('update-borrower/', views.fetch_borrow_request, name='update-borrower'),
    path('update-borrower-status/', views.update_borrower_status, name='update_borrower_status'),
    path('return-item/', views.return_item, name='return-item'),
    path('save-borrower-update/', views.save_borrow_update, name='save-borrower-update'),
    path('get-unreturned-items/<int:borrow_id>/', views.get_unreturned_items, name='get-unreturned-items'),
    path('get-available-quantity/<int:item_id>/', views.get_available_quantity, name='get_available_quantity'),
    path('search-borrow-request/', views.search_borrow_request, name='search_borrow_request'),
    path('update-reservation-status/<int:reservation_id>/', views.status_update, name='update-reservation-status'),
    path('update-reservation-item-status/', views.update_reservation_item_status, name='update_reservation_item_status'),
    path('proceed-borrow/<int:reservation_id>/', views.proceed_borrow, name='proceed-borrow'),
    path('save-reservation-request/', views.save_reservation_request, name='save_reservation_request'),
    path('get_property_ids/<int:item_id>/', views.get_property_ids, name='get_property_ids'),
    path('update-property-status/', views.update_property_status, name='update-property-status'),

    
 
    
]
