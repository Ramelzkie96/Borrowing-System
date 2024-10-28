from django.shortcuts import render, redirect 
from .forms import LoginForm
from django.contrib.auth import authenticate, login, logout 
from django.contrib.auth.decorators import login_required 
from functools import wraps
from faculty.models import BorrowRequest, facultyItem 
from django.contrib import messages 
from django.core.paginator import Paginator
from .models import User
from django.contrib.auth import get_user_model 
from django.contrib.auth.views import PasswordResetView 
from reservation.models import StudentReservation
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden  
from django.utils import timezone 
from django.views.decorators.http import require_POST 
from django.core.mail import send_mail 
from django.views.decorators.csrf import csrf_exempt  
from django.conf import settings 
from faculty.forms import EmailNotificationForm, BorrowRequestMultimediaForm
from django.utils.timezone import now
from django.contrib.contenttypes.models import ContentType  
from datetime import datetime
from django.db.models import Q 
import json
import os
from django.templatetags.static import static
import pdfkit
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash 
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
    borrow_request_count = BorrowRequest.objects.filter(user=user, status='Borrowed').count()

    # Count of items with status 'Returned/Defect Item' belonging to the logged-in user
    defect_item_count = BorrowRequest.objects.filter(user=user, status='Returned/Defect Item').count()

    # Count of total items belonging to the logged-in user
    faculty_item_count = facultyItem.objects.filter(user=user).count()
    
    # Count of all StudentReservation items with status 'Pending' that match the user_type
    student_reservation_count = StudentReservation.objects.filter(status='Pending', user_type=user.id).count()

    # Fetch all BorrowRequests with status 'Borrowed' for the logged-in user, ordered by most recent first
    borrowed_requests = BorrowRequest.objects.filter(status='Borrowed').order_by('-id')

    # Render the template with the counts and the list of borrowed requests
    return render(request, 'dashboard.html', {
        'borrow_request_count': borrow_request_count,
        'defect_item_count': defect_item_count,
        'faculty_item_count': faculty_item_count,
        'student_reservation_count': student_reservation_count,
        'borrowed_requests': borrowed_requests,
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
    
    # Count of borrowed items with status 'Borrowed' belonging to the logged-in user
    borrow_request_count = BorrowRequest.objects.filter(user=current_user, status='Borrowed').count()
    
    # Fetch all users
    borrow_request = BorrowRequest.objects.filter(status='Borrowed').order_by('-id')
    
    # Count of total items belonging to the logged-in user
    faculty_item_count = facultyItem.objects.filter(user=current_user).count()
    
    # Fetch all items from facultyItem model associated with the logged-in user
    user_items = facultyItem.objects.filter(user=request.user)
    
    # Count of items with status 'Returned/Defect Item' belonging to the logged-in user
    defect_item_count = BorrowRequest.objects.filter(user=current_user, status='Returned/Defect Item').count()
    
    # Count of all StudentReservation items with status 'Pending' that match the user_type
    student_reservation_count = StudentReservation.objects.filter(status='Pending', user_type=current_user.id).count()

    
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
        'defect_item_count': defect_item_count,
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
        
        
        
        
@require_POST
def return_item(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'You do not have permission to access this page.'}, status=403)
    
    request_id = request.POST.get('request_id')
    date_return = request.POST.get('date_return')
    status = request.POST.get('status')
    note = request.POST.get('note')

    if not date_return:
        return JsonResponse({'field_errors': {'dateReturn': 'Date returned is required.'}}, status=400)

    try:
        borrow_request = get_object_or_404(BorrowRequest, pk=request_id)
        current_status = borrow_request.status
        
        if current_status == 'Borrowed' and status not in ['Returned', 'Returned/Defect Item']:
            return JsonResponse({'field_errors': {'status': 'Status Borrowed must be changed to Returned or Returned/Defect Item.'}}, status=400)

        elif current_status in ['Returned', 'Returned/Defect Item'] and status == 'Borrowed':
            item = borrow_request.content_object
            item.quantity -= borrow_request.quantity
            item.save()
            borrow_request.date_return = date_return
            borrow_request.status = status
            borrow_request.note = note
            borrow_request.save()
            return JsonResponse({'success': 'Item set to Borrowed successfully!'})

        if current_status == 'Borrowed' and status in ['Returned', 'Returned/Defect Item']:
            item = borrow_request.content_object
            item.quantity += borrow_request.quantity
            item.save()

        # Update common fields
        borrow_request.date_return = date_return
        borrow_request.status = status
        borrow_request.note = note
        
        if status in ['Returned', 'Returned/Defect Item']:
            borrow_request.created_at = timezone.now()  # Reset timestamp
        borrow_request.save()

        messages.success(request, ('Item returned successfully!'))
        return JsonResponse({'success': 'Item returned successfully!'})

    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)







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
                return redirect('admin-dashboard')  # Use the direct URL
            except Exception as e:
                # Add an error message and redirect
                messages.error(request, f'Error sending email: {str(e)}')
                return redirect('admin-dashboard')  # Use the direct URL
        else:
            # Add an error message for invalid form data and redirect
            messages.error(request, 'Invalid form data.')
            return redirect('admin-dashboard')  # Use the direct URL
    
    # Handle cases where the request method is not POST
    messages.error(request, 'Invalid request method.')
    return redirect('admin-dashboard')  # Use the direct URL



