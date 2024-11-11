from django.db import models  # type: ignore
from django.contrib.auth.models import AbstractUser, BaseUserManager  # type: ignore
from django.core.files.storage import default_storage  # type: ignore
from django.core.validators import RegexValidator  # Import for custom username validation
from django.core.exceptions import ValidationError  # Import for handling validation errors

# Custom validator to allow spaces in the username
class SpaceAllowedUsernameValidator(RegexValidator):
    regex = r'^[\w\s.@+-]+$'  # Allows spaces, letters, numbers, and special characters
    message = (
        "Enter a valid username. This value may contain only letters, "
        "numbers, spaces, and @/./+/-/_ characters."
    )
    flags = 0

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)

        # Check for existing user with the same email
        if User.objects.filter(email=email).exists():
            raise ValidationError(f'The email "{email}" is already in use. Please use a different email.')

        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    faculty = models.BooleanField('Faculty', default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    # Custom username field to allow spaces in usernames
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[SpaceAllowedUsernameValidator()],  # Use custom validator
        help_text="Required. 150 characters or fewer. Letters, digits, spaces and @/./+/-/_ only.",
        error_messages={
            'unique': "A user with that username already exists.",
        },
    )

    email = models.EmailField(
        unique=True,
        error_messages={
            'unique': "A user with that email already exists.",
        }
    )

    # Use verbose_name to label is_superuser as 'IT Chairman'
    is_superuser = models.BooleanField('IT Chairman', default=False)

    objects = CustomUserManager()

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_set",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )
    
    # Add related_name to avoid clash with the default User model
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="dapartmentchair_user_set",  # This avoids the conflict
        blank=True,
    )

    # Add related_name to avoid clash with the default User model
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="dapartmentchair_user_set",  # This avoids the conflict
        blank=True,
    )

    def save(self, *args, **kwargs):
        if self.pk:
            old_user = User.objects.get(pk=self.pk)
            old_picture = old_user.profile_picture

            if old_picture and old_picture != self.profile_picture:
                if default_storage.exists(old_picture.path):
                    default_storage.delete(old_picture.path)

        if self.is_superuser:
            self.is_staff = True

        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


