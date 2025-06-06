from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta
from django.utils import timezone
import random

class facultyItem(models.Model):
    name = models.CharField(max_length=100)
    total_quantity = models.PositiveIntegerField(null=True)
    quantity = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name_plural = "Faculty Items"

        
class PropertyID(models.Model):
    faculty_item = models.ForeignKey(facultyItem, on_delete=models.CASCADE, related_name="property_ids")
    property_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Generate a random property ID if not set
        if not self.property_id:
            self.property_id = str(random.randint(1, 99999)).zfill(5)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Property ID {self.property_id} for {self.faculty_item.name}"


        
        
class BorrowRequest(models.Model):
    YEAR_CHOICES = [
        ('1st Year', '1st Year'),
        ('2nd Year', '2nd Year'),
        ('3rd Year', '3rd Year'),
        ('4th Year', '4th Year'),
    ]
    COURSE_CHOICES = [
        ('BS INFORMATION TECHNOLOGY', 'BS INFORMATION TECHNOLOGY'),
        ('BS INDUSTRIAL TECHNOLOGY', 'BS INDUSTRIAL TECHNOLOGY'),
        ('BS ELECTRICAL ENGINEERING', 'BS ELECTRICAL ENGINEERING'),
        ('BS MECHANICAL ENGINEERING', 'BS MECHANICAL ENGINEERING'),
    ]

    student_id = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=100, choices=COURSE_CHOICES) 
    year = models.CharField(max_length=10, choices=YEAR_CHOICES)
    email = models.EmailField()
    phone = models.CharField(max_length=20, null=True)
    date_borrow = models.CharField(max_length=50, null=True, blank=True)
    date_return = models.CharField(max_length=50, null=True, blank=True)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True  # Allow null values
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)  # Allow null values
    content_object = GenericForeignKey('content_type', 'object_id')
    purpose = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    note = models.CharField(max_length=200, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    borrower_type = models.CharField(max_length=100, null=True)
    upload_image = models.ImageField(upload_to='borrow_upload/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f'{self.name} - {self.content_object}'

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


class BorrowRequestItemFaculty(models.Model):
    borrow_request = models.ForeignKey(BorrowRequest, related_name='facultyitems', on_delete=models.CASCADE)
    item = models.ForeignKey(facultyItem, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=50, null=True, blank=True)
    date_return = models.DateField(null=True, blank=True)
    quantityy = models.PositiveIntegerField()
    is_returned = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='handled_faculty_items', 
        on_delete=models.CASCADE, 
        null=True, blank=True
    )

    def __str__(self):
        return f"{self.item.name}"
    
class EmailReminderLog(models.Model):
    borrower_name = models.CharField(max_length=100)
    borrower_email = models.EmailField()
    student_id = models.CharField(max_length=20)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Reference to the user
    notification_message = models.TextField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class EmailNotification(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    