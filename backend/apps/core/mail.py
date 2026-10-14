import logging
from django.conf import settings
from django.core.mail import get_connection, EmailMessage
from .models import EmailDelivery, SmtpProfile
logger=logging.getLogger('hrdesk')

def deliver(row):
    try:
        profile=SmtpProfile.objects.filter(profile=row.profile,status=True).first()
        kwargs={}
        if settings.ENVIRONMENT=='production' and profile:
            kwargs={'backend':'django.core.mail.backends.smtp.EmailBackend','host':profile.host,'port':profile.port,
                    'username':profile.username,'password':profile.password,'use_tls':profile.security=='TLS','use_ssl':profile.security=='SSL','timeout':20}
        connection=get_connection(**kwargs)
        sender=profile.from_address if profile and profile.from_address else settings.DEFAULT_FROM_EMAIL
        EmailMessage(row.subject,row.body,sender,[row.recipient],connection=connection).send(fail_silently=False)
        row.delivery_status='Sent';row.error=''
    except Exception as exc:
        row.delivery_status='Failed';row.error=type(exc).__name__
        logger.error('Email delivery failed id=%s type=%s',row.pk,type(exc).__name__)
    row.attempts+=1;row.save()
    return row

def notify(recipient,subject,body,profile='HR'):
    row=EmailDelivery(recipient=recipient,subject=subject,body=body,profile=profile);row.save()
    return deliver(row)

def request_notification(row,decision=False):
    from apps.accounts.models import User
    from .services import employee_for
    user=getattr(row,'user',None) or getattr(row,'employee',None)
    if not user:return
    if decision:recipients={user.email}
    else:
        recipients=set(User.objects.filter(role_id=1,is_active=True,is_deleted=False).values_list('email',flat=True))
        try:
            employee=employee_for(user)
            if employee.reports_to:recipients.add(employee.reports_to.email)
        except Exception:pass
    for email in recipients:
        notify(email,'HRDESK request update',f'A {row._meta.verbose_name} record ({row.pk}) has been {"decided" if decision else "submitted"}. Sign in to review it.')
