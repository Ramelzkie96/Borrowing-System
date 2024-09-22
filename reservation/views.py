from django.shortcuts import render, redirect
from .models import ReservationUser
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from faculty.models import facultyItem
from django.core.serializers import serialize
from django.contrib.contenttypes.models import ContentType
from .models import StudentReservation
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime



# Create your views here.
def reservation_dashboard(request):
    # Get user_id from session
    user_id = request.session.get('user_id')
    
    if not user_id:
        # Redirect to login if not logged in
        return redirect('reservation-login')
    
    try:
        # Fetch the user based on user_id
        user = ReservationUser.objects.get(id=user_id)
        
        # Get the total number of reservations for this user
        total_reservations = StudentReservation.objects.filter(user_id=user_id, status='Pending').count()
        
        # Get only unread notifications that have been handled by staff
        unread_notifications = StudentReservation.objects.filter(user_id=user_id, is_read=False, is_handled=True).count()
            
        # Fetch reservations for this user, including handled_by and notification, ordered by the most recent first
        reservations = StudentReservation.objects.filter(user_id=user_id, is_handled=True).order_by('-id')

        # Fetch all items from facultyItem model for the selection options
        items = facultyItem.objects.all()
        
        # Pass the user, total_reservations, unread_notifications, and reservations to the template
        context = {
            'user': user,
            'total_reservations': total_reservations,
            'unread_notification': unread_notifications,
            'reservations': reservations,
            'items': items,
        }
        return render(request, 'reservation-dashboard.html', context)
    
    except ReservationUser.DoesNotExist:
        # Handle case where the user is not found
        return redirect('reservation-login')






    
    
@csrf_exempt
def mark_notifications_read(request):
    if request.method == 'POST':
        # Fetch notifications for the user
        user_id = request.session.get('user_id')
        if user_id:
            # Update unread notifications to mark them as read
            StudentReservation.objects.filter(user_id=user_id, is_read=False).update(is_read=True)
            return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)




# @csrf_exempt  # Exempt CSRF check for this view if needed
# def mark_as_read(request, reservation_id):
#     if request.method == 'POST':
#         try:
#             reservation = StudentReservation.objects.get(id=reservation_id)
#             reservation.is_read = True
#             reservation.save()
#             return JsonResponse({'success': True})
#         except StudentReservation.DoesNotExist:
#             return JsonResponse({'success': False, 'message': 'Notification not found'}, status=404)
#     return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def reservation_login(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        password = request.POST.get('password')

        try:
            # Look for the user by student ID
            user = ReservationUser.objects.get(student_id=student_id)

            # Check if the password matches
            if user.check_password(password):
                # Store the user ID in the session
                request.session['user_id'] = user.id
                messages.success(request, "Login successful!")
                return redirect('reservation-dashboard')  # Redirect to dashboard
            else:
                messages.error(request, "Invalid credentials. Please try again.")
        except ReservationUser.DoesNotExist:
            messages.error(request, "Student ID not found.")
        
        return redirect('reservation-login')  # Redirect back to login if there are errors

    return render(request, 'reservation-login.html')


def reservation_register(request):
    student_id_error = password_error = None  # Initialize error variables

    if request.method == 'POST':
        name = request.POST['name']
        student_id = request.POST['student_id']
        year_level = request.POST['year_level']
        email = request.POST['email']
        course = request.POST['course']
        phone_number = request.POST['phone_number']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        # Validation for student_id length
        if len(student_id) > 9 or len(student_id) < 6:
            student_id_error = "Student ID must be between 6 and 9 characters long."
            
        # Check if student_id already exists
        if ReservationUser.objects.filter(student_id=student_id).exists():
            student_id_error = "Student ID already exists."

        # Validation for passwords matching
        if password != confirm_password:
            password_error = "Passwords do not match."

        # If there are errors, display a general error message
        if student_id_error or password_error:
            messages.error(request, "Please correct the errors below.")
            return render(request, 'reservation-register.html', {
                'student_id_error': student_id_error,
                'password_error': password_error,
                'request': request,
            })

        # If no errors, save the new user to the database
        new_user = ReservationUser(
            name=name,
            student_id=student_id,
            year_level=year_level,
            email=email,
            phone_number=phone_number,
            course=course,
            password=password,  # Passwords will be hashed in the model's save method
        )
        new_user.save()

        # Store the user ID in the session
        request.session['user_id'] = new_user.id
        messages.success(request, "Registration successful!")
        return redirect('reservation-dashboard')  # Redirect to dashboard

    return render(request, 'reservation-register.html')