@login_required
def add_item(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
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
            return redirect('admin-item-record')  # Redirect to item_record after adding item
        else:
            messages.error(request, 'ERROR! Please fill out all fields.')

        # Pass the submitted data back to the template in case of an error
        return render(request, 'admin-add-item.html', {'name': name, 'description': description, 'quantity': quantity})

    return render(request, 'admin-add-item.html')



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
        description = request.POST.get('description')
        quantity = request.POST.get('quantity')

        # Retrieve the item and ensure it belongs to the current user
        item = get_object_or_404(facultyItem, id=item_id)

        if item.user_id != request.user.id:  # Ensure the item belongs to the current user
            messages.error(request, "You are not authorized to update this item.")
            return redirect('admin-item-record')

        # Update item details
        item.name = name
        item.description = description
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
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    multimedia_items = facultyItem.objects.filter(user=request.user)
    items = list(multimedia_items)
    
    has_available_items = any(item.quantity > 0 for item in items)
    selected_item_has_zero_quantity = False

    if request.method == 'POST':
        content_type = ContentType.objects.get_for_model(facultyItem)
        form = BorrowRequestMultimediaForm(request.POST, user=request.user, content_type=content_type)
        
        if form.is_valid():
            selected_item = form.cleaned_data['item']
            requested_quantity = form.cleaned_data['quantity']
            date_borrow = form.cleaned_data['date_borrow']
            
            # First, attempt to get the value of the radio button
            borrower_type = request.POST.get('borrower_type', '')  # Get 'borrower_type', or default to empty string

            # If the 'other_borrower_type' input is filled, override the radio button value
            other_borrower_type = request.POST.get('other_borrower_type', '').strip()
            if other_borrower_type:
                borrower_type = other_borrower_type  # Use the custom input

            # Validate the date_borrow field
            if not date_borrow:
                form.add_error('date_borrow', 'This field is required.')
                messages.error(request, 'ERROR! Date Borrow is required!')
            else:
                # Check if the date_borrow is in the past (convert to date object for comparison)
                date_borrow_obj = datetime.strptime(date_borrow, "%d %B, %Y").date()
                if date_borrow_obj < now().date():
                    form.add_error('date_borrow', 'Date Borrow cannot be in the past.')
                    messages.error(request, 'ERROR! Date Borrow cannot be set to a past date.')
                elif selected_item.quantity >= requested_quantity:
                    borrow_request = form.save(commit=False)
                    borrow_request.content_type = content_type
                    borrow_request.object_id = selected_item.id
                    borrow_request.status = 'Borrowed'
                    borrow_request.borrower_type = borrower_type  # Save the selected or custom borrower type
                    borrow_request.user = request.user  # Set user to the currently logged-in user
                    borrow_request.save()
                    selected_item.quantity -= requested_quantity
                    selected_item.save()
                    messages.success(request, 'SUCCESS! Borrow request has been submitted.')
                    return redirect('admin-borrow-record')
                else:
                    messages.error(request, 'ERROR! No more item available')
                    selected_item_has_zero_quantity = selected_item.quantity == 0
        else:
            messages.error(request, 'ERROR! Please correct the errors below.')
    else:
        content_type = ContentType.objects.get_for_model(facultyItem)
        form = BorrowRequestMultimediaForm(user=request.user, content_type=content_type)

    return render(request, 'admin-borrowers.html', {
        'form': form,
        'has_available_items': has_available_items,
        'selected_item_has_zero_quantity': selected_item_has_zero_quantity,
    })
    
    
@login_required
def borrow_record(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Fetch borrow requests that are either created by the user (borrower) or handled by the user (faculty handler)
    borrow_requests = BorrowRequest.objects.filter(
        Q(user=request.user) | Q(handled_by=request.user)  # Include requests where the user is either the borrower or handler
    ).exclude(status__in=["Returned", "Returned/Defect Item"]).order_by('-id')

    total_borrow_requests = borrow_requests.count()

    # Fetch all items from facultyItem model associated with the logged-in user
    user_items = facultyItem.objects.filter(user=request.user)

    # Pagination setup
    show_entries = request.GET.get('show', 'all')
    if show_entries == 'all':
        paginator = Paginator(borrow_requests, 1000000)  # Large number to show all records on one page
        current_show = 'all'
    else:
        paginator = Paginator(borrow_requests, int(show_entries))
        current_show = int(show_entries)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin-borrow-record.html', {
        'page_obj': page_obj,
        'total_borrow_requests': total_borrow_requests,
        'current_show': current_show,
        'items': user_items,  # Pass only the user's items to the template
    })
    
    
