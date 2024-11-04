from django.core.paginator import Paginator 
from django.shortcuts import render, redirect, get_object_or_404 
from .models import facultyItem
from django.contrib import messages 
from django.http import JsonResponse  
from .models import BorrowRequest, facultyItem, BorrowRequestItem
from .forms import BorrowRequestMultimediaForm
from django.views.decorators.http import require_POST  
from django.core.mail import send_mail 
from django.views.decorators.csrf import csrf_exempt  
from .forms import EmailNotificationForm
from django.conf import settings 
from django.contrib.contenttypes.models import ContentType  
from reservation.models import StudentReservation
from django.contrib.auth.decorators import login_required  
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash  
import os
from django.templatetags.static import static
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django.utils import timezone 
from datetime import datetime
from django.utils.timezone import now
import pdfkit
from django.db.models import Q 
from django.http import HttpResponse
from django.template.loader import render_to_string
import json
from django.db import transaction
from django.db.models import Max, Count




@login_required
def add_item(request):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')  # Retrieve the description field
        quantity = request.POST.get('quantity')

        # Ensure all fields are filled
        if name and description and quantity:
            # No need to check if an item with the same name already exists
            # Create the new item and associate it with the current user
            facultyItem.objects.create(
                name=name,
                description=description,
                quantity=quantity,
                user_id=request.user.id  # Associate the item with the current user's ID
            )
            messages.success(request, 'SUCCESS! Item has been added successfully.')
            return redirect('item-record')  # Redirect to item_record after adding item
        else:
            messages.error(request, 'ERROR! Please fill out all fields.')

        # Pass the submitted data back to the template in case of an error
        return render(request, 'add-item.html', {'name': name, 'description': description, 'quantity': quantity})

    return render(request, 'add-item.html')



@login_required
def item_record(request):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Get only items that belong to the logged-in user
    items = facultyItem.objects.filter(user_id=request.user.id).order_by('-id')
    total_items = items.count()

    # Handle pagination based on 'show' parameter
    show_entries = request.GET.get('show', 'all')
    if show_entries == 'all':
        paginator = Paginator(items, 1000000)  # Show all items
        current_show = 'all'
    else:
        paginator = Paginator(items, int(show_entries))
        current_show = int(show_entries)

    # Get the current page number and the page object
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'item-record.html', {'page_obj': page_obj, 'total_items': total_items, 'current_show': current_show})

@login_required
def update_item(request):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        name = request.POST.get('name')
        description = request.POST.get('description')
        quantity = request.POST.get('quantity')

        # Retrieve the item and ensure it belongs to the current user
        item = get_object_or_404(facultyItem, id=item_id)

        if item.user_id != request.user.id:  # Ensure the item belongs to the current user
            messages.error(request, "You are not authorized to update this item.")
            return redirect('item-record')

        # Update item details
        item.name = name
        item.description = description
        item.quantity = quantity
        item.save()

        messages.success(request, 'SUCCESS! Item has been updated successfully.')
        return redirect('item-record')

    return redirect('item-record')


@login_required
def delete_item(request, item_id):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    if request.method == 'POST':
        item = get_object_or_404(facultyItem, id=item_id)
        item.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)





