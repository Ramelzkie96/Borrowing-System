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
from faculty.forms import EmailNotificationForm
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
                    messages.error(request, "No faculty role assigned!")
                    msg = 'No faculty role assigned'
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
    
    return render(request, 'admin-login.html')


@login_required 
def admin_dashboard(request):
    total_users = User.objects.count()  # Count all users
    current_user = request.user  # Get the logged-in user
    
    # Count of borrowed items with status 'Borrowed' belonging to the logged-in user
    borrow_request_count = BorrowRequest.objects.filter(user=current_user, status='Borrowed').count()
    
    # Fetch all users
    borrow_request = BorrowRequest.objects.filter(status='Borrowed').order_by('-id')
    
    # Count of total items belonging to the logged-in user
    faculty_item_count = facultyItem.objects.filter(user=current_user).count()

    
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
    }
    return render(request, 'admin-dashboard.html', context)



def admin_users(request):
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



def delete_user(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        
        try:
            user.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        
        
        
@require_POST
def return_item(request):
    # Restrict access to faculty users only
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    request_id = request.POST.get('request_id')
    date_return = request.POST.get('date_return')
    status = request.POST.get('status')
    note = request.POST.get('note')

    if not date_return:
        messages.error(request, 'Date returned is required.')
        return redirect('admin-dashboard')

    try:
        borrow_request = get_object_or_404(BorrowRequest, pk=request_id)
        current_status = borrow_request.status
        
        if current_status == 'Borrowed' and status not in ['Returned', 'Returned/Defect Item']:
            messages.error(request, 'Status Borrowed must be changed to Returned or Returned/Defect Item.')
            return redirect('admin-dashboard')

        elif current_status in ['Returned', 'Returned/Defect Item'] and status == 'Borrowed':
            item = borrow_request.content_object
            item.quantity -= borrow_request.quantity
            item.save()
            borrow_request.date_return = date_return
            borrow_request.status = status
            borrow_request.note = note
            borrow_request.save()
            messages.success(request, 'Item set to Borrowed successfully!')
            return redirect('admin-dashboard')

        if current_status == 'Borrowed' and status in ['Returned', 'Returned/Defect Item']:
            item = borrow_request.content_object
            item.quantity += borrow_request.quantity
            item.save()

        # Update common fields
        borrow_request.date_return = date_return
        borrow_request.status = status
        borrow_request.note = note
        
        # Reset the timestamp when status is updated to Returned or Returned/Defect Item
        if status in ['Returned', 'Returned/Defect Item']:
            borrow_request.created_at = timezone.now()  # Reset timestamp
        borrow_request.save()

        messages.success(request, 'Item returned successfully!')
        return redirect('admin-dashboard')

    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('admin-dashboard')

    messages.error(request, 'Invalid request method.')
    return redirect('admin-dashboard')



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