from rest_framework.exceptions import PermissionDenied
from apps.accounts.models import RolePermission


def has_menu(user, menu_id):
    return bool(user.is_authenticated and user.is_active and not user.is_deleted and user.role_id
                and user.role.status and not user.role.is_deleted and
                RolePermission.objects.filter(role_id=user.role_id, menu_item_id=menu_id,
                    menu_item__status=True, menu_item__master_status=True, menu_item__is_deleted=False).exists())


def require_menu(user, *menu_ids):
    if not any(has_menu(user, code) for code in menu_ids):
        raise PermissionDenied()


def is_hr(user):
    return user.role_id in (1, 2)


def require_hr(user):
    if not is_hr(user):
        raise PermissionDenied()


def require_super(user):
    if user.role_id != 1:
        raise PermissionDenied()


def reporting_manager(user):
    from apps.employees.models import Employee
    from apps.masters.models import MasterItem
    return Employee.objects.filter(reports_to=user).exists() or MasterItem.objects.filter(kind='reporting-managers',status=True,extra__user_id=user.pk).exists()


def allowed_user_ids(user, team=False):
    from apps.employees.models import Employee
    if is_hr(user):
        return None
    ids = [user.pk]
    if team:
        ids.extend(Employee.objects.filter(reports_to=user).values_list("user_id", flat=True))
    return ids
