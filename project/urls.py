from django.contrib import admin
from django.urls import path, include
from DapartmentChair.admin import admin_site  # Import your custom admin site
from DapartmentChair.views import custom_login_view



urlpatterns = [
    path('admin/login/', custom_login_view, name='custom_login'),
    path('admin/', admin_site.urls),  # Use your custom admin site instead of default
    path('', include('DapartmentChair.urls')),
    path('', include('faculty.urls')),
    path('', include('reservation.urls'))
]