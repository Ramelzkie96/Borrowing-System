from django.contrib.admin import AdminSite
from django.urls import reverse
from django.shortcuts import redirect

class CustomAdminSite(AdminSite):
    def login(self, request, extra_context=None):
        # Redirect to your custom login page
        return redirect(reverse('custom_login'))

    def index(self, request, extra_context=None):
        # If the user is authenticated, redirect to the admin dashboard
        if request.user.is_authenticated:
            return redirect(reverse('admin-dashboard'))
        # Otherwise, redirect to the login page
        return redirect(reverse('custom_login'))

admin_site = CustomAdminSite()
