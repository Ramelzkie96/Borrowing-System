from django.db import models # type: ignore
from django.contrib.auth.models import AbstractUser, BaseUserManager # type: ignore
from django.core.files.storage import default_storage # type: ignore

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
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

    objects = CustomUserManager()
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_user_set",
        blank=True,
        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
        verbose_name="groups",
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_set",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    def save(self, *args, **kwargs):
        if self.pk:
            # Fetch the old instance to compare with the new one
            old_user = User.objects.get(pk=self.pk)
            old_picture = old_user.profile_picture

            # Check if the profile picture is being changed
            if old_picture and old_picture != self.profile_picture:
                # Delete the old profile picture from the filesystem
                if default_storage.exists(old_picture.path):
                    default_storage.delete(old_picture.path)

        # Automatically set is_admin and is_staff for superusers
        if self.is_superuser:
            self.is_staff = True

        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
