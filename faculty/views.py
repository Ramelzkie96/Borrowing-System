from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from .models import facultyItem
from django.contrib import messages
from django.http import JsonResponse
from .models import BorrowRequest, facultyItem, BorrowRequestItemFaculty, PropertyID
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
    # Restrict access to superusers only
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        total_quantity = request.POST.get('total_quantity', '').strip()

        # Collect all dynamically generated property IDs
        property_id_list = [
            value.strip()
            for key, value in request.POST.items()
            if key.startswith("property_id_") and value.strip()
        ]

        # Ensure required fields are filled
        if name and total_quantity:
            try:
                total_quantity = int(total_quantity)
                if total_quantity <= 0:
                    raise ValueError("Quantity must be a positive number.")

                # Check if the item already exists for the current user (case-insensitive)
                existing_item = facultyItem.objects.filter(
                    name__iexact=name,
                    user=request.user
                ).first()

                if existing_item:
                    # Update the existing item's quantities
                    existing_item.total_quantity += total_quantity
                    existing_item.quantity += total_quantity
                    existing_item.save()

                    # Add new property IDs to the existing item with status 'Good'
                    for pid in property_id_list:
                        PropertyID.objects.create(
                            faculty_item=existing_item, 
                            property_id=pid, 
                            status='Good'  # Set status to 'Good' for new PropertyID
                        )

                    messages.success(request, 'SUCCESS! Item updated successfully.')
                else:
                    # Create a new item
                    new_item = facultyItem.objects.create(
                        name=name,
                        total_quantity=total_quantity,
                        quantity=total_quantity,
                        user=request.user
                    )

                    # Add property IDs for the new item with status 'Good'
                    for pid in property_id_list:
                        PropertyID.objects.create(
                            faculty_item=new_item, 
                            property_id=pid, 
                            status='Good'  # Set status to 'Good' for new PropertyID
                        )

                    messages.success(request, 'SUCCESS! New item added successfully.')

                return redirect('item-record')  # Redirect to item record

            except ValueError as e:
                messages.error(request, f'ERROR! {str(e)}')

        else:
            # Provide specific error messages for missing fields
            if not name:
                messages.error(request, 'ERROR! Please provide a name.')
            if not total_quantity:
                messages.error(request, 'ERROR! Please provide a valid quantity.')

        # Pass the submitted data back to the template in case of an error
        return render(request, 'add-item.html', {
            'name': name,
            'total_quantity': total_quantity
        })

    return render(request, 'add-item.html')


def get_property_ids(request, item_id):
    # Fetch the faculty item and its associated property IDs
    item = facultyItem.objects.get(id=item_id)
    property_ids = item.property_ids.all()  # Get all related PropertyID objects
    
    # Prepare the data to send as JSON
    property_data = [
        {
            'property_id': pid.property_id,
            'status': pid.status
        }
        for pid in property_ids
    ]
    
    return JsonResponse({'property_ids': property_data})



