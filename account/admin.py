from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, AdminPasswordChangeForm
from .models import User
from .forms import SignUpForm
from django.utils.html import format_html
from django.conf import settings
from django.contrib.auth.models import Group

# Set custom site header
admin.site.site_header = "IT Chairman Admin"

class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User

class MyUserAdmin(BaseUserAdmin):
    form = MyUserChangeForm
    add_form = SignUpForm
    change_password_form = AdminPasswordChangeForm

    # Disable actions dropdown completely
    actions = []

    # This method disables all actions
    def get_actions(self, request):
        # Return an empty dictionary to disable all actions
        return {}

    def profile_picture_image(self, obj):
        if obj.profile_picture:
            return format_html(
                '<div style="display: flex; justify-content: center;"><img src="{}" style="width: 30px; height: 30px; border-radius: 50%;" /></div>',
                obj.profile_picture.url
            )
        else:
            default_image_url = '{}{}'.format(settings.MEDIA_URL, 'profile_pics/users.jpg')
            return format_html(
                '<div style="display: flex; justify-content: center;"><img src="{}" style="width: 30px; height: 30px; border-radius: 50%;" /></div>',
                default_image_url
            )
    profile_picture_image.short_description = 'Profile Picture'

    list_display = ('username', 'email', 'profile_picture_image', 'faculty', 'is_superuser')
    list_filter = ('faculty', 'is_superuser')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email', 'profile_picture')}),
        ('Permissions', {'fields': (('faculty', 'is_superuser'),)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'profile_picture', 'password1', 'password2'),
        }),
        ('Roles', {
            'classes': ('wide',),
            'fields': ('faculty', 'is_superuser'),  # Keep 'is_superuser' field here
        }),
    )

    search_fields = ('username', 'email')
    ordering = ('username',)

    # Override save_model to show a toast message after saving a user
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            messages.success(request, f'The user "{obj.username}" has been updated successfully!')
        else:
            messages.success(request, f'A new user "{obj.username}" has been created successfully!')

    # Override delete_model to show a toast message after deleting a user
    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        messages.error(request, f'The user "{obj.username}" has been deleted.')

    # Override message_user to suppress default Django messages
    def message_user(self, request, message, level=messages.INFO, extra_tags='', fail_silently=False):
        # Do nothing, suppress the default message
        pass

    # Customize the form field labels
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['is_superuser'].label = 'IT Chairman'  # Change label for 'is_superuser' field
        return form

# Register the custom User model admin
admin.site.register(User, MyUserAdmin)
# Unregister the default Group model admin, if not needed
admin.site.unregister(Group)
