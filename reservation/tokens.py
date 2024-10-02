# tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator
import hashlib

class ReservationPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Use user's primary key, password, and timestamp to generate a unique hash
        return (
            str(user.pk) + user.password + str(timestamp)
        )

# Instantiate the token generator
reservation_token_generator = ReservationPasswordResetTokenGenerator()
