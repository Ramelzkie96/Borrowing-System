from django.shortcuts import render, redirect
from .models import ReservationUser, ReservationItem
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
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password, make_password
import json
import re
from django.utils.encoding import force_str
from django.core.mail import EmailMultiAlternatives
from .tokens import reservation_token_generator
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.http import urlsafe_base64_decode
from django.http import JsonResponse
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_list_or_404
from django.views.decorators.http import require_POST



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

        # Fetch only unread notifications for the badge count
        reservation_items = ReservationItem.objects.filter(
            reservation__user_id=user_id, is_handled=True
        ).order_by('-handled_by', '-id')

  

        # Pass the user, total_reservations, reservation_items, unread_count to the template
        context = {
            'user': user,
            'total_reservations': total_reservations,
            'reservation_items': reservation_items,
        }
        return render(request, 'reservation-dashboard.html', context)
    
    except ReservationUser.DoesNotExist:
        # Handle case where the user is not found
        return redirect('reservation-login')









    
    



@csrf_exempt
def delete_notification(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')  # Expecting the ReservationItem ID in the request data

            # Check if the user is authenticated
            user_id = request.session.get('user_id')
            if user_id:
                # Find the reservation item related to the user via the linked StudentReservation
                reservation_item = ReservationItem.objects.filter(id=item_id, reservation__user_id=user_id).first()
                
                if reservation_item:
                    # Clear the notification-related fields on the ReservationItem
                    reservation_item.handled_by_profile_picture = None
                    reservation_item.handled_by = None
                    reservation_item.notification = None
                    reservation_item.is_handled = False  # Set is_handled to False
                    reservation_item.save()
                    
                    return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'message': 'Notification not found or unauthorized'}, status=400)
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False}, status=400)