@login_required
def borrowers(request):
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")

    multimedia_items = facultyItem.objects.filter(user=request.user)
    items = list(multimedia_items)

    has_available_items = any(item.quantity > 0 for item in items)

    form = BorrowRequestMultimediaForm(user=request.user)

    if request.method == 'POST':
        content_type = ContentType.objects.get_for_model(facultyItem)
        student_id = request.POST.get('student_id')
        date_borrow = request.POST.get('date_borrow')

        try:
            date_borrow_parsed = datetime.strptime(date_borrow, "%d %B, %Y").date()

            if date_borrow_parsed < now().date():
                messages.error(request, 'ERROR! Date Borrow cannot be set to a past date.')
            else:
                borrow_request = BorrowRequest.objects.filter(
                    student_id=student_id,
                    date_borrow=date_borrow
                ).exclude(status='Returned').first()

                borrower_type = request.POST.get('borrower_type')
                if borrower_type not in ['Student', 'Teacher']:
                    other_borrower_type = request.POST.get('other_borrower_type')
                    if other_borrower_type:
                        borrower_type = other_borrower_type

                if not borrow_request:
                    borrow_request = BorrowRequest(
                        student_id=student_id,
                        name=request.POST.get('name'),
                        course=request.POST.get('course'),
                        year=request.POST.get('year'),
                        email=request.POST.get('email'),
                        phone=request.POST.get('phone'),
                        date_borrow=date_borrow,
                        date_return=None,
                        status='Borrowed',
                        note=request.POST.get('note', ''),
                        user=request.user,
                        borrower_type=borrower_type,
                        content_type=content_type,
                        object_id=0,
                        upload_image=request.FILES.get('upload_image')
                    )
                    borrow_request.save()

                items_borrowed = request.POST.getlist('item')
                quantities_borrowed = request.POST.getlist('quantities[]')

                # Begin transaction
                with transaction.atomic():
                    for item_id, quantity in zip(items_borrowed, quantities_borrowed):
                        selected_item = facultyItem.objects.get(id=item_id)
                        requested_quantity = int(quantity)

                        # Backend quantity validation
                        if requested_quantity > selected_item.quantity:
                            messages.error(
                                request,
                                f"ERROR! Not enough '{selected_item.name}' available. Requested: {requested_quantity}, Available: {selected_item.quantity}."
                            )
                            return redirect('borrowers')  # Redirect back to form

                        borrow_request_item = BorrowRequestItem.objects.filter(
                            borrow_request=borrow_request,
                            item=selected_item,
                            is_returned=False
                        ).first()

                        if borrow_request_item:
                            borrow_request_item.quantityy += requested_quantity
                            borrow_request_item.save()
                        else:
                            BorrowRequestItem.objects.create(
                                borrow_request=borrow_request,
                                item=selected_item,
                                quantityy=requested_quantity,
                                is_returned=False,
                                handled_by=request.user  # Set handled_by to the current user here
                            )

                        selected_item.quantity -= requested_quantity
                        selected_item.save()

                messages.success(request, 'SUCCESS! Borrow requests have been submitted.')
                return redirect('borrow-record')

        except ValueError:
            messages.error(request, 'ERROR! Invalid date format. Please use DD MMMM, YYYY format (e.g., 29 October, 2024).')

    return render(request, 'borrowers.html', {
        'form': form,
        'multimedia_items': multimedia_items,
        'has_available_items': has_available_items,
    })







@login_required
def borrow_record(request):
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Fetch latest borrow request per unique combination of student_id and date_borrow,
    # filtering by handled_by in BorrowRequestItem
    borrow_requests = (BorrowRequest.objects
                       .filter(items__handled_by=request.user)  # Use related name 'items' to filter
                       .exclude(status__in=["Returned", "Returned/Defect Item"])
                       .values('student_id', 'date_borrow')
                       .annotate(latest_id=Max('id'))
                       .order_by('-date_borrow', '-student_id'))

    # Retrieve actual BorrowRequest objects using latest_id from the previous query
    latest_requests = BorrowRequest.objects.filter(id__in=[item['latest_id'] for item in borrow_requests])
    
    # Order the latest requests by id in descending order to show the latest first
    latest_requests = latest_requests.order_by('-id')

    total_borrow_requests = latest_requests.count()

    # Fetch all items from facultyItem model associated with the logged-in user
    user_items = facultyItem.objects.filter(user=request.user)

    # Pagination setup
    show_entries = request.GET.get('show', 'all')
    if show_entries == 'all':
        paginator = Paginator(latest_requests, 1000000)
        current_show = 'all'
    else:
        paginator = Paginator(latest_requests, int(show_entries))
        current_show = int(show_entries)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'borrow-record.html', {
        'page_obj': page_obj,
        'total_borrow_requests': total_borrow_requests,
        'current_show': current_show,
        'items': user_items,
    })




    

