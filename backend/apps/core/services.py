import calendar
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError, APIException, PermissionDenied
from apps.core.access import is_hr, require_menu, reporting_manager

class Conflict(APIException):
    status_code = 409
    default_detail = "This conflicts with an existing record."


def employee_for(user):
    from apps.employees.models import Employee
    try:
        return Employee.objects.get(user=user)
    except Employee.DoesNotExist:
        raise ValidationError({"user": ["An employee profile is required."]})


def work_capacity(employee, date):
    from apps.masters.models import WorkWeek
    from apps.holidays.models import Holiday
    week = WorkWeek.objects.filter(process=employee.process).first()
    if week:
        kind = getattr(week, ['mon','tue','wed','thu','fri','sat','sun'][date.weekday()])
        capacity = {'Full Day':Decimal('1'),'Half Day':Decimal('.5'),'Non-Working Day':Decimal('0')}[kind]
    else:
        capacity = Decimal('1') if date.weekday() in employee.working_days else Decimal('0')
    holidays = Holiday.objects.filter(date=date, status=True)
    if employee.process_id:
        holidays = holidays.filter(process_id=employee.process_id)
    for holiday in holidays:
        capacity = max(Decimal('0'), capacity - (Decimal('1') if holiday.type == 'Full Day' else Decimal('.5')))
    return capacity


def leave_usage(user, leave_type, exclude=None):
    from apps.leave.models import LeaveRequest, LeaveEntitlement
    entitlement = LeaveEntitlement.objects.filter(user=user, leave_type=leave_type).first()
    assigned = entitlement.assigned if entitlement else Decimal('0')
    rows = LeaveRequest.objects.filter(user=user, leave_type=leave_type)
    if exclude:
        rows = rows.exclude(pk=exclude)
    used = rows.filter(status='Approve With Pay').aggregate(n=Sum('days'))['n'] or Decimal('0')
    pending = rows.filter(status='Pending').aggregate(n=Sum('days'))['n'] or Decimal('0')
    return {'assigned': assigned, 'used': used, 'pending': pending, 'balance': assigned-used, 'available':assigned-used-pending}


def allocate_entitlements(leave_type, actor=None):
    from apps.employees.models import Employee
    from apps.leave.models import LeaveEntitlement
    year = leave_type.leave_year
    count = 0
    for employee in Employee.objects.filter(status=True, process_id=year.process_id, date_of_joining__lte=year.to_date):
        start = max(year.from_date, employee.date_of_joining)
        end = min(year.to_date, employee.deactivated_on or year.to_date)
        days = max(0,(end-start).days+1)
        assigned = (leave_type.allocation_per_year * Decimal(days) / Decimal((year.to_date-year.from_date).days+1)
                    * Decimal(employee.working_capacity_pct) / Decimal(100)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        if not LeaveEntitlement.objects.filter(user=employee.user,leave_type=leave_type).exists():
            item=LeaveEntitlement(user=employee.user,leave_type=leave_type,assigned=assigned)
            item.save(actor=actor)
            count += 1
    return count


def validate_leave(data, user, instance=None):
    from apps.leave.models import LeaveRequest
    employee = employee_for(user)
    lt = data['leave_type']
    start, end = data['from_date'], data['to_date']
    if not lt.status or not lt.leave_year.status:
        raise ValidationError({'leave_type':['Please select an active leave type.']})
    if lt.process_id != employee.process_id:
        raise ValidationError({'leave_type':['Leave type must belong to the employee process.']})
    if start>end or start<lt.leave_year.from_date or end>lt.leave_year.to_date:
        raise ValidationError({'to_date':['Dates must be ordered and within the leave year.']})
    duration=data.get('duration','Full Day')
    if duration!='Full Day' and start!=end:
        raise ValidationError({'duration':['Half-day leave must cover one date.']})
    rows=LeaveRequest.objects.filter(user=user,from_date__lte=end,to_date__gte=start).exclude(status='Rejected')
    if instance: rows=rows.exclude(pk=instance.pk)
    if rows.exists(): raise Conflict('An active leave request overlaps these dates.')
    days=Decimal('0')
    day=start
    while day<=end:
        days+=min(work_capacity(employee,day),Decimal('1') if duration=='Full Day' else Decimal('.5'))
        day+=timedelta(days=1)
    if days<=0: raise ValidationError({'from_date':['Select at least one working day.']})
    usage=leave_usage(user,lt,instance.pk if instance else None)
    if days>usage['available']:
        balance=format(usage['available'].normalize(),'f')
        raise ValidationError({'non_field_errors':[f'You only left {balance} balance leaves , and you cannot apply more than that balance leave, please contact admin.']})
    data['days']=days
    return data


def decide(instance, action, actor, reason=''):
    from apps.leave.models import LeaveRequest
    from apps.timesheets.models import Timesheet, TimesheetLog
    from apps.wfh.models import WfhRequest
    from apps.pmo.models import WeeklyStatusReport, Query
    with transaction.atomic():
        row=type(instance).objects.select_for_update().get(pk=instance.pk)
        if isinstance(row,LeaveRequest):
            if row.status!='Pending': raise Conflict('This leave request has already been decided.')
            if action=='reject' and not reason.strip(): raise ValidationError({'reason':['Please enter some reason for rejection']})
            if not is_hr(actor):
                require_menu(actor,46)
                if not reporting_manager(actor) or employee_for(row.user).reports_to_id != actor.pk or row.user_id==actor.pk:
                    raise PermissionDenied()
                row.manager_status='Rejected' if action=='reject' else 'Approved'
                row.rejection_reason=reason if action=='reject' else ''
            else:
                require_menu(actor,31)
                if action=='approve':
                    if row.days>leave_usage(row.user,row.leave_type,row.pk)['available']:
                        raise ValidationError({'non_field_errors':['Insufficient leave balance.']})
                    row.status='Approve With Pay'
                elif action=='approve-unpaid':row.status='Approve Without Pay'
                else:row.status='Rejected'
                row.rejection_reason=reason if action=='reject' else ''
        elif isinstance(row,WfhRequest):
            require_menu(actor,52)
            if not is_hr(actor):raise PermissionDenied()
            if row.status!='Pending':raise Conflict('This request has already been decided.')
            if action=='reject' and not reason.strip():raise ValidationError({'reason':['Please enter some reason for rejection']})
            row.status='Rejected' if action=='reject' else 'Approved'
            row.rejection_reason=reason if action=='reject' else ''
        elif isinstance(row,Timesheet):
            require_menu(actor,82)
            if not is_hr(actor):raise PermissionDenied()
            if row.approval_status!='Pending':raise Conflict('This timesheet has already been decided.')
            if action=='reject' and not reason.strip():raise ValidationError({'reason':['Please enter a rejection comment.']})
            row.approval_status='Rejected' if action=='reject' else 'Accepted'
            log=TimesheetLog(timesheet=row,action=row.approval_status,comment=reason,actor=actor)
            log.save(actor=actor)
        elif isinstance(row,WeeklyStatusReport):
            require_menu(actor,78)
            if not is_hr(actor):raise PermissionDenied()
            if row.status!='Submitted':raise Conflict('This report has already been decided.')
            row.status='Rejected' if action=='reject' else 'Approved'
        elif isinstance(row,Query):
            require_menu(actor,79)
            if not is_hr(actor) or action!='close':raise PermissionDenied()
            if row.status=='Closed':raise Conflict('This query is already closed.')
            row.status='Closed'
        else:raise ValidationError({'action':['Unsupported action.']})
        row.save(actor=actor)
        from .mail import request_notification
        transaction.on_commit(lambda: request_notification(row,decision=True))
        return row
