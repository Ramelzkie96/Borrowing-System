from django.core.paginator import Paginator 
from django.shortcuts import render, redirect, get_object_or_404 
from .models import facultyItem
from django.contrib import messages 
from django.http import JsonResponse  
from .models import BorrowRequest, facultyItem, BorrowRequestItemFaculty
from .forms import BorrowRequestMultimediaForm
from django.views.decorators.http import require_POST  
from django.core.mail import send_mail 
from django.views.decorators.csrf import csrf_exempt  
from .forms import EmailNotificationForm
from django.conf import settings 
from django.contrib.contenttypes.models import ContentType  
from reservation.models import StudentReservation, ReservationItem
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
from collections import OrderedDict
from django.urls import reverse





@login_required
def add_item(request):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    if request.method == 'POST':
        name = request.POST.get('name')
        property_id = request.POST.get('property_id')
        quantity = request.POST.get('quantity')

        # Ensure required fields are filled
        if name and quantity:
            try:
                # Ensure quantity is a valid integer
                quantity = int(quantity)
                if quantity <= 0:
                    raise ValueError("Quantity must be a positive number.")
                
                # Create the new item and associate it with the current user
                facultyItem.objects.create(
                    name=name,
                    property_id=property_id if property_id else None,  # Set property_id if provided
                    quantity=quantity,
                    user_id=request.user.id  # Associate the item with the current user's ID
                )
                messages.success(request, 'SUCCESS! Item has been added successfully.')
                return redirect('item-record')  # Redirect to item_record after adding item
            
            except ValueError as e:
                messages.error(request, f'ERROR! {str(e)}')
        else:
            messages.error(request, 'ERROR! Please fill out all required fields.')

        # Pass the submitted data back to the template in case of an error
        return render(request, 'add-item.html', {'name': name, 'property_id': property_id, 'quantity': quantity})

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
        property_id = request.POST.get('property_id')
        quantity = request.POST.get('quantity')

        # Retrieve the item and ensure it belongs to the current user
        item = get_object_or_404(facultyItem, id=item_id)

        if item.user_id != request.user.id:  # Ensure the item belongs to the current user
            messages.error(request, "You are not authorized to update this item.")
            return redirect('item-record')

        # Update item details
        item.name = name
        item.property_id = property_id  # Update property ID if provided
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

            if date_borrow_parsed < timezone.now().date():
                messages.error(request, 'ERROR! Date Borrow cannot be set to a past date.')
            else:
                borrower_type = request.POST.get('borrower_type')
                if borrower_type not in ['Student', 'Teacher']:
                    other_borrower_type = request.POST.get('other_borrower_type')
                    if other_borrower_type:
                        borrower_type = other_borrower_type

                # Check if there is an existing BorrowRequest with the same student_id, date_borrow, and user
                borrow_request = BorrowRequest.objects.filter(
                    student_id=student_id,
                    date_borrow=date_borrow,
                    user=request.user
                ).first()

                # If no such BorrowRequest exists, create a new one
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
                        status='Unreturned',
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
                descriptions = request.POST.getlist('description')

                # Begin transaction
                with transaction.atomic():
                    for item_id, quantity, description in zip(items_borrowed, quantities_borrowed, descriptions):
                        selected_item = facultyItem.objects.get(id=item_id)
                        requested_quantity = int(quantity)

                        # Backend quantity validation
                        if requested_quantity > selected_item.quantity:
                            messages.error(
                                request,
                                f"ERROR! Not enough '{selected_item.name}' available. Requested: {requested_quantity}, Available: {selected_item.quantity}."
                            )
                            return redirect('borrowers')  # Redirect back to form

                        # Check if an item entry exists for this BorrowRequest
                        borrow_request_item = BorrowRequestItemFaculty.objects.filter(
                            borrow_request=borrow_request,
                            item=selected_item,
                            is_returned=False
                        ).first()

                        if borrow_request_item:
                            # Update quantity and description for the existing item
                            borrow_request_item.quantityy += requested_quantity
                            borrow_request_item.description = description  # Update the description if needed
                            borrow_request_item.save()
                        else:
                            # Create a new item entry for this BorrowRequest
                            BorrowRequestItemFaculty.objects.create(
                                borrow_request=borrow_request,
                                item=selected_item,
                                quantityy=requested_quantity,
                                description=description,  # Set the description for the new entry
                                is_returned=False,
                                handled_by=request.user  # Set handled_by to the current user here
                            )
                            
                            borrow_request.status = 'Unreturned'
                            borrow_request.save()

                        # Decrease item quantity in stock
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
                       .filter(facultyitems__handled_by=request.user)  # Use related name 'items' to filter
                       .values('student_id', 'date_borrow')
                       .annotate(latest_id=Max('id')))

    # Retrieve actual BorrowRequest objects using latest_id from the previous query
    latest_requests = BorrowRequest.objects.filter(id__in=[item['latest_id'] for item in borrow_requests])

    # Calculate seconds ago for each request and store them in a list
    now = timezone.now()
    requests_with_time_ago = [
        {
            'request': req,
            'seconds_ago': (now - req.created_at).total_seconds()
        }
        for req in latest_requests
    ]

    # Sort the requests by seconds_ago
    sorted_requests = sorted(requests_with_time_ago, key=lambda x: x['seconds_ago'])

    # Extract sorted requests
    sorted_latest_requests = [item['request'] for item in sorted_requests]

    total_borrow_requests = len(sorted_latest_requests)

    # Fetch all items from facultyItem model associated with the logged-in user
    user_items = facultyItem.objects.filter(user=request.user)

    # Pagination setup
    show_entries = request.GET.get('show', 'all')
    if show_entries == 'all':
        paginator = Paginator(sorted_latest_requests, 1000000)
        current_show = 'all'
    else:
        paginator = Paginator(sorted_latest_requests, int(show_entries))
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
    
    student_id = request.GET.get('student_id')
    name = request.GET.get('name')
    date_borrow = request.GET.get('date_borrow')
    status = request.GET.get('status')
    user_id = request.user.id

    # Filter BorrowRequest based on the user handling the items and borrow request date
    borrow_requests = BorrowRequest.objects.filter(
        facultyitems__handled_by=user_id,
        date_borrow=date_borrow,
    ).distinct()

    if not borrow_requests.exists():
        return render(request, '404.html', status=404)
    
    # Collect all items, including duplicates, across all borrow requests handled by the user
    all_items = []
    for borrow_request in borrow_requests:
        items = borrow_request.facultyitems.filter(handled_by=user_id)
        all_items.extend(items)  # Append each item to the list, allowing duplicates

    context = {
        'student_id': student_id,
        'name': name,
        'date_borrow': date_borrow,
        'status': status,
        'all_items': all_items,  # Pass all items, including duplicates, to the template
    }
    
    return render(request, 'borrower-details.html', context)





