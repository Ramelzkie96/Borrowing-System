from django.shortcuts import render, redirect
from .forms import LoginForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from functools import wraps
from faculty.models import BorrowRequest, facultyItem, BorrowRequestItemFaculty, PropertyID
from django.contrib import messages
from django.core.paginator import Paginator
from .models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.views import PasswordResetView
from reservation.models import StudentReservation, ReservationItem
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from faculty.forms import EmailNotificationForm, BorrowRequestMultimediaForm
from django.utils.timezone import now
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, timedelta
from django.db.models import Q
import json
import os
from django.templatetags.static import static
import pdfkit
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.db.models import Max, Count
from django.db import transaction
from django.shortcuts import get_list_or_404
from collections import OrderedDict
# Create your views here.

User = get_user_model()

def login_view(request):
    form = LoginForm(request.POST or None)
    msg = None

    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                request.session['user_id'] = user.id
                request.session['faculty'] = user.faculty

                if user.faculty:
                    messages.success(request, "Login successfully!")
                    return redirect('dashboard')
                else:
                    messages.error(request, "No faculty role assigned! Contact the IT Chairman.")
                    msg = 'No faculty role assigned! Contact the IT Chairman.'
            else:
                messages.error(request, "Invalid credentials!")
                msg = 'Invalid credentials'
        else:
            messages.error(request, "Error validating form!")
            msg = 'Error validating form'

    # Ensure that all messages are passed correctly
    return render(request, 'login.html', {'form': form, 'msg': msg, messages: 'messages'})


def logoutUser(request):
    logout(request)
    messages.success(request, "Logout successfully!")
    return redirect('login_view')

def adminlogout(request):
    logout(request)
    messages.success(request, "Logout successfully!")
    return redirect('custom_login')

@login_required(login_url='home_redirect')
def faculty(request):
    # Get the logged-in user
    user = request.user

    # Count of borrowed items with status 'Borrowed' belonging to the logged-in user
    borrow_request_count = BorrowRequest.objects.filter(
    Q(status='Unreturned') | Q(status='Partial Item Returned'),
    user=user
).count()





    # Count of total items belonging to the logged-in user
    faculty_item_count = facultyItem.objects.filter(user=user).count()

    # Count of all StudentReservation items with status 'Pending' that match the user_type
    student_reservation_count = StudentReservation.objects.filter(
    id__in=ReservationItem.objects.filter(
        user_facultyItem=user.id
    ).values('reservation'),
    status__in=['Pending', 'Partially Process']
).count()


    # Fetch latest borrow request per unique combination of student_id and date_borrow
    latest_ids = BorrowRequest.objects.order_by('-id')

    # Fetch the BorrowRequest objects for these latest IDs
    borrowed_requests = BorrowRequest.objects.filter(
    Q(status='Unreturned') | Q(status='Partial Item Returned'),
    id__in=latest_ids
).order_by('-created_at')

    # Render the template with the counts and the list of borrowed requests
    return render(request, 'dashboard.html', {
        'borrow_request_count': borrow_request_count,
        'faculty_item_count': faculty_item_count,
        'student_reservation_count': student_reservation_count,
        'borrowed_requests': borrowed_requests,
        'username': user.username,  # Add the username to the context
    })






def faculty_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.faculty:
            return view_func(request, *args, **kwargs)
        else:
            return redirect('home_redirect')  # Redirect to the appropriate login page

    return _wrapped_view





class CustomPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        email = form.cleaned_data['email']
        UserModel = get_user_model()  # Use the custom user model
        if not UserModel.objects.filter(email=email).exists():
            form.add_error('email', 'No account found with that email.')
            return self.form_invalid(form)
        return super().form_valid(form)


def custom_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('admin-dashboard')  # Redirect to the admin dashboard after login
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'admin-login.html', {'is_login_page': True})