def update_property_status(request):
    if request.method == 'POST':
        try:
            # Retrieve form data
            item_name = request.POST.get('item_name')
            total_quantity = request.POST.get('total_quantity')  # Get total_quantity from the form
            property_data = request.POST.getlist('property_updates[]')
            new_items = request.POST.get('new_items', '[]')
            new_items = json.loads(new_items) if new_items else []

            faculty_item = None

            if item_name:
                # Update item name
                first_property_data = property_data[0]
                original_property_id = first_property_data.split(',')[0]
                property = PropertyID.objects.filter(property_id=original_property_id).first()
                if property:
                    faculty_item = property.faculty_item
                    faculty_item.name = item_name
                    faculty_item.save()

            # Process property updates
            for data in property_data:
                original_property_id, updated_property_id, status = data.split(',')

                # Check for duplicate Property ID
                if PropertyID.objects.filter(property_id=updated_property_id).exclude(property_id=original_property_id).exists():
                    messages.error(request, f'Duplicate Property ID found: {updated_property_id}. Update aborted.')
                    return redirect('item-record')

                property = PropertyID.objects.filter(property_id=original_property_id).first()
                if property:
                    property.property_id = updated_property_id
                    property.status = status
                    property.save()

            # Add new items
            for item in new_items:
                property_id = item['property_id']
                status = item['status']

                if PropertyID.objects.filter(property_id=property_id).exists():
                    messages.error(request, f'Duplicate Property ID found: {property_id}. New item addition aborted.')
                    return redirect('item-record')

                PropertyID.objects.create(
                    property_id=property_id,
                    status=status,
                    faculty_item=faculty_item
                )

            # Update total_quantity value
            if faculty_item and total_quantity:
                try:
                    faculty_item.total_quantity = int(total_quantity)  # Update total_quantity
                    faculty_item.save()
                except ValueError:
                    messages.error(request, 'Invalid value for total quantity. Update aborted.')
                    return redirect('item-record')

            # Update faculty item quantity based on "Good" status
            if faculty_item:
                good_count = PropertyID.objects.filter(faculty_item=faculty_item, status='Good').count()
                faculty_item.quantity = good_count
                faculty_item.save()

            messages.success(request, 'Properties and total quantity updated successfully.')
            return redirect('item-record')

        except Exception as e:
            messages.error(request, f'Unexpected error: {str(e)}')
            return redirect('item-record')

    messages.error(request, 'Invalid request method.')
    return redirect('item-record')







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
        total_quantity = request.POST.get('total_quantity')
        quantity = request.POST.get('quantity')

        # Retrieve the item and ensure it belongs to the current user
        item = get_object_or_404(facultyItem, id=item_id)

        if item.user_id != request.user.id:  # Ensure the item belongs to the current user
            messages.error(request, "You are not authorized to update this item.")
            return redirect('item-record')

        # Update item details
        item.name = name
        item.property_id = property_id  # Update property ID if provided
        item.total_quantity = total_quantity
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
    faculty_items = facultyItem.objects.filter(user=request.user)
    has_available_items = any(item.quantity > 0 for item in multimedia_items)

    form = BorrowRequestMultimediaForm(user=request.user)

    if request.method == 'POST':
        content_type = ContentType.objects.get_for_model(facultyItem)
        student_id = request.POST.get('student_id')
        date_borrow = request.POST.get('date_borrow')
        date_return_value = request.POST.get('date_return')  # Use raw input

        # Validate required fields
        if not date_borrow and not date_return_value:
            messages.error(request, 'ERROR! Both Date Borrow and Date Return are required.')
            return redirect('borrowers')
        elif not date_borrow:
            messages.error(request, 'ERROR! Date Borrow is required.')
            return redirect('borrowers')
        elif not date_return_value:
            messages.error(request, 'ERROR! Date Return is required.')
            return redirect('borrowers')

        try:
            # Parse and validate dates
            date_borrow_parsed = datetime.strptime(date_borrow, "%d %B, %Y").date()
            date_return_parsed = datetime.strptime(date_return_value, "%d %B, %Y").date()

            # # Ensure date_borrow is not in the past
            if date_borrow_parsed < timezone.now().date():
                messages.error(request, 'ERROR! Date Borrow cannot be set to a past date.')
                return redirect('borrowers')

            # Ensure date_return is not before date_borrow
            if date_return_parsed < date_borrow_parsed:
                messages.error(request, 'ERROR! Date Return cannot be before Date Borrow.')
                return redirect('borrowers')

            borrower_type = request.POST.get('borrower_type')
            if borrower_type not in ['Student', 'Teacher']:
                other_borrower_type = request.POST.get('other_borrower_type')
                if other_borrower_type:
                    borrower_type = other_borrower_type
                    
                    
            
            # Handle the upload_image field
            uploaded_image = request.FILES.get('upload_image')
            hidden_image = request.POST.get('hidden_upload_image')

            if uploaded_image:
                upload_image = uploaded_image
            elif hidden_image:
                # Remove '/media/' from the beginning if it exists
                if hidden_image.startswith('/media/'):
                    hidden_image = hidden_image[len('/media/'):]
                upload_image = hidden_image
            else:
                upload_image = None
                

            borrow_request = BorrowRequest.objects.filter(
                student_id=student_id,
                date_borrow=date_borrow,
                user=request.user
            ).first()

            if not borrow_request:
                borrow_request = BorrowRequest(
                    student_id=student_id,
                    name=request.POST.get('name'),
                    course=request.POST.get('course'),
                    year=request.POST.get('year'),
                    email=request.POST.get('email'),
                    phone=request.POST.get('phone'),
                    date_borrow=date_borrow,
                    date_return=date_return_value,  # Save raw input as-is
                    status='Unreturned',
                    note=request.POST.get('note', ''),
                    user=request.user,
                    purpose=request.POST.get('purpose'),
                    borrower_type=borrower_type,
                    content_type=content_type,
                    object_id=0,
                    upload_image=upload_image
                )
                borrow_request.save()

            items_borrowed = request.POST.getlist('item')
            quantities_borrowed = request.POST.getlist('quantities[]')
            descriptions = request.POST.getlist('description')

            if not items_borrowed:
                messages.error(request, 'ERROR! No items selected for borrowing.')
                return redirect('borrowers')

            with transaction.atomic():
                for item_id, quantity, description in zip(items_borrowed, quantities_borrowed, descriptions):
                    selected_item = facultyItem.objects.get(id=item_id)
                    requested_quantity = int(quantity)

                    if requested_quantity > selected_item.quantity:
                        messages.error(
                            request,
                            f"ERROR! Not enough '{selected_item.name}' available. "
                            f"Requested: {requested_quantity}, Available: {selected_item.quantity}."
                        )
                        return redirect('borrowers')

                    borrow_request_item = BorrowRequestItemFaculty.objects.filter(
                        borrow_request=borrow_request,
                        item=selected_item,
                        is_returned=False
                    ).first()

                    if borrow_request_item:
                        borrow_request_item.quantityy += requested_quantity
                        borrow_request_item.description = description
                        borrow_request_item.save()
                    else:
                        BorrowRequestItemFaculty.objects.create(
                            borrow_request=borrow_request,
                            item=selected_item,
                            quantityy=requested_quantity,
                            description=description,
                            is_returned=False,
                            handled_by=request.user
                        )

                    borrow_request.status = 'Unreturned'
                    borrow_request.date_return = date_return_value
                    borrow_request.created_at = timezone.now()
                    borrow_request.save()

                    selected_item.quantity -= requested_quantity
                    selected_item.save()

            messages.success(request, 'SUCCESS! Borrow requests have been submitted.')
            return redirect('borrow-record')

        except ValueError:
            messages.error(request, 'ERROR! Invalid date format. Please use DD MMMM, YYYY format (e.g., 25 November, 2024).')

    return render(request, 'borrowers.html', {
        'faculty_items': faculty_items,
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
# im taking rest not modify yet
@login_required
def borrower_details(request):
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")

    student_id = request.GET.get('student_id')
    name = request.GET.get('name')
    date_borrow = request.GET.get('date_borrow')
    status = request.GET.get('status')
    purpose = request.GET.get('purpose')
    user_id = request.user.id

    # Filter BorrowRequest based on the user handling the items and borrow request date
    borrow_requests = BorrowRequest.objects.filter(
        facultyitems__handled_by=user_id,
        date_borrow=date_borrow,
        student_id=student_id
    ).distinct()

    if not borrow_requests.exists():
        return render(request, '404.html', status=404)

    # Collect all items, including duplicates, across all borrow requests handled by the user
    all_items = []
    upload_image = None  # Initialize as None in case no image is found

    for borrow_request in borrow_requests:
        items = borrow_request.facultyitems.filter(handled_by=user_id)
        all_items.extend(items)  # Append each item to the list, allowing duplicates
        # Fetch the first image if available
        if borrow_request.upload_image:
            upload_image = borrow_request.upload_image.url

    context = {
        'student_id': student_id,
        'name': name,
        'date_borrow': date_borrow,
        'status': status,
        'purpose': purpose,
        'all_items': all_items,  # Pass all items, including duplicates, to the template
        'upload_image': upload_image,  # Add upload_image to the context
        'date_return': borrow_request.date_return,
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




def search_borrow_request(request):
    student_id = request.GET.get('student_id', '').replace('-', '')  # Cleaned ID
    original_id = request.GET.get('original_id', '')  # Original ID with hyphens

    if student_id:
        # Query the BorrowRequest model using both versions of the ID
        borrow_request = BorrowRequest.objects.filter(
            Q(student_id=student_id) | Q(student_id=original_id)
        ).last()

        if borrow_request:
            data = {
                'success': True,
                'name': borrow_request.name,
                'course': borrow_request.course,
                'year': borrow_request.year,
                'email': borrow_request.email,
                'phone': borrow_request.phone,
                'borrower_type': borrow_request.borrower_type,
                'date_borrow': borrow_request.date_borrow,
                'date_return': borrow_request.date_return,
                'purpose': borrow_request.purpose,
                'upload_image': f"{settings.MEDIA_URL}{borrow_request.upload_image}" if borrow_request.upload_image else None,
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
        'date_return': borrow_request.date_return,
        'borrower_type': borrow_request.borrower_type,
        'upload_image_url': borrow_request.upload_image.url if borrow_request.upload_image else None,  # Add this
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
                borrow_request.created_at = timezone.now()
                borrow_request.save()
                messages.success(request, f"Borrower status updated to {borrow_request.status}.")
                return redirect('borrow-record')  # Redirect after Fully Returned status update

            elif status == "Partial Item Returned" and returned_items > 0:
                borrow_request.status = "Partial Item Returned"  # Set status to Partial Item Returned
                borrow_request.created_at = timezone.now()
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
        borrow_request.date_borrow = request.POST.get('date_borrow')
        borrow_request.date_return = request.POST.get('date_return')
        borrow_request.borrower_type = request.POST.get('borrower_type')
        borrow_request.purpose = request.POST.get('purpose')
        
        # Handle image upload
        if 'upload_image' in request.FILES:  # Check if a file is uploaded
            borrow_request.upload_image = request.FILES['upload_image']  # Update the image field
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
        unreturned_items = borrow_request.facultyitems.filter(is_returned=False)
        items_list = [
            {
                'name': item.item.name,
                'quantity': item.quantityy,
                'date_borrow': borrow_request.date_borrow,
                'time_ago': borrow_request.time_ago(),
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




from django.db.models import BooleanField, Case, When, Subquery, OuterRef

@login_required
def student_reservation(request):
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")

    # Get the logged-in user's ID
    user_id = request.user.id

    # Filter ReservationItems and annotate reservations
    reservation_items = ReservationItem.objects.filter(user_facultyItem=user_id, reservation__is_borrow=False)
    reserved_request = StudentReservation.objects.filter(
        id__in=reservation_items.values('reservation'),
    ).annotate(
        single_handle_status=Subquery(
            ReservationItem.objects.filter(
                reservation=OuterRef('id'),
                user_facultyItem=user_id
            ).values('handle_status')[:1]
        ),
        has_approved=Case(
            When(
                id__in=ReservationItem.objects.filter(
                    reservation=OuterRef('id'),
                    status="Approved",
                    reservation__is_borrow=False
                ).values('reservation'),
                then=True
            ),
            default=False,
            output_field=BooleanField()
        )
    ).order_by('-id')

    # Pagination logic
    show_entries = request.GET.get('show', 'all')
    if show_entries == 'all':
        paginator = Paginator(reserved_request, 1000000)
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

        # Check statuses of items handled by the current user
        user_items = reservation.items.filter(user_facultyItem=request.user)
        all_approved_or_denied = all(i.status in ['Approved', 'Denied'] for i in user_items)
        any_pending = any(i.status == 'Pending' for i in user_items)

        # Update the handle_status of the ReservationItem based on the current user’s items
        if all_approved_or_denied and not any_pending:
            # All items handled by the current user are either approved or denied
            user_items.update(handle_status='Completed')
        else:
            # If any items handled by the current user are still pending
            user_items.update(handle_status='Pending')

        # Update the overall reservation status based on all items in the reservation
        all_items_approved = all(i.status == 'Approved' for i in reservation.items.all())
        all_items_denied = all(i.status == 'Denied' for i in reservation.items.all())
        any_item_pending = any(i.status == 'Pending' for i in reservation.items.all())

        if all_items_approved:
            reservation.status = 'Approved'
        elif all_items_denied:
            reservation.status = 'Denied'
        elif any_item_pending:
            reservation.status = 'Partially Processed'
        else:
            reservation.status = 'Completed'

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

        # # Send the email
        # send_mail(subject, message, from_email, recipient_list)

        # Redirect to 'admin-student-reservation' if needed
        if reservation.status in ['Approved', 'Denied', 'Completed']:
            response_data['redirect_url'] = reverse('student-reservation')

        return JsonResponse(response_data)

    except ReservationItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found.'})





@login_required
def proceed_borrow(request, reservation_id):
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")

    try:
        # Retrieve the reservation
        reservation = StudentReservation.objects.get(id=reservation_id)
        
        # Filter approved items linked to the reservation and current user
        approved_items = ReservationItem.objects.filter(
            reservation=reservation,
            status='Approved',
            user_facultyItem=request.user
        )

        # Filter faculty items handled by the current user
        faculty_items = facultyItem.objects.filter(user=request.user)
        
        # Default the borrower type to "Student"
        borrower_type = "Student"

        context = {
            'reserve_request_id': reservation.id,
            'student_id': reservation.student_id,
            'name': reservation.name,
            'course': reservation.course,
            'year': reservation.year_level,
            'email': reservation.email,
            'phone': reservation.phone_number,
            'date_reserve': reservation.reserve_date,
            'date_return': reservation.date_return,
            'purpose': reservation.purpose,
            'items': approved_items,
            'faculty_items': faculty_items,  # Pass faculty items to contex
            'borrower_type': borrower_type,  # Pass default borrower typet
            'upload_image_url': reservation.upload_image.url if reservation.upload_image else None,  # Add this
        }
        return render(request, 'proceed-borrow.html', context)

    except StudentReservation.DoesNotExist:
        return HttpResponseNotFound("Reservation not found.")
    
    


@transaction.atomic
def save_reservation_request(request):
    if request.method == 'POST':
        # Extract main BorrowRequest fields
        student_id = request.POST.get('student_id')
        name = request.POST.get('name')
        course = request.POST.get('course')
        year = request.POST.get('year')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        purpose = request.POST.get('purpose')
        borrower_type = request.POST.get('borrower_type')
        date_borrow = request.POST.get('date_reserve')
        date_return = request.POST.get('date_return')
        reservation_id = request.POST.get('id') 

        # Handle the upload_image field
        uploaded_image = request.FILES.get('upload_image')
        hidden_image = request.POST.get('hidden_upload_image')
        if uploaded_image:
            upload_image = uploaded_image
        elif hidden_image and hidden_image.startswith('/media/'):
            upload_image = hidden_image[len('/media/'):]
        else:
            upload_image = None

        # Check if BorrowRequest already exists for the same student_id and date_borrow
        borrow_request, created = BorrowRequest.objects.get_or_create(
            student_id=student_id,
            date_borrow=date_borrow,
            defaults={
                'name': name,
                'course': course,
                'year': year,
                'email': email,
                'phone': phone,
                'purpose': purpose,
                'status': "Unreturned",
                'borrower_type': borrower_type,
                'date_return': date_return,
                'user': request.user,
                'upload_image': upload_image,
            }
        )
        
        try:
            student_reservation = StudentReservation.objects.get(id=reservation_id)
            student_reservation.is_borrow = True  # Explicitly set to True
            student_reservation.save()
        except StudentReservation.DoesNotExist:
            messages.error(request, "Student reservation record not found.")
            return redirect('admin-student-reservation')


        # Initialize a flag to check if any BorrowRequestItemFaculty is created
        item_created = False
        counter = 1

        while f'itemm_{counter}' in request.POST:
            item_id = request.POST.get(f'itemm_{counter}')
            description = request.POST.get(f'description_{counter}')
            quantity = int(request.POST.get(f'quantity_{counter}', 0))

            if item_id:
                faculty_item = get_object_or_404(facultyItem, id=item_id)

                # Validate quantity
                if quantity > faculty_item.quantity:
                    transaction.set_rollback(True)
                    messages.error(request, f"Insufficient quantity for {faculty_item.name}.")
                    return redirect('student-reservation')

                # Check if the item already exists in BorrowRequestItemFaculty
                borrow_request_item = BorrowRequestItemFaculty.objects.filter(
                    borrow_request=borrow_request,
                    item=faculty_item
                ).first()

                if borrow_request_item:
                    # Update existing item's quantity
                    borrow_request_item.quantityy += quantity
                    borrow_request_item.description = description  # Update description if needed
                    borrow_request_item.save()
                else:
                    # Create a new BorrowRequestItemFaculty
                    BorrowRequestItemFaculty.objects.create(
                        borrow_request=borrow_request,
                        item=faculty_item,
                        item_name=faculty_item.name,
                        quantityy=quantity,
                        description=description,
                        handled_by=request.user,
                    )

                # Update facultyItem quantity
                faculty_item.quantity -= quantity
                faculty_item.save()

                # Set item_created flag to True as we've added or updated an item
                item_created = True

            counter += 1

        # If no items were created or updated, roll back and show an error
        if not item_created:
            transaction.set_rollback(True)
            messages.error(request, "You must select at least one item.")
            return redirect('student-reservation')

        # Display a success message
        if created:
            messages.success(request, "New borrow request created successfully!")
        else:
            messages.success(request, "Borrow request updated successfully!")

        return redirect('borrow-record')

    return redirect('student-reservation')









import random  # don't forget to import random at the top!

@login_required
def generate_report(request, id):
    if not request.user.faculty:
        return HttpResponseForbidden("You do not have permission to access this page.")

    try:
        borrow_request = BorrowRequest.objects.get(id=id)
        items = borrow_request.facultyitems.select_related('item')  # already fetching related item
    except BorrowRequest.DoesNotExist:
        return HttpResponseNotFound("BorrowRequest not found.")

    # Prepare a list to store items with random property IDs
    items_with_property = []

    for item in items:
        faculty_item = item.item  # this is the facultyItem instance
        property_ids = faculty_item.property_ids.all()  # get all related PropertyIDs

        if property_ids.exists():
            selected_property = random.choice(property_ids)
            selected_property_id = selected_property.property_id
        else:
            selected_property_id = "N/A"  # fallback if no property IDs exist

        # Attach the selected property_id manually
        item.random_property_id = selected_property_id
        items_with_property.append(item)

    context = {
        'borrow_request': borrow_request,
        'items': items_with_property,
        'image_url': request.build_absolute_uri(static('images/logo.png')),
    }

    html_string = render_to_string('borrower-report.html', context)

    wkhtmltopdf_path = os.path.join(settings.BASE_DIR, 'wkhtmltopdf', 'bin', 'wkhtmltopdf.exe')
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)

    try:
        options = {
            'no-stop-slow-scripts': '',
            'disable-smart-shrinking': '',
            'enable-local-file-access': '',
            'page-width': '8.5in',
            'page-height': '13in',
            'orientation': 'Portrait',
            'margin-top': '0.5in',
            'margin-right': '0.5in',
            'margin-bottom': '0.5in',
            'margin-left': '0.5in',
            'dpi': 300,
            'zoom': 1.0,
        }

        pdf = pdfkit.from_string(html_string, False, configuration=config, options=options)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="borrow_report.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"An error occurred: {str(e)}")