def reservation_login(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        password = request.POST.get('password')

        # Remove hyphens from the input student ID
        sanitized_student_id = student_id.replace("-", "")

        try:
            # Search for the user by sanitizing the stored student IDs (removing hyphens)
            user = ReservationUser.objects.get(student_id=sanitized_student_id)

            # Debugging outputs
            print(f"Attempting login for: {sanitized_student_id}")
            print(f"Input Password: {password}")
            print(f"Stored Hashed Password: {user.password}")

            if user.check_password(password):
                request.session['user_id'] = user.id
                messages.success(request, "Login successful!")
                return redirect('reservation-dashboard')
            else:
                messages.error(request, "Invalid credentials. Please try again.")
        except ReservationUser.DoesNotExist:
            messages.error(request, "Student ID not found.")

        return redirect('reservation-login')

    return render(request, 'reservation-login.html')






def reservation_register(request):
    student_id_error = password_error = email_error = None  # Initialize error variables

    if request.method == 'POST':
        name = request.POST['name']
        student_id = request.POST['student_id']
        year_level = request.POST['year_level']
        email = request.POST['email']
        course = request.POST['course']
        phone_number = request.POST['phone_number']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        # Remove hyphens from the student ID
        sanitized_student_id = student_id.replace("-", "")

        # Validation: Ensure student_id is exactly 9 digits long after removing hyphens
        if not re.match(r'^\d{9}$', sanitized_student_id):
            student_id_error = "Student ID must contain exactly 9 digits. Example: 21-****-*** or 21*******"

        # Check if student_id already exists (using the sanitized version)
        if ReservationUser.objects.filter(student_id=sanitized_student_id).exists():
            student_id_error = "Student ID already exists."

        # Check if email already exists
        if ReservationUser.objects.filter(email=email).exists():
            email_error = "Email already exists."

        # Validation for passwords matching
        if password != confirm_password:
            password_error = "Passwords do not match."

        # If there are errors, display a general error message
        if student_id_error or email_error or password_error:
            messages.error(request, "Please correct the errors above.")
            return render(request, 'reservation-register.html', {
                'student_id_error': student_id_error,
                'email_error': email_error,
                'password_error': password_error,
                'request': request,
            })

        # If no errors, save the new user to the database
        new_user = ReservationUser(
            name=name,
            student_id=sanitized_student_id,  # Save the sanitized version of student_id
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
        purpose = request.POST.get('purpose')
        item_ids = request.POST.getlist('itemm')
        quantities = request.POST.getlist('quantityy')
        descriptions = request.POST.getlist('description')
        
        # Retrieve the user_id from the session
        user_id = request.session.get('user_id')
        if not user_id:
            messages.error(request, "User not logged in!")
            return redirect('reservation-login')  # Redirect to login if user is not logged in

        # Retrieve the logged-in user instance
        logged_in_user = ReservationUser.objects.get(id=user_id)

        # Validate that reserve_date is provided
        if not reserve_date:
            messages.error(request, "Please select a reservation date.")
            return redirect('reservation-dashboard')  # Redirect back to the reservation form

        try:
            with transaction.atomic():
                # Check if a reservation already exists for this student_id and reserve_date
                reservation, created = StudentReservation.objects.get_or_create(
                    student_id=student_id,
                    reserve_date=reserve_date,
                    defaults={
                        'name': name,
                        'course': course,
                        'year_level': year_level,
                        'email': email,
                        'phone_number': phone_number,
                        'purpose': purpose,
                        'status': 'Pending',
                        'user': logged_in_user,
                    }
                )

                # Loop through items and handle ReservationItem entries
                for item_id, quantity, description in zip(item_ids, quantities, descriptions):
                    quantity = int(quantity)
                    item = facultyItem.objects.get(id=item_id)

                    # Check if the requested quantity exceeds available quantity
                    if quantity > item.quantity:
                        messages.error(request, f"Only {item.quantity} items available for {item.name}.")
                        return redirect('reservation-dashboard')

                    # Check if ReservationItem for this item_name already exists in the reservation
                    reservation_item, item_created = ReservationItem.objects.get_or_create(
                        reservation=reservation,
                        item_name=item.name,
                        defaults={
                            'user': logged_in_user,  # Associate with the logged-in user
                            'description': description,
                            'quantity': quantity,
                            'status': 'Pending',
                            'user_facultyItem': item.user,  # Store the user from facultyItem
                        }
                    )

                    if not item_created:
                        # If the item exists, increment the quantity
                        reservation_item.quantity += quantity
                        reservation_item.save()

                    # No need to store the handled_by field, as requested
                    item.save()

            messages.success(request, "Items reserved successfully!")
            return redirect('reservation-dashboard')

        except facultyItem.DoesNotExist:
            messages.error(request, f"Item with ID {item_id} does not exist.")
            return redirect('reservation-dashboard')
        except ValueError:
            messages.error(request, "Invalid quantity entered.")
            return redirect('reservation-dashboard')

    return redirect('reservation-dashboard')





    

def get_faculty_items(request):
    items = facultyItem.objects.all().values('id', 'name', 'quantity')
    item_list = list(items)
    return JsonResponse(item_list, safe=False)




def reservation_status(request):
    user_id = request.session.get('user_id')  # Retrieve user_id from session

    if not user_id:
        return redirect('reservation-login')  # Redirect to login if no user_id

    try:
        # Fetch the ReservationUser instance
        user = ReservationUser.objects.get(id=user_id)

        # Fetch reservations for the logged-in user
        student_reservations = StudentReservation.objects.filter(user_id=user.id).order_by('-id')
        
        # Fetch only unread notifications for the badge count
        reservation_items = ReservationItem.objects.filter(
            reservation__user_id=user_id, is_handled=True
        ).order_by('-handled_by', '-id')
        
        

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
            'reservation_items': reservation_items,
            'current_show': current_show
        }
        return render(request, 'reservation-status.html', context)
    
    except ReservationUser.DoesNotExist:
        # Handle case where the user is not found
        return redirect('reservation-login')  # Redirect to login if the user does not exist
    
    
def reservation_items(request, reservation_id): 
    # Get ReservationItem entries for the selected reservation
    items = ReservationItem.objects.filter(reservation__id=reservation_id).values(
        'item_name', 'description', 'quantity', 'status'
    )
    return JsonResponse(list(items), safe=False)





def reservation_edit(request, reservation_id):
    user_id = request.session.get('user_id')  # Retrieve user_id from session

    if not user_id:
        return redirect('reservation-login')  # Redirect to login if no user_id
    
    
    # Fetch the user based on user_id
    user = ReservationUser.objects.get(id=user_id)

    # Retrieve the StudentReservation instance for the specific user
    reservation = get_object_or_404(StudentReservation, id=reservation_id, user_id=user_id)

    # Retrieve related ReservationItem instances for the specific reservation
    reservation_items = reservation.items.all()

    # Retrieve all faculty items to display in the form (assuming you want these for item selection)
    all_faculty_items = facultyItem.objects.all()
    
    # Fetch only unread notifications for the badge count
    reservation_itemss = ReservationItem.objects.filter(
        reservation__user_id=user_id, is_handled=True
    ).order_by('-handled_by', '-id')

    # Prepare reservation items with IDs and other fields for the form
    reservation_items_data = [
        {
            'id': item.id,
            'item_name': item.item_name,
            'description': item.description,
            'quantity': item.quantity
        } for item in reservation_items
    ]

    # Context to be passed to the template for rendering the reservation edit form
    context = {
        'borrow_request_id': reservation.id,
        'student_id': reservation.student_id,
        'name': reservation.name,
        'course': reservation.course,
        'year_level': reservation.year_level,
        'email': reservation.email,
        'phone': reservation.phone_number,
        'user': user,
        'reserve_date': reservation.reserve_date,
        'purpose': reservation.purpose,
        'status': reservation.status,
        'reservation_items': reservation_items_data,  # Use prepared data for the items
        'reservation_itemss': reservation_itemss,
        'all_faculty_items': all_faculty_items,  # Pass all faculty items for selection in the form
    }

    return render(request, 'reservation-edit.html', context)




def reservation_update(request):
    if request.method == 'POST':
        reservation_id = request.POST.get('id')
        user_id = request.session.get('user_id')

        # Fetch reservation
        reservation = get_object_or_404(StudentReservation, id=reservation_id, user_id=user_id)

        # Update the main reservation details
        reservation.student_id = request.POST.get('student_id')
        reservation.name = request.POST.get('name')
        reservation.course = request.POST.get('course')
        reservation.year_level = request.POST.get('year')
        reservation.email = request.POST.get('email')
        reservation.phone_number = request.POST.get('phone')
        reservation.reserve_date = request.POST.get('datepicker')
        reservation.purpose = request.POST.get('purpose')
        reservation.save()

        # Process reservation items
        items_data = request.POST
        item_count = len([key for key in items_data if key.startswith('items[')])

        for i in range(item_count):
            item_id = items_data.get(f'items[{i}][id]')
            item_name = items_data.get(f'items[{i}][item_name]')
            quantity = items_data.get(f'items[{i}][quantity]')
            description = items_data.get(f'items[{i}][description]')

            # Check if item_name is provided; skip if empty to avoid IntegrityError
            if not item_name:
                continue

            # Update existing item or create a new one if item_id is not found
            if item_id:
                reservation_item = get_object_or_404(ReservationItem, id=item_id, reservation=reservation)
                reservation_item.item_name = item_name
                reservation_item.quantity = int(quantity) if quantity else 0
                reservation_item.description = description
                reservation_item.save()
            else:
                ReservationItem.objects.create(
                    reservation=reservation,
                    item_name=item_name,
                    quantity=int(quantity) if quantity else 0,
                    description=description,
                )

        messages.success(request, "Reservation updated successfully!")
        return redirect('reservation-status')

    return redirect('reservation-edit', reservation_id=reservation_id)








def get_available_stock(request, item_id):
    try:
        item = facultyItem.objects.get(id=item_id)
        return JsonResponse({'available_stock': item.quantity})
    except facultyItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)