def logout(request):
    try:
        del request.session['user_id']
    except KeyError:
        pass  # If no user ID in session, do nothing
    messages.success(request, "Logged out successfully!")
    return redirect('reservation-login')



def submit_reservation(request):
    if request.method == 'POST':
        # Retrieve form data
        student_id = request.POST.get('student_id')
        name = request.POST.get('name')
        course = request.POST.get('course')
        year_level = request.POST.get('year')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone')
        reserve_date = request.POST.get('datepicker')
        item_id = request.POST.get('itemm')
        quantity = int(request.POST.get('quantityy'))  # Convert quantity to integer
        purpose = request.POST.get('description')

        # Retrieve the user_id from the session
        user_id = request.session.get('user_id')

        if not user_id:
            messages.error(request, "User not logged in!")
            return redirect('reservation-login')  # Redirect to login if user is not logged in

        # Validate reserve_date
        if not reserve_date:
            messages.error(request, "Reservation date is required.")
            return redirect('reservation-dashboard')

        try:
            # Parse the date
            reserve_date = datetime.strptime(reserve_date, '%d %B, %Y').date()  # Ensure it's a date object
            if reserve_date < datetime.now().date():
                messages.error(request, "Reservation date cannot be in the past.")
                return redirect('reservation-dashboard')
        except ValueError:
            messages.error(request, "Invalid reservation date format.")
            return redirect('reservation-dashboard')

        try:
            # Fetch the item and get its user_id
            item = facultyItem.objects.get(id=item_id)
            item_user_id = item.user_id  # Get the user_id from the facultyItem model
        except facultyItem.DoesNotExist:
            messages.error(request, "Selected item does not exist.")
            return redirect('reservation-dashboard')

        # Check if the requested quantity exceeds available quantity
        if quantity > item.quantity:
            messages.error(request, f"Only {item.quantity} items available for {item.name}.")
            return redirect('reservation-dashboard')

        # Create the reservation
        reservation = StudentReservation.objects.create(
            student_id=student_id,
            name=name,
            course=course,
            year_level=year_level,
            email=email,
            phone_number=phone_number,
            reserve_date=reserve_date,
            content_type=ContentType.objects.get_for_model(facultyItem),
            object_id=item_id,
            quantity=quantity,
            purpose=purpose,
            status='Pending',
            user_id=user_id,
            user_type=item_user_id, 
        )

        messages.success(request, "Item reserved successfully!")
        return redirect('reservation-dashboard')

    return redirect('reservation-dashboard')  # Handle non-POST requests






def reservation_status(request):
    user_id = request.session.get('user_id')  # Retrieve user_id from session

    if not user_id:
        return redirect('reservation-login')  # Redirect to login if no user_id

    try:
        # Fetch the ReservationUser instance
        user = ReservationUser.objects.get(id=user_id)

        # Fetch reservations for the logged-in user
        student_reservations = StudentReservation.objects.filter(user_id=user.id).order_by('-id')
        
        # Get only unread notifications that have been handled by staff
        unread_notification = StudentReservation.objects.filter(user_id=user_id, is_read=False, is_handled=True).count()
        
        # Fetch reservations for this user, including handled_by and notification, ordered by the most recent first
        reservations = StudentReservation.objects.filter(user_id=user_id, is_handled=True).order_by('-id')

        # Handle pagination
        show_entries = request.GET.get('show', 'all')
        if show_entries == 'all':
            paginator = Paginator(student_reservations, 1000000)  # Large number to ensure all items are on one page
            current_show = 'all'
        else:
            paginator = Paginator(student_reservations, int(show_entries))
            current_show = int(show_entries)

        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # Pass the user and reservations to the template
        context = {
            'user': user,
            'student_reservations': page_obj,
            'reservations': reservations,
            'unread_notification': unread_notification,
            'current_show': current_show
        }
        return render(request, 'reservation-status.html', context)
    
    except ReservationUser.DoesNotExist:
        # Handle case where the user is not found
        return redirect('reservation-login')  # Redirect to login if the user does not exist

