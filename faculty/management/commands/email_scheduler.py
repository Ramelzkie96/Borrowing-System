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
            today = datetime.now().strftime('%d %B, %Y')  # Example: "30 December, 2024"

            # Filter BorrowRequests where date_return is today or in the past
            borrowers = BorrowRequest.objects.filter(date_return__lte=today)

            for borrower in borrowers:
                # Get all related items for the borrower
                items = BorrowRequestItemFaculty.objects.filter(borrow_request=borrower)

                # Count items not marked as `is_returned`
                items_not_returned = items.filter(is_returned=False)
                items_not_returned_count = items_not_returned.count()

                # If all items are returned, skip this borrower
                if items_not_returned_count == 0:
                    print(f"All items for {borrower.name} are marked as returned. No email sent.")
                    continue

                # Compose the email
                subject = "Borrowing Reminder: Item Return Overdue"
                message = (
                    f"Dear {borrower.name},\n\n"
                    f"This is a reminder that {items_not_returned_count} of your borrowed item(s) were due to be returned "
                    f"on {borrower.date_return}. Please return them as soon as possible to avoid penalties.\n\n"
                    "Thank you!\n\n- Borrowing System"
                )
                recipient_email = borrower.email

                # Send the email
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
                    notification_message = f"Email sent to {borrower.email} on {today} at 7:00 pm, with {items_not_returned_count} item(s) overdue."
                    print(notification_message)

                    EmailReminderLog.objects.create(
                        borrower_name=borrower.name,
                        borrower_email=borrower.email,
                        student_id=borrower.student_id,
                        user=borrower.user,
                        notification_message=notification_message
                    )

                except Exception as e:
                    print(f"Failed to send email to {borrower.email}: {e}")
                    
        # run in every 10 seconds
        schedule.every(10).seconds.do(send_email_reminders)


        # Schedule the task
        # schedule.every(1).minutes.do(send_email_reminders)
        
        # Schedule the task
        # schedule.every().day.at("19:00").do(send_email_reminders)

        print("Email scheduler is running...")

        while True:
            schedule.run_pending()
            time.sleep(1)
