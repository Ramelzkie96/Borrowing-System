from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.core.validators import MinLengthValidator
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta
from django.utils import timezone
from django.conf import settings


class ReservationUser(models.Model):
    YEAR_LEVEL_CHOICES = [
        ('1', '1st Year'),
        ('2', '2nd Year'),
        ('3', '3rd Year'),
        ('4', '4th Year'),
    ]

    name = models.CharField(max_length=50)
    student_id = models.CharField(max_length=9, unique=True)
    year_level = models.CharField(max_length=10, choices=YEAR_LEVEL_CHOICES)
    email = models.EmailField(unique=True)
    course = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15)
    password = models.CharField(max_length=128)  # Hashed password storage
    profile_image = models.ImageField(upload_to='profile_pics/', default='profile_pics/users.jpg')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Hash the password if it's new or has changed
        if self.pk is None or not self.__is_password_hashed():
            self.password = make_password(self.password)

        super().save(*args, **kwargs)

    def check_password(self, password):
        return check_password(password, self.password)

    def __is_password_hashed(self):
        # Check if the password is already hashed
        return self.password and self.password.startswith('pbkdf2_sha256$')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)



class StudentReservation(models.Model):
    student_id = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=50)
    year_level = models.CharField(max_length=50)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    reserve_date = models.CharField(max_length=50)  # Changed to DateField for better date handling
    purpose = models.TextField(null=True)
    status = models.CharField(max_length=20, default='Pending')
    user = models.ForeignKey('ReservationUser', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    
    def __str__(self):
        return f"Reservation by {self.name} for {self.content_object.name}"
    
    
    def time_ago(self):
        now = timezone.now()
        diff = now - self.created_at
        
        if diff < timedelta(minutes=1):
            return f"{int(diff.total_seconds())} seconds ago"
        elif diff < timedelta(hours=1):
            return f"{int(diff.total_seconds() // 60)} minutes ago"
        elif diff < timedelta(days=1):
            return f"{int(diff.total_seconds() // 3600)} hours ago"
        elif diff < timedelta(days=30):
            return f"{int(diff.total_seconds() // 86400)} days ago"
        elif diff < timedelta(days=365):
            return f"{int(diff.total_seconds() // 2592000)} months ago"
        else:
            return f"{int(diff.total_seconds() // 31536000)} years ago"
    
    
class ReservationItem(models.Model):
    reservation = models.ForeignKey(StudentReservation, on_delete=models.CASCADE, related_name='items')
    user = models.ForeignKey(ReservationUser, on_delete=models.CASCADE)  # Link to ReservationUser
    item_name = models.CharField(max_length=100)
    description = models.TextField()
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=50, null=True)
    notification = models.CharField(max_length=500, null=True)
    handled_by = models.CharField(max_length=50, blank=True, null=True)
    handled_by_profile_picture = models.URLField(max_length=500, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    is_handled = models.BooleanField(default=False)
    user_type = models.CharField(max_length=50, blank=True, null=True) 
    is_update = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    user_facultyItem = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)  # Modified to store the user

    def __str__(self):
        return f"{self.item_name} (Qty: {self.quantity}) for {self.reservation.name}"
    
    
    
    def time_ago(self):
        now = timezone.now()
        diff = now - self.created_at
        
        if diff < timedelta(minutes=1):
            return f"{int(diff.total_seconds())} seconds ago"
        elif diff < timedelta(hours=1):
            return f"{int(diff.total_seconds() // 60)} minutes ago"
        elif diff < timedelta(days=1):
            return f"{int(diff.total_seconds() // 3600)} hours ago"
        elif diff < timedelta(days=30):
            return f"{int(diff.total_seconds() // 86400)} days ago"
        elif diff < timedelta(days=365):
            return f"{int(diff.total_seconds() // 2592000)} months ago"
        else:
            return f"{int(diff.total_seconds() // 31536000)} years ago"

    
    