@login_required
def borrow_more_item(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    if request.method == 'POST':
        # Get the original borrow request based on the request ID from the form
        request_id = request.POST.get('request_id')
        original_request = get_object_or_404(BorrowRequest, id=request_id)

        # Ensure that the logged-in user is the owner of the original borrow request
        if original_request.user != request.user:
            return HttpResponseForbidden("You are not allowed to access this request.")

        # Get the new values from the modal form
        date_borrow = request.POST.get('date_borrow')
        item_id = request.POST.get('item')
        quantity = int(request.POST.get('quantity'))  # Convert to integer

        # Find the selected item in facultyItem based on the user and item ID
        item = get_object_or_404(facultyItem, id=item_id, user=request.user)

        # Validate that the requested quantity does not exceed the available quantity
        if quantity > item.quantity:
            messages.error(request, f"No more quantity available for {item.name}!")
            return redirect('admin-borrow-record')

        # Create a new BorrowRequest based on the existing one
        new_borrow_request = BorrowRequest.objects.create(
            student_id=original_request.student_id,
            name=original_request.name,
            course=original_request.course,
            year=original_request.year,
            email=original_request.email,
            phone=original_request.phone,
            date_borrow=date_borrow,
            content_type=original_request.content_type,  # Same content type
            object_id=item.id,  # New faculty item id
            quantity=quantity,
            purpose=original_request.purpose,
            status='Borrowed',  # Set status to 'Pending' or another default value
            note=original_request.note,
            user=request.user,
            borrower_type=original_request.borrower_type
        )

        # Update the item quantity by subtracting the borrowed quantity
        item.quantity -= quantity
        item.save()

        # Display success message
        messages.success(request, "Item borrowed successfully.")
        
    # If not a POST request, redirect to the borrow record page
    return redirect('admin-borrow-record')


@login_required
def update_borrow_request(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    if request.method == 'POST':
        borrow_id = request.POST.get('id')
        student_id = request.POST.get('student_id')
        name = request.POST.get('name')
        course = request.POST.get('course')
        year = request.POST.get('year')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        item_id = request.POST.get('itemm')
        new_quantity = int(request.POST.get('quantityy'))
        date = request.POST.get('datepicker')
        purpose = request.POST.get('description')

        # Get borrower_type values
        borrower_type = request.POST.get('borrower_type')
        other_borrower_type = request.POST.get('other_borrower_type', '').strip()  # Default to empty string

        # If the "Others" field is filled, use its value
        if other_borrower_type:
            borrower_type = other_borrower_type

        try:
            # Get the BorrowRequest object, ensure it's tied to the logged-in user
            borrow_request = get_object_or_404(BorrowRequest, id=borrow_id, user=request.user)
            
            # Get the content type and ensure the item also belongs to the logged-in user
            content_type = ContentType.objects.get_for_model(borrow_request.content_object)
            item = content_type.get_object_for_this_type(id=item_id, user=request.user)

            # Calculate adjusted quantities
            original_quantity = borrow_request.quantity
            original_item_quantity = item.quantity
            borrowed_quantity_change = new_quantity - original_quantity
            item_quantity_change = original_item_quantity - borrowed_quantity_change

            # Validate quantity change
            if new_quantity <= 0:
                messages.error(request, 'Quantity must be greater than zero.')
                return redirect('admin-borrow-record')

            if item_quantity_change < 0:
                messages.error(request, f'Not enough quantity available for {item.name}.')
                return redirect('admin-borrow-record')

            # Update BorrowRequest with the new values
            borrow_request.student_id = student_id
            borrow_request.name = name
            borrow_request.course = course
            borrow_request.year = year
            borrow_request.email = email
            borrow_request.phone = phone
            borrow_request.content_object = item
            borrow_request.quantity = new_quantity
            borrow_request.date_borrow = date
            borrow_request.purpose = purpose
            borrow_request.borrower_type = borrower_type  # Update borrower_type here
            borrow_request.save()

            # Update the item quantity
            item.quantity = item_quantity_change
            item.save()

            # Success message
            messages.success(request, f'Borrow request for {item.name} has been updated.')
            return redirect('admin-borrow-record')

        except Exception as e:
            # Handle any errors and show the error message
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('admin-borrow-record')

    else:
        # Handle invalid request methods
        messages.error(request, 'Invalid request method.')
        return redirect('admin-borrow-record')



@login_required
def generate_report(request, student_id):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Fetch all BorrowRequests for the specific student ID and order by latest date_borrow
    borrowers = BorrowRequest.objects.filter(
        Q(student_id=student_id) & (Q(user=request.user) | Q(handled_by=request.user))
    ).order_by('-id')[:5]
    
    # Get the latest borrow record
    latest_borrow = borrowers.first() 
    
    image_url = request.build_absolute_uri(static('images/logo.png'))
    
    # Pass the data to the template
    context = {
        'borrowers': borrowers,
        'student_id': student_id,
        'latest_borrow': latest_borrow,
        'image_url': image_url,
    }
    
    # Render the HTML template
    html_string = render_to_string('borrower-report.html', context)

    # Configure pdfkit
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

    # Generate PDF
    try:
        options = {
            'no-stop-slow-scripts': '',
            'disable-smart-shrinking': '',
            'enable-local-file-access': '',  # Allows local file access
        }
        
        pdf = pdfkit.from_string(html_string, False, configuration=config, options=options)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="borrow_report.pdf"'  # Open in browser
        return response
    except Exception as e:
        return HttpResponse(f"An error occurred: {str(e)}")
    
    
@login_required
def returned_record(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Fetch returned requests handled by or created by the current user
    returned_requests = BorrowRequest.objects.filter(
        Q(user=request.user) | Q(handled_by=request.user), 
        status__in=["Returned", "Returned/Defect Item"]
    ).order_by('-id')

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

    return render(request, 'admin-returned-record.html', {
        'page_obj': page_obj,
        'current_show': current_show,
        'returned_requests': returned_requests,
    })
    
    
@login_required
def admin_student_reservation(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Get the logged-in user's ID
    user_id = request.user.id  # Use request.user.id to directly get the logged-in user's ID

    # Retrieve all faculty items associated with the logged-in user
    user_faculty_items = facultyItem.objects.filter(user_id=user_id)

    # Get the IDs of the faculty items associated with the logged-in user
    faculty_item_ids = user_faculty_items.values_list('id', flat=True)

    # Filter to show reservations related to the logged-in user and user type
    reserved_request = StudentReservation.objects.filter(
        user_id=user_id,  # Ensure only reservations linked to the logged-in user are shown
        content_type__model='facultyitem',  # Assuming content_type corresponds to the facultyItem model
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

    return render(request, 'admin-student-reservation.html', {
        'page_obj': page_obj,
        'current_show': current_show,
        'reserved_request': reserved_request
    })



@login_required
def update_reservation_status(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
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
        return redirect('admin-student-reservation')  # Adjust this to the appropriate URL name

    # Handle cases where the request method is not POST
    messages.error(request, 'Invalid request')
    return redirect('admin-student-reservation')  # Adjust this to the appropriate URL name


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