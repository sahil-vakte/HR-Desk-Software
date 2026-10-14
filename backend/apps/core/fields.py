from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models

class EncryptedTextField(models.TextField):
    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        return Fernet(settings.FIELD_ENCRYPTION_KEY.encode()).decrypt(value.encode()).decode()

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        return Fernet(settings.FIELD_ENCRYPTION_KEY.encode()).encrypt(value.encode()).decode()