def fetch_borrow_request_items(request):
    if request.method == 'GET':
        request_id = request.GET.get('request_id')
        
        items = BorrowRequestItemFaculty.objects.filter(
            borrow_request_id=request_id,
            is_returned=False
        ).select_related('item')

        item_list = [
            {
                'item_name': borrow_item.item.name,
                'description': borrow_item.description,
                'quantity': borrow_item.quantityy,
                'date_return': borrow_item.date_return.strftime('%d %B, %Y') if borrow_item.date_return else None,
            }
            for borrow_item in items
        ]

        return JsonResponse({'items': item_list})

    return JsonResponse({'error': 'Invalid request'}, status=400)





def fetch_borrow_request_items_record(request):
    if request.method == 'GET':
        student_id = request.GET.get('student_id')
        date_borrow = request.GET.get('date_borrow')
        handled_by = request.user  # assuming handled_by is the current logged-in user

        items = BorrowRequestItemFaculty.objects.filter(
            borrow_request__student_id=student_id,
            borrow_request__date_borrow=date_borrow,
            handled_by=handled_by,
            is_returned=True  # filter only returned items
        ).select_related('item')

        item_list = [
            {
                'item_name': borrow_item.item.name,
                'description': borrow_item.description,
                'quantity': borrow_item.quantityy,
                'date_return': borrow_item.date_return.strftime('%d %B, %Y') if borrow_item.date_return else None,
            }
            for borrow_item in items
        ]

        return JsonResponse({'items': item_list})

    return JsonResponse({'error': 'Invalid request'}, status=400)