@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'You do not have permission to access this page.'}, status=403)
    total_users = User.objects.count()  # Count all users
    current_user = request.user  # Get the logged-in user

    borrow_request_count = (BorrowRequest.objects
                        .filter(user=current_user)
                        .filter(Q(status='Unreturned') | Q(status='Partial Item Returned'))
                        .values('student_id', 'date_borrow')
                        .distinct()
                        .count())

    # Fetch latest borrow request per unique combination of student_id and date_borrow
    latest_ids = BorrowRequest.objects.order_by('-id')

    # Fetch the BorrowRequest objects for these latest IDs
    borrow_request = BorrowRequest.objects.filter(
    id__in=latest_ids
                ).filter(
                    Q(status='Unreturned') | Q(status='Partial Item Returned')
                ).order_by('-created_at')

    # Count of total items belonging to the logged-in user
    faculty_item_count = facultyItem.objects.filter(user=current_user).count()

    # Fetch all items from facultyItem model associated with the logged-in user
    user_items = facultyItem.objects.filter(user=request.user)

    # Count of all StudentReservation items with status 'Pending' that match the user_type
    # Filter StudentReservation with status 'Pending' or 'Partially Process' and related items with user_type matching request.user.id
    student_reservation_count = StudentReservation.objects.filter(
    id__in=ReservationItem.objects.filter(
        user_facultyItem=current_user.id
    ).values('reservation'),
    status__in=['Pending', 'Partially Process']
).count()


    # Pagination setup based on "show" parameter from the request
    show_entries = request.GET.get('show', 'all')  # Default to 'all' if 'show' is not provided
    if show_entries == 'all':
        paginator = Paginator(borrow_request, 1000)  # Large number to show all records on one page
        current_show = 'all'
    else:
        try:
            paginator = Paginator(borrow_request, int(show_entries))
            current_show = int(show_entries)
        except ValueError:
            paginator = Paginator(borrow_request, 1000)  # Default to 'all' if an invalid value is passed
            current_show = 'all'

    # Get the current page number
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'total_users': total_users,
        'page_obj': page_obj,
        'current_show': current_show,
        'username': current_user.username,  # Get username
        'borrow_request_count': borrow_request_count,
        'faculty_item_count': faculty_item_count,
        'items': user_items,
        'student_reservation_count': student_reservation_count,
    }
    return render(request, 'admin-dashboard.html', context)


@login_required
def admin_users(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'You do not have permission to access this page.'}, status=403)
    # Fetch all users
    users = User.objects.all().order_by('-id')

    # Pagination setup based on "show" parameter from the request
    show_entries = request.GET.get('show', 'all')  # Default to 'all' if 'show' is not provided
    if show_entries == 'all':
        paginator = Paginator(users, 1000)  # Large number to show all records on one page
        current_show = 'all'
    else:
        try:
            paginator = Paginator(users, int(show_entries))
            current_show = int(show_entries)
        except ValueError:
            paginator = Paginator(users, 1000)  # Default to 'all' if an invalid value is passed
            current_show = 'all'

    # Get the current page number
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)


    context = {
        'page_obj': page_obj,
        'current_show': current_show,  # Pass the current "show" value to the template
    }

    return render(request, 'admin-users.html', context)


def create_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')
        profile_picture = request.FILES.get('profile_picture')

        # Validation checks
        errors = {}

        # Password matching check
        if password != confirm_password:
            errors['confirm_password_error'] = "Passwords do not match."

        # Username existence check
        if User.objects.filter(username=username).exists():
            errors['username_error'] = "Username already exists. Please choose a different username."

        # Email existence check
        if User.objects.filter(email=email).exists():
            errors['email_error'] = "Email already exists. Please choose a different email."

        # Return errors if any
        if errors:
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        try:
            # Create user instance
            user = User(
                username=username,
                email=email,
                profile_picture=profile_picture,
                is_superuser=(role == 'IT Chairman'),  # Set superuser status based on role
                faculty=(role == 'Faculty'),  # Set faculty status based on role
            )
            user.set_password(password)  # Hash the password
            user.save()  # Save the user instance to the database
            messages.success(request, 'User created successfully.')
            return JsonResponse({'success': True, 'redirect': reverse('admin-users')})

        except ValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': "Invalid request method."}, status=400)



