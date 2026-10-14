import re
from django.core.exceptions import ValidationError

PASSWORD_MESSAGE = "Password must be 12+ chars with upper, lower, number & special character."

class StrongPasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 12 or not all(re.search(pattern, password) for pattern in [r"[A-Z]", r"[a-z]", r"[0-9]", r"[^A-Za-z0-9]"]):
            raise ValidationError(PASSWORD_MESSAGE)

    def get_help_text(self):
        return PASSWORD_MESSAGE