def changeprofile(request):
    user_id = request.session.get('user_id')  # Retrieve user_id from session

    if not user_id:
        return redirect('reservation-login')  # Redirect to login if no user_id
    
    try:
        # Fetch the ReservationUser instance
        user = ReservationUser.objects.get(id=user_id)
        
        # Fetch only unread notifications for the badge count
        reservation_items = ReservationItem.objects.filter(
            reservation__user_id=user_id, is_handled=True
        ).order_by('-handled_by', '-id')

        if request.method == 'POST':
            # Retrieve form data
            name = request.POST.get('name')
            student_id = request.POST.get('student_id')
            email = request.POST.get('email')

            # Update user fields
            user.name = name
            user.student_id = student_id
            user.email = email

            # If a new profile image is uploaded, update the profile image
            if 'profilePicture' in request.FILES:
                user.profile_image = request.FILES['profilePicture']

            # Save changes to the user profile
            user.save()

            # Add a success message
            messages.success(request, 'Profile updated successfully!')
            return redirect('reservation-change-profile')  # Redirect to the profile page or another page
        
        # Handle GET request (render the form)
        context = {
            'user': user,
            'profile_picture': user.profile_image.url if user.profile_image else None,
            'default_image_url': '/media/profile_pics/users.jpg',  # URL to default image
            'reservation_items': reservation_items
        }
        return render(request, 'reservation-changeprofile.html', context)
    
    except ReservationUser.DoesNotExist:
        return redirect('reservation-login')
    
    
    
