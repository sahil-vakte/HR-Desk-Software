from rest_framework.permissions import BasePermission


class DenyUnconfiguredEndpoint(BasePermission):
    """Fail closed until a view explicitly implements menu AND object scope checks."""
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return False
