from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=(username or "").strip(), is_deleted=False)
        except User.DoesNotExist:
            User().set_password(password or "")
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
