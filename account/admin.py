from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, AdminPasswordChangeForm
from .models import User
from .forms import SignUpForm
from django.utils.html import format_html
from django.conf import settings

admin.site.site_header = "IT Chairman Admin"

class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User

class MyUserAdmin(BaseUserAdmin):
    form = MyUserChangeForm
    add_form = SignUpForm
    change_password_form = AdminPasswordChangeForm

    def profile_picture_image(self, obj):
        if obj.profile_picture:
            return format_html('<div style="display: flex; justify-content: center;"><img src="{}" style="width: 30px; height: 30px; border-radius: 50%;" /></div>'.format(obj.profile_picture.url))
        else:
            default_image_url = '{}{}'.format(settings.MEDIA_URL, 'profile_pics/users.jpg')
            return format_html('<div style="display: flex; justify-content: center;"><img src="{}" style="width: 30px; height: 30px; border-radius: 50%;" /></div>'.format(default_image_url))
    profile_picture_image.short_description = 'Profile Picture'

    list_display = ('username', 'email', 'profile_picture_image', 'faculty', 'is_superuser',)
    list_filter = ('faculty', 'is_superuser')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email', 'profile_picture')}),
        ('Permissions', {'fields': (('faculty', 'is_superuser'),)}),
        ('Groups', {'fields': ('groups',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'profile_picture', 'password1', 'password2'),
        }),
        ('Roles', {
            'classes': ('wide',),
            'fields': ('faculty', 'is_superuser'),
        }),
        ('Groups', {
            'classes': ('wide',),
            'fields': ('groups',),
        }),
    )

    search_fields = ('username', 'email')
    ordering = ('username',)

    def change_user_password(self, request, id, form_url=''):
        user = self.get_object(request, id)
        if user is not None:
            if request.method == 'POST':
                form = self.change_password_form(user, request.POST)
                if form.is_valid():
                    form.save()
            else:
                form = self.change_password_form(user)
            return self.render_change_form(request, form, change=True, obj=user, form_url=form_url)

admin.site.register(User, MyUserAdmin)