# im taking rest not modify yet
@login_required
def borrower_details(request):
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")

    # Retrieve request data from URL parameters
    student_id = request.GET.get('student_id')
    name = request.GET.get('name')  # Retrieve name from URL
    date_borrow = request.GET.get('date_borrow')

    # Fetch all BorrowRequest records with matching student_id and date_borrow
    borrow_requests = BorrowRequest.objects.filter(
        student_id=student_id,
        date_borrow=date_borrow,
        status='Borrowed'  # Filter for status 'Borrowed'
    )

    if not borrow_requests.exists():
        return render(request, '404.html', status=404)  # Or a suitable not-found response

    # Retrieve all related BorrowRequestItems for each BorrowRequest
    borrow_requests_with_items = [
        {
            'borrow_request': borrow_request,
            'items': borrow_request.items.all()
        }
        for borrow_request in borrow_requests
    ]

    # Pass the data to the template context
    context = {
        'student_id': student_id,
        'name': name,  # Add name to the context
        'date_borrow': date_borrow,
        'borrow_requests_with_items': borrow_requests_with_items,
    }
    return render(request, 'borrower-details.html', context)











def fetch_borrow_request_items(request):
    if request.method == 'GET':
        request_id = request.GET.get('request_id')
        items = BorrowRequestItem.objects.filter(borrow_request_id=request_id).select_related('item')

        item_list = [
            {
                'item_name': borrow_item.item.name,  # Assuming 'name' is the field you want to display
                'quantity': borrow_item.quantityy,
                'date_return': borrow_item.date_return.strftime('%d %B, %Y') if borrow_item.date_return else None,
            }
            for borrow_item in items
        ]

        return JsonResponse({'items': item_list})

    return JsonResponse({'error': 'Invalid request'}, status=400)



def search_borrow_request(request):
    student_id = request.GET.get('student_id')

    if student_id:
        # Query the BorrowRequest model for the student_id
        borrow_request = BorrowRequest.objects.filter(student_id=student_id).last()  # Get the first matching record

        if borrow_request:
            data = {
                'success': True,
                'name': borrow_request.name,
                'course': borrow_request.course,
                'year': borrow_request.year,
                'email': borrow_request.email,
                'phone': borrow_request.phone,
                'borrower_type': borrow_request.borrower_type,
                'date_borrow': borrow_request.date_borrow,  # Add this line to return the date
            }
            return JsonResponse(data)

    # Return a response indicating no record was found
    return JsonResponse({'success': False, 'error': 'No record found.'}, status=404)



@login_required
def fetch_borrow_request(request):
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")

    # Get the BorrowRequest instance
    borrow_request_id = request.GET.get('id')
    borrow_request = get_object_or_404(BorrowRequest, id=borrow_request_id)

    # Filter items that are not returned
    items = borrow_request.items.select_related('item').filter(is_returned=False)

    # Prepare context for displaying in the template
    context = {
        'borrow_request_id': borrow_request_id,
        'student_id': borrow_request.student_id,
        'name': borrow_request.name,
        'course': borrow_request.course,
        'year': borrow_request.year,
        'email': borrow_request.email,
        'phone': borrow_request.phone,
        'date_borrow': borrow_request.date_borrow,
        'purpose': borrow_request.purpose,
        'borrower_type': borrow_request.borrower_type,
        'items': items,  # Only items that are not returned
    }

    return render(request, 'update-borrow-request.html', context)