@login_required
def fetch_borrow_request(request):
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")

    # Get the BorrowRequest instance
    borrow_request_id = request.GET.get('id')
    borrow_request = get_object_or_404(BorrowRequest, id=borrow_request_id)

    # Fetch the related BorrowRequestItems
    borrow_request_items = borrow_request.facultyitems.all()  # Get all related items

    # Fetch items from facultyItem that are handled by the current user
    items = facultyItem.objects.filter(user=request.user)

    # Prepare context for displaying in the template
    context = {
        'borrow_request_id': borrow_request_id,
        'borrow_request_items': borrow_request_items,
        'items': items,
        'purpose': borrow_request.purpose,
        'student_id': borrow_request.student_id,
        'name': borrow_request.name,
        'course': borrow_request.course,
        'year': borrow_request.year,
        'email': borrow_request.email,
        'phone': borrow_request.phone,
        'date_borrow': borrow_request.date_borrow,
        'borrower_type': borrow_request.borrower_type,
        # Other context variables if needed...
    }

    return render(request, 'update-borrow-request.html', context)



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

    # Fetch the related BorrowRequestItems
    borrow_request_items = borrow_request.facultyitems.all()  # Get all related items

    # Fetch items from facultyItem that are handled by the current user
    items = facultyItem.objects.filter(user=request.user)

    # Prepare context for displaying in the template
    context = {
        'borrow_request_id': borrow_request_id,
        'borrow_request_items': borrow_request_items,
        'items': items,
        'purpose': borrow_request.purpose,
        'student_id': borrow_request.student_id,
        'name': borrow_request.name,
        'course': borrow_request.course,
        'year': borrow_request.year,
        'email': borrow_request.email,
        'phone': borrow_request.phone,
        'date_borrow': borrow_request.date_borrow,
        'borrower_type': borrow_request.borrower_type,
        # Other context variables if needed...
    }

    return render(request, 'update-borrow-request.html', context)