def edit_user(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        username = request.POST.get('usernamee')
        email = request.POST.get('emaill')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_passworddd')  # New confirm password field
        role = request.POST.get('rolee')
        profile_picture = request.FILES.get('profile_picturee')

        # Get the user instance by ID
        user = get_object_or_404(User, id=user_id)

        # Validation checks
        errors = {}

        # Username existence check (exclude the current user)
        if User.objects.filter(username=username).exclude(id=user.id).exists():
            errors['usernamee_error'] = "Username already exists. Please choose a different username."

        # Email existence check (exclude the current user)
        if User.objects.filter(email=email).exclude(id=user.id).exists():
            errors['emaill_error'] = "Email already exists. Please choose a different email."

        if new_password != confirm_password:
            errors['confirm_passworddd_error'] = "New password and confirm password do not match."

        # Return errors if any
        if errors:
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        try:
            # Update user instance
            user.username = username
            user.email = email
            if profile_picture:
                user.profile_picture = profile_picture

            # Clear previous roles
            user.is_superuser = False
            user.faculty = False

            # Assign new role based on the selected radio button
            if role == 'IT Chairman':
                user.is_superuser = True
            elif role == 'Faculty':
                user.faculty = True

            # Update password if a new one is provided
            if new_password:
                user.set_password(new_password)

            user.save()  # Save updated user to the database
            messages.success(request, 'User updated successfully.')
            return JsonResponse({'success': True, 'redirect': reverse('admin-users')})

        except ValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': "Invalid request method."}, status=400)



@csrf_exempt
def update_user_status(request):
    if request.method == 'POST':
        # Access the data from request.POST
        user_id = request.POST.get('user_id')
        is_active = request.POST.get('is_active') == 'true'  # Convert to boolean

        try:
            user = User.objects.get(id=user_id)
            # If the toggle is off, deactivate both faculty and superuser status
            if not is_active:
                user.faculty = False
                user.is_superuser = False
            else:
                # Reactivate the user with appropriate status (based on your business logic)
                user.faculty = True  # or set user.is_superuser = True depending on your needs

            user.save()
            return JsonResponse({'success': True})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})





#logic for borrower details in check button
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


# logic updating Returned in Status@csrf_exempt  # Make sure to secure this endpoint in production
@csrf_exempt  # Optional, remove if not necessary for production
def update_borrower_status(request):
    if request.method == "POST":
        borrow_request_id = request.POST.get("borrow_request_id")
        status = request.POST.get("status", "Unreturned")  # Get status from the form data

        try:
            # Fetch the BorrowRequest based on the ID provided
            borrow_request = BorrowRequest.objects.get(id=borrow_request_id)

            # Fetch all items associated with this BorrowRequest
            items = borrow_request.facultyitems.all()
            total_items = items.count()
            returned_items = items.filter(is_returned=True).count()

            # Set the BorrowRequest status based on the count of returned items
            if status == "Fully Returned":
                borrow_request.status = "Fully Returned"  # Set status to Fully Returned
                borrow_request.created_at = timezone.now()
                borrow_request.save()
                messages.success(request, f"Borrower status updated to {borrow_request.status}.")
                return redirect('admin-borrow-record')  # Redirect after Fully Returned status update

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
            return redirect('admin-borrower-details')  # Redirect on error

    messages.error(request, "Invalid request method.")
    return redirect('admin-borrower-details')  # Redirect on invalid request method







@csrf_exempt  # Optional, remove if not necessary for production
def update_borrower_status_dashboard(request):
    if request.method == "POST":
        borrow_request_id = request.POST.get("borrow_request_id")
        status = request.POST.get("status", "Unreturned")  # Get status from the form data

        try:
            # Fetch the BorrowRequest based on the ID provided
            borrow_request = BorrowRequest.objects.get(id=borrow_request_id)

            # Fetch all items associated with this BorrowRequest
            items = borrow_request.facultyitems.all()
            total_items = items.count()
            returned_items = items.filter(is_returned=True).count()

            # Set the BorrowRequest status based on the count of returned items
            if status == "Fully Returned":
                borrow_request.status = "Fully Returned"  # Set status to Fully Returned
                borrow_request.created_at = timezone.now()
                borrow_request.save()
                messages.success(request, f"Borrower status updated to {borrow_request.status}.")
                return redirect('admin-dashboard')  # Redirect after Fully Returned status update

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
            return redirect('admin-borrower-details_dashboard')  # Redirect on error

    messages.error(request, "Invalid request method.")
    return redirect('admin-borrower-details_dashboard')  # Redirect on invalid request method






