import os
import sys
import webbrowser
from utils import get_local_ip
import time
from django.core.management import execute_from_command_line



if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

    ip = get_local_ip()
    port = "8000"

    # Open browser using the actual IP (useful when accessing from other devices)
    webbrowser.open(f"http://{ip}:{port}")

    # Start server on 0.0.0.0 so it's accessible to other devices
    execute_from_command_line(["manage.py", "runserver", f"0.0.0.0:{port}", "--noreload"])
