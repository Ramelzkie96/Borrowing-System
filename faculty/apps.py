from django.apps import AppConfig
import threading
import time
import schedule
from datetime import datetime
from django.core.mail import send_mail
from django.conf import settings
import sys
import os  # for detecting main run process


def send_email_reminders():
    from faculty.models import BorrowRequest, BorrowRequestItemFaculty, EmailReminderLog

    today = datetime.now().date()
    all_borrowers = BorrowRequest.objects.all()
    suppressed_logs = 0  # count how many users are skipped

    for borrower in all_borrowers:
        try:
            return_date = datetime.strptime(borrower.date_return, '%d %B, %Y').date()
        except (ValueError, TypeError):
            print(f"[Reminder] Skipped: Invalid or missing return date for {borrower.name}")
            continue

        if return_date <= today:
            items = BorrowRequestItemFaculty.objects.filter(borrow_request=borrower)
            items_not_returned = items.filter(is_returned=False)

            if not items_not_returned.exists():
                suppressed_logs += 1
                continue  # do not print each one

            subject = "Borrowing Reminder: Item Return Overdue"
            message = (
                f"Dear {borrower.name},\n\n"
                f"This is a reminder that {items_not_returned.count()} of your borrowed item(s) were due on "
                f"{borrower.date_return}. Please return them as soon as possible to avoid penalties.\n\n"
                "Thank you!\n\n- Borrowing System"
            )

            try:
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [borrower.email],
                    fail_silently=False,
                )
                print(f"[Reminder] Email sent to {borrower.email}")

                notification_message = (
                    f"Email sent to {borrower.email} on {today.strftime('%d %B, %Y')} "
                    f"at 7:00 pm, with {items_not_returned.count()} item(s) overdue."
                )

                EmailReminderLog.objects.create(
                    borrower_name=borrower.name,
                    borrower_email=borrower.email,
                    student_id=borrower.student_id,
                    user=borrower.user,
                    notification_message=notification_message
                )

            except Exception as e:
                print(f"[Reminder] Failed to send email to {borrower.email}: {e}")

    if suppressed_logs:
        print(f"[Reminder] {suppressed_logs} borrower(s) skipped (all items returned).")


def start_scheduler():
    schedule.every().day.at("19:00").do(send_email_reminders)
    print("Email scheduler is running in background...")

    while True:
        schedule.run_pending()
        time.sleep(1)


scheduler_started = False  # Global flag

class FacultyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'faculty'

    def ready(self):
        global scheduler_started
        is_frozen_app = getattr(sys, 'frozen', False)

        if not scheduler_started and (
            is_frozen_app or any(keyword in sys.argv[0] for keyword in ['run.py', 'run', 'run.exe'])
        ):
            scheduler_started = True
            threading.Thread(target=start_scheduler, daemon=True).start()
            print("Email scheduler is running in background...")