@csrf_exempt  # Optional, remove if not necessary for production
def update_borrower_status(request):
    if request.method == "POST":
        borrow_request_id = request.POST.get("borrow_request_id")
        status = "Returned"  # Set the status to Returned

        try:
            borrow_request = BorrowRequest.objects.get(id=borrow_request_id)
            borrow_request.status = status  # Update the status
            
            # Reset created_at to the current time
            borrow_request.created_at = timezone.now()  
            
            borrow_request.save()

            # Add a success message
            messages.success(request, "Borrower status updated to Returned.")
            return redirect('borrow-record')  # Redirect after successful update

        except BorrowRequest.DoesNotExist:
            messages.error(request, "BorrowRequest not found.")
            return redirect('borrower-details')  # Redirect on error

    messages.error(request, "Invalid request method.")
    return redirect('borrower-details')  # Redirect on invalid request method



@csrf_exempt
def return_item(request):
    if request.method == "POST":
        data = json.loads(request.body)
        item_id = data.get("item_id")
        borrow_request_item_id = data.get("borrow_request_item_id")
        date_return = data.get("date_return")

        try:
            borrow_item = BorrowRequestItem.objects.get(id=borrow_request_item_id)
            faculty_item = facultyItem.objects.get(id=item_id)

            # Update BorrowRequestItem fields
            borrow_item.date_return = date_return
            borrow_item.is_returned = True  # Mark as returned
            borrow_item.save()

            # Update facultyItem quantity
            faculty_item.quantity += borrow_item.quantityy
            faculty_item.save()

            return JsonResponse({"success": True})

        except BorrowRequestItem.DoesNotExist:
            return JsonResponse({"success": False, "error": "BorrowRequestItem not found."})
        except facultyItem.DoesNotExist:
            return JsonResponse({"success": False, "error": "facultyItem not found."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method."})




@login_required
def save_borrow_update(request):
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")

    if request.method == 'POST':
        # Get the BorrowRequest instance
        borrow_request_id = request.POST.get('id')
        borrow_request = get_object_or_404(BorrowRequest, id=borrow_request_id)

        # Update the borrow request data
        borrow_request.student_id = request.POST.get('student_id')
        borrow_request.name = request.POST.get('name')
        borrow_request.course = request.POST.get('course')
        borrow_request.year = request.POST.get('year')
        borrow_request.email = request.POST.get('email')
        borrow_request.phone = request.POST.get('phone')
        borrow_request.purpose = request.POST.get('description')
        date_borrow = request.POST.get('datepicker')
        borrow_request.date_borrow = date_borrow

        # Update borrower_type, considering the "Others" option if provided
        borrower_type = request.POST.get('borrower_type')
        if borrower_type not in ["Student", "Teacher"]:
            borrower_type = request.POST.get('other_borrower_type')  # Use the "Others" field if applicable
        borrow_request.borrower_type = borrower_type

        borrow_request.save()

        # Handle the item and quantity updates only if necessary
        item_id = request.POST.get('itemm')
        try:
            borrow_item = borrow_request.items.get(item_id=item_id)
            quantity_input = request.POST.get('quantityy')

            if quantity_input:  # Ensure quantity input is provided
                quantity = int(quantity_input)
                
                # Only update if the new quantity is different
                if quantity != borrow_item.quantityy:
                    # Get the available quantity from facultyItem
                    faculty_item = borrow_item.item
                    available_quantity = faculty_item.quantity

                    # Validate the requested quantity against available stock
                    if quantity > available_quantity + borrow_item.quantityy:
                        messages.error(request, "The requested quantity exceeds the available stock.")
                        return redirect('update-borrower', id=borrow_request_id)

                    # Calculate the difference in quantity only if it's an increase
                    quantity_difference = quantity - borrow_item.quantityy

                    # Update the BorrowRequestItem
                    borrow_item.quantityy = quantity
                    borrow_item.save()

                    # Update the available quantity in facultyItem
                    faculty_item.quantity -= quantity_difference
                    faculty_item.save()

        except BorrowRequestItem.DoesNotExist:
            # Skip updating if the BorrowRequestItem does not exist
            pass

        messages.success(request, 'SUCCESS! Borrow requests have been updated successfully.')
        return redirect('borrow-record')

    return HttpResponseBadRequest("Invalid request method.")



@login_required
def get_available_quantity(request, item_id):
    try:
        item = facultyItem.objects.get(id=item_id, user=request.user)
        return JsonResponse({"available_quantity": item.quantity})
    except facultyItem.DoesNotExist:
        return JsonResponse({"available_quantity": 0})




@csrf_exempt
def send_email_notification(request):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    if request.method == 'POST':
        form = EmailNotificationForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            email = form.cleaned_data['email']
            message_content = form.cleaned_data['message']
            
            try:
                send_mail(
                    title,
                    message_content,
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )
                # Add a success message and redirect
                messages.success(request, 'Email sent successfully.')
                return redirect('borrow-record')  # Use the direct URL
            except Exception as e:
                # Add an error message and redirect
                messages.error(request, f'Error sending email: {str(e)}')
                return redirect('borrow-record')  # Use the direct URL
        else:
            # Add an error message for invalid form data and redirect
            messages.error(request, 'Invalid form data.')
            return redirect('borrow-record')  # Use the direct URL
    
    # Handle cases where the request method is not POST
    messages.error(request, 'Invalid request method.')
    return redirect('borrow-record')  # Use the direct URL


def get_unreturned_items(request, borrow_id):
    try:
        borrow_request = BorrowRequest.objects.get(id=borrow_id)
        unreturned_items = borrow_request.items.filter(is_returned=False)
        items_list = [
            {
                'name': item.item.name,
                'quantity': item.quantityy
            }
            for item in unreturned_items
        ]

        return JsonResponse({'success': True, 'items': items_list})
    except BorrowRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Borrow request not found.'})
    
    


@login_required
def returned_record(request):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Fetch returned requests handled by or created by the current user
    # Fetch all returned requests handled by or created by the user
    returned_requests = BorrowRequest.objects.filter(
        Q(user=request.user),
        status='Returned'  # Only filter for the Returned status
    ).order_by('-id')  # Order by id in descending order

    # Pagination setup
    show_entries = request.GET.get('show', 'all')
    if show_entries == 'all':
        paginator = Paginator(returned_requests, 1000000)  # Show all records
        current_show = 'all'
    else:
        paginator = Paginator(returned_requests, int(show_entries))
        current_show = int(show_entries)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'returned-record.html', {
        'page_obj': page_obj,
        'current_show': current_show,
        'returned_requests': returned_requests,
    })
    
@login_required
def change_profile(request):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    user = request.user

    if request.method == 'POST':
        username = request.POST.get('username')
        profile_picture = request.FILES.get('profilePicture')

        old_picture = user.profile_picture

        if username:
            user.username = username
        if profile_picture:
            user.profile_picture = profile_picture

        user.save()

        # Delete the old profile picture
        if old_picture and old_picture != user.profile_picture:
            old_picture_path = old_picture.path
            if os.path.exists(old_picture_path):
                os.remove(old_picture_path)

        messages.success(request, 'Profile updated successfully!')
        return redirect('change-profile')

    default_image_url = '{}{}'.format(settings.MEDIA_URL, 'profile_pics/users.jpg')

    context = {
        'profile_picture': user.profile_picture,
        'username': user.username,
        'default_image_url': default_image_url,
    }
    return render(request, 'change-profile.html', context)
    
    
@login_required
def change_password(request):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in after changing password
            messages.success(request, 'Your password was successfully updated!')
            return redirect('change-password')  # Redirect to the change password page or another appropriate page
        else:
            # Handle specific errors
            if 'old_password' in form.errors:
                messages.error(request, 'Old password is incorrect.')
            if 'new_password2' in form.errors:
                messages.error(request, 'New password and confirm password do not match.')
            else:
                messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(user=request.user)
    
    return render(request, 'change-password.html', {'form': form})




@login_required
def student_reservation(request):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Get the logged-in user's ID
    user_id = request.session.get('user_id')

    # Get the user type of the logged-in user
    user_faculty_items = facultyItem.objects.filter(user_id=user_id)

    # Get the IDs of the faculty items associated with the logged-in user
    faculty_item_ids = user_faculty_items.values_list('id', flat=True)

    # Filter to show reservations related to the logged-in user and user type
    reserved_request = StudentReservation.objects.filter(
        content_type__model='facultyitem',  # Assuming user_type corresponds to the facultyItem model
        object_id__in=faculty_item_ids
    ).order_by('-id')

    show_entries = request.GET.get('show', 'all')
    if show_entries == 'all':
        paginator = Paginator(reserved_request, 1000000)  # Large number to ensure all items are on one page
        current_show = 'all'
    else:
        paginator = Paginator(reserved_request, int(show_entries))
        current_show = int(show_entries)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'student-reservation.html', {
        'page_obj': page_obj,
        'current_show': current_show,
        'reserved_request': reserved_request
    })
    
    
