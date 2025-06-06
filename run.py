import os
import sys
import webbrowser
import time
from utils import get_local_ip
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    os.environ["IS_FROM_RUNPY"] = "1"  # ✅ Add this custom env var

    ip = get_local_ip()
    port = "8000"
    time.sleep(1)
    webbrowser.open(f"http://{ip}:{port}")
    execute_from_command_line(["manage.py", "runserver", f"0.0.0.0:{port}", "--noreload"])