def changepassword(request):
    user_id = request.session.get('user_id')  # Retrieve user_id from session

    if not user_id:
        return redirect('reservation-login')  # Redirect to login if no user_id

    try:
        # Fetch the ReservationUser instance
        user = ReservationUser.objects.get(id=user_id)
        
        # Fetch only unread notifications for the badge count
        reservation_items = ReservationItem.objects.filter(
            reservation__user_id=user_id, is_handled=True
        ).order_by('-handled_by', '-id')
        
        if request.method == 'POST':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            errors = {}

            # Check if old password matches the stored password
            if not user.check_password(old_password):
                errors['old_password_error'] = 'Old password is incorrect.'
                messages.error(request, 'Old password is incorrect.')

            # Check if new password and confirm password match
            if new_password != confirm_password:
                errors['password_mismatch'] = 'New password and confirm password do not match.'
                messages.error(request, 'New password and confirm password do not match.')

            # If no errors, update password
            if not errors:
                # Hash the new password before saving it
                user.password = make_password(new_password)
                user.save()

                # Keep the user logged in after password change
                update_session_auth_hash(request, user)

                messages.success(request, 'Your password was successfully updated!')
                return redirect('reservation-change-password')  # Redirect to the same page after success

            # If there are errors, render the form with errors
            return render(request, 'reservation-changepassword.html', {'errors': errors})

        # Handle GET request (render the form)
        context = {
            'user': user,
            'profile_picture': user.profile_image.url if user.profile_image else None,
            'default_image_url': '/media/profile_pics/users.jpg',  # URL to default image
            'reservation_items': reservation_items
        }
        # On GET request, render the form
        return render(request, 'reservation-changepassword.html', context)

    except ReservationUser.DoesNotExist:
        return redirect('reservation-login')  # Redirect to login if user does not exist
    
    
    
    
# Instantiate the token generator
# token_generator = PasswordResetTokenGenerator()

def reservation_forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = ReservationUser.objects.get(email=email)
            
            # Generate token and encode user ID
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = reservation_token_generator.make_token(user)
            
            # Construct password reset URL
            reset_url = f"{request.scheme}://{request.get_host()}/reservation-reset-password/{uid}/{token}/"
            
            # Prepare email content
            subject = 'Reset Your Password'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [user.email]
            context = {
                'user': user,
                'reset_url': reset_url
            }
            html_content = render_to_string('reservation-reset_email_template.html', context)
            
            # Send email
            email_message = EmailMultiAlternatives(subject, '', from_email, to_email)
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()
            
            messages.success(request, 'A password reset link has been sent to your email.')
        except ReservationUser.DoesNotExist:
            messages.error(request, 'No account found with the provided email.')
    
    return render(request, 'reservation-reset-password.html')

def reset_password(request, uidb64, token):
    try:
        # Decode the user ID
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = ReservationUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, ReservationUser.DoesNotExist):
        user = None
    
    if user is not None and reservation_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password and new_password == confirm_password:
                user.password = make_password(new_password)
                user.save()
                messages.success(request, 'Your password has been reset successfully. You can now log in.')
                return redirect('reservation-login')  # Replace 'login' with your login URL name
            else:
                messages.error(request, 'Passwords do not match.')
        
        return render(request, 'reservation-password_reset_form.html')
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return redirect('reservation_forgot_password')