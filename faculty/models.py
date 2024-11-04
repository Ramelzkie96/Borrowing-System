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
    property_id = models.CharField(max_length=10, blank=True, editable=False)  # Make property_id optional
    description = models.TextField(null=True, blank=True)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Link each item to the custom user model
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        # If the item is new (no primary key yet) and the property_id is not already set
        if not self.pk and not self.property_id:
            self.property_id = str(random.randint(1, 99999)).zfill(5)  # Generate a random number, pad with zeros if needed

        super().save(*args, **kwargs)  # Call the original save() method to save the object

    def __str__(self):
        return f"{self.name} ({self.quantity})"

    class Meta:
        verbose_name_plural = "Faculty Items"

        
        
class BorrowRequest(models.Model):
    YEAR_CHOICES = [
        ('1st Year', '1st Year'),
        ('2nd Year', '2nd Year'),
        ('3rd Year', '3rd Year'),
        ('4th Year', '4th Year'),
    ]

    student_id = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    year = models.CharField(max_length=10, choices=YEAR_CHOICES)
    email = models.EmailField()
    phone = models.CharField(max_length=20, null=True)
    date_borrow = models.CharField(max_length=50, null=True, blank=True)
    date_return = models.CharField(max_length=50, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    purpose = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)
    note = models.CharField(max_length=200, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    borrower_type = models.CharField(max_length=100, null=True)
    upload_image = models.ImageField(upload_to='borrow_upload/', null=True, blank=True)
    
    # New field to store the timestamp 
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


class BorrowRequestItem(models.Model):
    borrow_request = models.ForeignKey(BorrowRequest, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(facultyItem, on_delete=models.CASCADE)
    quantityy = models.PositiveIntegerField()
    date_return = models.DateField(null=True, blank=True)
    is_returned = models.BooleanField(default=False)  # New field to track return status
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='handled_items', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.item.name} ({self.quantityy})"

 


class EmailNotification(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    