@csrf_exempt  # Optional, remove if not necessary for production
def update_borrower_status(request):
    if request.method == "POST":
        borrow_request_id = request.POST.get("borrow_request_id")
        status = request.POST.get("status", "Unreturned")  # Get status from the form data

        try:
            # Fetch the BorrowRequest based on the ID provided
            borrow_request = BorrowRequest.objects.get(id=borrow_request_id)
            
            # Fetch all items associated with this BorrowRequest
            facultyitems = borrow_request.facultyitems.all()
            total_items = facultyitems.count()
            returned_items = facultyitems.filter(is_returned=True).count()

            # Set the BorrowRequest status based on the count of returned items
            if status == "Fully Returned":
                borrow_request.status = "Fully Returned"  # Set status to Fully Returned
                borrow_request.save()
                messages.success(request, f"Borrower status updated to {borrow_request.status}.")
                return redirect('borrow-record')  # Redirect after Fully Returned status update

            elif status == "Partial Item Returned" and returned_items > 0:
                borrow_request.status = "Partial Item Returned"  # Set status to Partial Item Returned
                borrow_request.save()
                messages.success(request, "Item returned successfully!")
                return redirect(request.META.get('HTTP_REFERER'))  # Reload the page when status is Partial Item Returned

            else:
                borrow_request.status = "Unreturned"  # Set status to Unreturned
                borrow_request.save()
                messages.success(request, f"Borrower status updated to {borrow_request.status}.")
                return redirect(request.META.get('HTTP_REFERER'))  # Reload the page when status is Unreturned

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
            borrow_item = BorrowRequestItemFaculty.objects.get(id=borrow_request_item_id)
            faculty_item = facultyItem.objects.get(id=item_id)

            # Update BorrowRequestItem fields
            borrow_item.date_return = date_return
            borrow_item.is_returned = True  # Mark as returned
            borrow_item.save()

            # Update facultyItem quantity
            faculty_item.quantity += borrow_item.quantityy
            faculty_item.save()

            return JsonResponse({"success": True})

        except BorrowRequestItemFaculty.DoesNotExist:
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
        # Get the borrow request ID from the form
        borrow_request_id = request.POST.get('id')
        borrow_request = get_object_or_404(BorrowRequest, id=borrow_request_id)

        # Update the BorrowRequest fields
        borrow_request.student_id = request.POST.get('student_id')
        borrow_request.name = request.POST.get('name')
        borrow_request.course = request.POST.get('course')
        borrow_request.year = request.POST.get('year')
        borrow_request.email = request.POST.get('email')
        borrow_request.phone = request.POST.get('phone')
        borrow_request.date_borrow = request.POST.get('datepicker')
        borrow_request.borrower_type = request.POST.get('borrower_type')
        borrow_request.purpose = request.POST.get('purpose')
        borrow_request.save()  # Save changes to BorrowRequest

        # Update each BorrowRequestItem based on the form data
        for index in range(1, len(request.POST) // 2 + 1):
            item_id = request.POST.get(f'itemm_{index}')
            description = request.POST.get(f'description_{index}')
            new_quantity = request.POST.get(f'quantity_{index}')  # Change to correct field name

            if item_id and description:  # Check if both fields are provided
                borrow_item = get_object_or_404(BorrowRequestItemFaculty, id=request.POST.get(f'borrow_item_id_{index}'))  # Assuming you have an ID for each item

                # Restore quantity in the original item based on the old quantity
                faculty_item = borrow_item.item  # Get the corresponding facultyItem
                faculty_item.quantity += borrow_item.quantityy  # Restore the previous quantity
                faculty_item.save()  # Save the changes to the facultyItem

                # Update BorrowRequestItem with new values
                borrow_item.item_id = item_id
                borrow_item.description = description
                borrow_item.quantityy = int(new_quantity)  # Set the new quantity
                borrow_item.save()  # Save changes to BorrowRequestItem

                # Deduct the quantity from the facultyItem based on the new quantity
                faculty_item.quantity -= borrow_item.quantityy
                faculty_item.save()  # Save the updated facultyItem

        messages.success(request, 'SUCCESS! Borrow requests have been updated successfully.')
        return redirect('borrow-record')

    messages.error(request, "Something is wrong during update.")
    return redirect('update-borrower')



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
    user_id = request.user.id  # Use request.user.id to directly get the logged-in user's ID

    # Filter ReservationItems based on user_facultyItem
    reservation_items = ReservationItem.objects.filter(user_facultyItem=user_id)

    # Get the associated StudentReservations from the filtered ReservationItems
    reserved_request = StudentReservation.objects.filter(
        id__in=reservation_items.values('reservation')
    ).order_by('-id')

    # Pagination logic
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
def status_update(request, reservation_id):
    # Restrict access to faculty users only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Fetch the reservation
    reservation = get_object_or_404(StudentReservation, id=reservation_id)
    
    # Fetch the items associated with the reservation that the logged-in user is handling
    items = reservation.items.filter(user_facultyItem=request.user)

    context = {
        'reservation': reservation,
        'items': items,
    }
    return render(request, 'reservation-approval-status.html', context)




@login_required
@require_POST
def update_reservation_item_status(request):
    data = json.loads(request.body)
    item_id = data.get('item_id')
    new_status = data.get('status')

    try:
        # Fetch the reservation item
        item = ReservationItem.objects.get(id=item_id)

        # Fetch the associated StudentReservation
        reservation = item.reservation  # This gets the associated StudentReservation

        # Update the status of the ReservationItem
        item.status = new_status
        item.notification = f"{item.item_name} has been {new_status}"
        item.user_type = request.user.username  # Store the username of the current user

        # Set the profile picture URL
        if request.user.profile_picture:
            item.handled_by_profile_picture = request.user.profile_picture.url
        else:
            item.handled_by_profile_picture = f'{settings.MEDIA_URL}profile_pics/users.jpg'

        # Set is_update to True when approved or denied
        item.is_update = True
        item.is_read = False
        item.is_handled = True
        item.created_at = timezone.now()
        item.save()

        time_ago = item.time_ago()

        # Check the statuses of all items in the reservation
        items = reservation.items.all()
        all_approved = all(item.status == 'Approved' for item in items)
        all_denied = all(item.status == 'Denied' for item in items)
        any_pending = any(item.status == 'Pending' for item in items)

        # Update the status of the StudentReservation based on item statuses
        if all_approved:
            reservation.status = 'Approved'
            redirect_needed = True  # Set flag to redirect
        elif all_denied:
            reservation.status = 'Denied'
            redirect_needed = True  # Set flag to redirect
        elif any_pending:
            reservation.status = 'Partially Processed'
            redirect_needed = False
        else:
            reservation.status = 'Completed'
            redirect_needed = True  # Redirect when all items are processed but not all the same status

        reservation.save()

        # Prepare response
        response_data = {
            'success': True,
            'message': f"Item '{item.item_name}' status updated to {new_status}.",
            'new_status': new_status,
            'new_class': 'badge-success' if new_status == 'Approved' else 'badge-danger',  # Customize class based on status
            'time_ago': time_ago  # Send the specific time ago of this item
        }

        # Send email notification
        # subject = f"Reservation Item Status Updated: {item.item_name}"
        # message = f"Dear {reservation.name},\n\nThe status of your reservation item '{item.item_name}' has been updated to '{new_status}'.\n\nNotification: {item.notification}\n\nBest regards,\nYour Reservation Team"
        # from_email = settings.EMAIL_HOST_USER
        # recipient_list = [reservation.email]

        # Send the email
        # send_mail(subject, message, from_email, recipient_list)

        # Redirect to 'admin-student-reservation' if needed
        if redirect_needed:
            response_data['redirect_url'] = reverse('student-reservation')

        return JsonResponse(response_data)

    except ReservationItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found.'})










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
