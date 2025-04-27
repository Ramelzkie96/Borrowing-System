import os
import django
import schedule
import time
from datetime import datetime
from django.core.mail import send_mail
from project.settings import EMAIL_HOST_USER
from faculty.models import BorrowRequest, BorrowRequestItemFaculty
from django.core.management.base import BaseCommand
from faculty.models import EmailReminderLog

class Command(BaseCommand):
    help = 'Send email reminders for borrowed items'

    def handle(self, *args, **kwargs):
        # Set up Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
        django.setup()

        def send_email_reminders():
            today = datetime.now().date()
            all_borrowers = BorrowRequest.objects.all()

            for borrower in all_borrowers:
                try:
                    # Convert date_return string to date object (format must match stored format)
                    return_date = datetime.strptime(borrower.date_return, '%d %B, %Y').date()
                except (ValueError, TypeError):
                    print(f"Invalid or missing return date for {borrower.name}")
                    continue

                if return_date <= today:
                    items = BorrowRequestItemFaculty.objects.filter(borrow_request=borrower)
                    items_not_returned = items.filter(is_returned=False)

                    if not items_not_returned.exists():
                        print(f"All items for {borrower.name} are marked as returned. No email sent.")
                        continue

                    subject = "Borrowing Reminder: Item Return Overdue"
                    message = (
                        f"Dear {borrower.name},\n\n"
                        f"This is a reminder that {items_not_returned.count()} of your borrowed item(s) were due to be returned "
                        f"on {borrower.date_return}. Please return them as soon as possible to avoid penalties.\n\n"
                        "Thank you!\n\n- Borrowing System"
                    )
                    recipient_email = borrower.email

                    try:
                        send_mail(
                            subject,
                            message,
                            EMAIL_HOST_USER,
                            [recipient_email],
                            fail_silently=False,
                        )
                        print(f"Reminder email sent to {borrower.email}")

                        # Log the notification
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
                        print(f"Failed to send email to {borrower.email}: {e}")

        # Schedule the task
        schedule.every(20).seconds.do(send_email_reminders)
        print("Email scheduler is running...")

        while True:
            schedule.run_pending()
            time.sleep(1)