@login_required
def update_reservation_status(request):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    if request.method == 'POST':
        reservation_id = request.POST.get('reservation_id')
        new_status = request.POST.get('status')
        notification_message = request.POST.get('message')

        # Fetch the reservation object
        reservation = get_object_or_404(StudentReservation, id=reservation_id)
        reservation.status = new_status
        reservation.notification = notification_message

        # Use the user_id of the logged-in user
        handled_by = request.user.username  # Store the user_id of the logged-in user

        # Capture the profile picture of the user handling the update
        if request.user.profile_picture:
            profile_picture_url = request.user.profile_picture.url
        else:
            # Use a default image if no profile picture is set
            profile_picture_url = f'{settings.MEDIA_URL}profile_pics/users.jpg'

        # Save the profile picture in the reservation
        reservation.handled_by_profile_picture = profile_picture_url

        # Set is_handled to True and is_read to False to mark it as a new notification
        reservation.is_handled = True
        reservation.is_read = False

        # Save the reservation with the updated fields
        reservation.handled_by = handled_by
        reservation.save()

        # Send an email notification to the student
        student_email = reservation.email

        try:
            send_mail(
                'Reservation Status Update',
                notification_message,
                settings.EMAIL_HOST_USER,  # From email
                [student_email],           # To email
                fail_silently=False,
            )
            messages.success(request, 'Status updated and email sent successfully!')
        except Exception as e:
            messages.error(request, f'Failed to send email: {str(e)}')

        # Redirect to a page where the user can see the result or continue with other actions
        return redirect('student-reservation')  # Adjust this to the appropriate URL name

    # Handle cases where the request method is not POST
    messages.error(request, 'Invalid request')
    return redirect('student-reservation')  # Adjust this to the appropriate URL name



@login_required
def generate_report(request, id):
    # Ensure only allowed users can access the report
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Get the specific BorrowRequest by ID
    try:
        borrow_request = BorrowRequest.objects.get(id=id)
        items = borrow_request.items.select_related('item')  # Fetch related items with facultyItem details
    except BorrowRequest.DoesNotExist:
        return HttpResponseNotFound("BorrowRequest not found.")
    
    # Structure data for the report
    context = {
        'borrow_request': borrow_request,
        'items': items,  # Ensure you pass the items to the context
        'image_url': request.build_absolute_uri(static('images/logo.png')),
    }
    
    # Render the HTML template
    html_string = render_to_string('borrower-report.html', context)

    # Configure pdfkit for PDF generation
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    
    try:
        options = {
            'no-stop-slow-scripts': '',
            'disable-smart-shrinking': '',
            'enable-local-file-access': '',
        }
        
        pdf = pdfkit.from_string(html_string, False, configuration=config, options=options)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="borrow_report.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"An error occurred: {str(e)}")