@csrf_exempt
def send_email_notification(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
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
                return redirect('admin-borrow-record')  # Use the direct URL
            except Exception as e:
                # Add an error message and redirect
                messages.error(request, f'Error sending email: {str(e)}')
                return redirect('admin-borrow-record')  # Use the direct URL
        else:
            # Add an error message for invalid form data and redirect
            messages.error(request, 'Invalid form data.')
            return redirect('admin-borrow-record')  # Use the direct URL

    # Handle cases where the request method is not POST
    messages.error(request, 'Invalid request method.')
    return redirect('admin-borrow-record')  # Use the direct URL



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
def add_item(request):
    # Restrict access to superusers only
    if not request.user.is_superuser:
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

                return redirect('admin-item-record')  # Redirect to item record

            except ValueError as e:
                messages.error(request, f'ERROR! {str(e)}')

        else:
            # Provide specific error messages for missing fields
            if not name:
                messages.error(request, 'ERROR! Please provide a name.')
            if not total_quantity:
                messages.error(request, 'ERROR! Please provide a valid quantity.')

        # Pass the submitted data back to the template in case of an error
        return render(request, 'admin-add-item.html', {
            'name': name,
            'total_quantity': total_quantity
        })

    return render(request, 'admin-add-item.html')







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
        # Get property IDs and their corresponding statuses from the form
        property_data = request.POST.getlist('property_ids[]')

        # Create a dictionary to count the number of "Good" statuses per facultyItem
        good_counts = {}

        # Iterate through the list of property data (property_id,status)
        for data in property_data:
            property_id, status = data.split(',')

            # Use filter to handle multiple entries for the same property_id
            properties = PropertyID.objects.filter(property_id=property_id)
            for property in properties:
                # Update the status to the new status (Good or Defective)
                property.status = status
                property.save()

                # Count how many "Good" properties there are for each facultyItem
                if status == 'Good':
                    # If good, increment the count for the corresponding facultyItem
                    if property.faculty_item.id not in good_counts:
                        good_counts[property.faculty_item.id] = 0
                    good_counts[property.faculty_item.id] += 1

        # Now update the facultyItem quantities based on the number of "Good" properties
        for faculty_item_id, good_count in good_counts.items():
            # Fetch the corresponding facultyItem
            faculty_item = facultyItem.objects.get(id=faculty_item_id)

            # Update the quantity of the facultyItem based on the "Good" statuses
            faculty_item.quantity = good_count  # Quantity is now the count of Good statuses
            faculty_item.save()

        return redirect('admin-item-record')  # Redirect to the appropriate page after the update

    return render(request, 'admin-item-record.html')




@login_required
def item_record(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
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

    return render(request, 'admin-item-record.html', {'page_obj': page_obj, 'total_items': total_items, 'current_show': current_show})



@login_required
def update_item(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
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
            return redirect('admin-item-record')

        # Update item details
        item.name = name
        item.property_id = property_id  # Update property ID if provided
        item.total_quantity = total_quantity
        item.quantity = quantity
        item.save()

        messages.success(request, 'SUCCESS! Item has been updated successfully.')
        return redirect('admin-item-record')

    return redirect('admin-item-record')



@login_required
def delete_item(request, item_id):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")

    if request.method == 'POST':
        item = get_object_or_404(facultyItem, id=item_id)
        item.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)






@login_required
def borrowers(request):
    if not request.user.is_superuser:
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
            return redirect('admin-borrowers')
        elif not date_borrow:
            messages.error(request, 'ERROR! Date Borrow is required.')
            return redirect('admin-borrowers')
        elif not date_return_value:
            messages.error(request, 'ERROR! Date Return is required.')
            return redirect('admin-borrowers')

        try:
            # Parse and validate dates
            date_borrow_parsed = datetime.strptime(date_borrow, "%d %B, %Y").date()
            date_return_parsed = datetime.strptime(date_return_value, "%d %B, %Y").date()

            # Ensure date_borrow is not in the past
            if date_borrow_parsed < timezone.now().date():
                messages.error(request, 'ERROR! Date Borrow cannot be set to a past date.')
                return redirect('admin-borrowers')

            # Ensure date_return is not before date_borrow
            if date_return_parsed < date_borrow_parsed:
                messages.error(request, 'ERROR! Date Return cannot be before Date Borrow.')
                return redirect('admin-borrowers')

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
                return redirect('admin-borrowers')

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
                        return redirect('admin-borrowers')

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
            return redirect('admin-borrow-record')

        except ValueError:
            messages.error(request, 'ERROR! Invalid date format. Please use DD MMMM, YYYY format (e.g., 25 November, 2024).')

    return render(request, 'admin-borrowers.html', {
        'faculty_items': faculty_items,
        'form': form,
        'multimedia_items': multimedia_items,
        'has_available_items': has_available_items,
    })










@login_required
def get_available_quantity(request, item_id):
    try:
        item = facultyItem.objects.get(id=item_id, user=request.user)
        return JsonResponse({"available_quantity": item.quantity})
    except facultyItem.DoesNotExist:
        return JsonResponse({"available_quantity": 0})






















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





from django.db.models import Max, F
from django.db.models.functions import Now, Extract



@login_required
def borrow_record(request):
    if not request.user.is_superuser:
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

    return render(request, 'admin-borrow-record.html', {
        'page_obj': page_obj,
        'total_borrow_requests': total_borrow_requests,
        'current_show': current_show,
        'items': user_items,
    })






# im taking rest not modify yet
@login_required
def borrower_details(request):
    if not request.user.is_superuser:
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

    return render(request, 'admin-borrow-details.html', context)











@login_required
def borrower_details_dashboard(request):
    if not (request.user.is_superuser or request.user.faculty):
        return HttpResponseForbidden("You do not have permission to access this page.")

    student_id = request.GET.get('student_id')
    name = request.GET.get('name')
    date_borrow = request.GET.get('date_borrow')
    date_return = request.GET.get('date_return')
    status = request.GET.get('status')
    purpose = request.GET.get('purpose')
    username = request.GET.get('username')
    user_id = request.user.id

    # Filter BorrowRequest based on the borrow request date
    borrow_requests = BorrowRequest.objects.filter(
        student_id=student_id,
        date_borrow=date_borrow,
        date_return=date_return,
        user=username
        
    ).distinct()

    if not borrow_requests.exists():
        return render(request, '404.html', status=404)

    # Get the first borrow request to fetch the user
    borrow_request = borrow_requests.first()
    handled_by = borrow_request.user.username  # Fetch the username of the associated user

    # Collect items that are not marked as returned across all borrow requests
    all_items = []
    upload_image = None

    for borrow_request in borrow_requests:
        items = borrow_request.facultyitems.filter(is_returned=False)  # Filter by is_returned=False
        all_items.extend(items)  # Append each item to the list
        # Fetch the first image if available
        if borrow_request.upload_image:
            upload_image = borrow_request.upload_image.url

    context = {
        'student_id': student_id,
        'name': name,
        'date_borrow': date_borrow,
        'status': status,
        'all_items': all_items,  # Pass filtered items to the template
        'purpose': purpose,
        'upload_image': upload_image,  # Add upload_image to the context
        'date_return': borrow_request.date_return,
        'handled_by': handled_by  # Pass the username to the context
    }

    return render(request, 'admin-borrow-details-dashboard.html', context)





@login_required
def fetch_borrow_request(request):
    if not request.user.is_superuser:
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

    return render(request, 'admin-update-borrow-request.html', context)







@login_required
def save_borrow_update(request):
    if not request.user.is_superuser:
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
        return redirect('admin-borrow-record')

    messages.error(request, "Something is wrong during update.")
    return redirect('admin-update-borrower')







@login_required
def generate_report(request, id):
    # Ensure only allowed users can access the report
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")

    # Get the specific BorrowRequest by ID
    try:
        borrow_request = BorrowRequest.objects.get(id=id)
        items = borrow_request.facultyitems.select_related('item')  # Fetch related items with facultyItem details
    except BorrowRequest.DoesNotExist:
        return HttpResponseNotFound("BorrowRequest not found.")

    # Structure data for the report
    context = {
        'borrow_request': borrow_request,
        'items': items,  # Ensure you pass the items to the context
        'image_url': request.build_absolute_uri(static('images/logo.png')),
    }

    # Render the HTML template
    html_string = render_to_string('admin-borrower-report.html', context)

    # Configure pdfkit for PDF generation
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

    try:
        options = {
            'no-stop-slow-scripts': '',
            'disable-smart-shrinking': '',
            'enable-local-file-access': '',
            'page-width': '8.5in',          # Set width to 8.5 inches
            'page-height': '13in',          # Set height to 13 inches (Legal size)
            'orientation': 'Portrait',      # Portrait orientation
            'margin-top': '0.5in',          # Adjusted margins for better readability
            'margin-right': '0.5in',
            'margin-bottom': '0.5in',
            'margin-left': '0.5in',
            'dpi': 300,                     # Higher DPI for better print quality
            'zoom': 1.0,                    # Ensure zoom is 1.0 to maintain original size
        }

        pdf = pdfkit.from_string(html_string, False, configuration=config, options=options)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="borrow_report.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"An error occurred: {str(e)}")












def fetch_borrow_request_items(request):
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



from django.db.models import BooleanField, Case, When, Subquery, OuterRef

@login_required
def admin_student_reservation(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")

    # Get the logged-in user's ID
    user_id = request.user.id

    # Filter ReservationItems and annotate reservations
    reservation_items = ReservationItem.objects.filter(user_facultyItem=user_id)
    reserved_request = StudentReservation.objects.filter(
        id__in=reservation_items.values('reservation')
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
                    status="Approved"
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

    return render(request, 'admin-student-reservation.html', {
        'page_obj': page_obj,
        'current_show': current_show,
        'reserved_request': reserved_request
    })



@login_required
def status_update(request, reservation_id):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")

    # Fetch the reservation
    reservation = get_object_or_404(StudentReservation, id=reservation_id)

    # Fetch the items associated with the reservation that the logged-in user is handling
    items = reservation.items.filter(user_facultyItem=request.user)
    

    context = {
        'reservation': reservation,
        'items': items,
    }
    return render(request, 'admin-reservation-status.html', context)





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
        subject = f"Reservation Item Status Updated: {item.item_name}"
        message = f"Dear {reservation.name},\n\nThe status of your reservation item '{item.item_name}' has been updated to '{new_status}'.\n\nNotification: {item.notification}\n\nBest regards,\nYour Reservation Team"
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [reservation.email]

        # Send the email
        send_mail(subject, message, from_email, recipient_list)

        # Redirect to 'admin-student-reservation' if needed
        if reservation.status in ['Approved', 'Denied', 'Completed']:
            response_data['redirect_url'] = reverse('admin-student-reservation')

        return JsonResponse(response_data)

    except ReservationItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found.'})
    
    
    

@login_required
def proceed_borrow(request, reservation_id):
    if not request.user.is_superuser:
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
        return render(request, 'admin-proceed-borrow.html', context)

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
                    return redirect('admin-student-reservation')

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
            return redirect('admin-student-reservation')

        # Display a success message
        if created:
            messages.success(request, "New borrow request created successfully!")
        else:
            messages.success(request, "Borrow request updated successfully!")

        return redirect('admin-borrow-record')

    return redirect('admin-student-reservation')











@login_required
def change_profile(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
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
        return redirect('admin-change-profile')

    default_image_url = '{}{}'.format(settings.MEDIA_URL, 'profile_pics/users.jpg')

    context = {
        'profile_picture': user.profile_picture,
        'username': user.username,
        'default_image_url': default_image_url,
    }
    return render(request, 'admin-change-profile.html', context)


@login_required
def change_password(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")

    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in after changing password
            messages.success(request, 'Your password was successfully updated!')
            return redirect('admin-change-password')  # Redirect to the change password page or another appropriate page
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

    return render(request, 'admin-change-password.html', {'form': form})





def delete_borrow_request(request, borrow_request_id):
    if request.method == "POST":
        # Get the BorrowRequest
        borrow_request = get_object_or_404(BorrowRequest, id=borrow_request_id)

        # Delete associated BorrowRequestItemFaculty objects
        BorrowRequestItemFaculty.objects.filter(borrow_request=borrow_request).delete()

        # Delete the BorrowRequest itself
        borrow_request.delete()

        # Respond with success
        return JsonResponse({"success": True, "message": "Borrow request and related items deleted successfully."})
    return JsonResponse({"success": False, "message": "Invalid request method."})



@csrf_exempt
def delete_reservation(request, reservation_id):
    if request.method == "POST":
        try:
            # Fetch the reservation by ID
            reservation = StudentReservation.objects.get(id=reservation_id)
            # Delete the reservation and cascade delete ReservationItems
            reservation.delete()
            return JsonResponse({"success": True, "message": "Reservation deleted successfully."})
        except StudentReservation.DoesNotExist:
            return JsonResponse({"success": False, "message": "Reservation not found."}, status=404)
    return JsonResponse({"success": False, "message": "Invalid request."}, status=400)





def aa_update_student_reservation(request):
    if request.method == "POST":
        reservation_id = request.POST.get("reservation_id")
        date_return = request.POST.get("date_return")
        course = request.POST.get("course")
        purpose = request.POST.get("purpose")  # Get purpose from the POST data
        upload_image = request.FILES.get("upload_image")

        # Fetch the StudentReservation instance
        reservation = get_object_or_404(StudentReservation, id=reservation_id)

        # Update fields
        reservation.date_return = date_return
        reservation.course = course
        reservation.purpose = purpose  # Update the purpose field
        if upload_image:
            reservation.upload_image = upload_image

        # Save the instance
        reservation.save()

        # Redirect to the desired URL after a successful update
        return redirect('admin-student-reservation')
    else:
        return JsonResponse({"success": False, "message": "Invalid request method."})

