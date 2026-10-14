from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from apps.core.views import HealthView, csrf_token, SpaView
from apps.accounts.views import LoginView, LogoutView, SessionView, ForgotPasswordView, ResetPasswordView, ChangePasswordView
from apps.accounts.admin_api import UsersViewSet, RolesViewSet, MenusViewSet
from apps.core.api import ResourceViewSet
from apps.core.registry import RESOURCES
from apps.core.ui import ResourceMetadata, LookupView, ProfileMetadata
from apps.core.files import UploadView, DownloadView
from apps.core.settings_api import SettingsView
from apps.core.dashboard import Dashboard, LeaveBalance
from apps.employees.extra_views import NextId, CheckEmail, EmployeeExport, EmergencyPDF, JobReporting
from apps.employees.views import EmployeeCreate, OwnProfile, ProfileSection, VerifyDocument, Directory
from apps.attendance.views import Punch, MyAttendance
from apps.timesheets.views import WeekView, LogView
from apps.pmo.views import QueryReplies
from apps.reports.views import Report
from apps.recruitment.views import CandidateSend, PublicCandidate, Evaluation, ParseCV, ApplicantSection

from apps.core.extras import Branding, AuditList, ProjectChildren, WhosWhere, NewsletterSend, AttendanceGrid, LeaveDetailsExport, HolidayYearCopy

from apps.core.nested import NestedResource
from apps.leave.models import LeaveYear
from apps.holidays.models import HolidayYear
LeaveTypes=type('LeaveTypes',(NestedResource,),{'resource_key':'leave-types','parent_model':LeaveYear,'parent_field':'leave_year'})
Holidays=type('Holidays',(NestedResource,),{'resource_key':'holidays','parent_model':HolidayYear,'parent_field':'holiday_year'})
router=DefaultRouter()
router.register('admin/users',UsersViewSet,basename='users')
router.register('admin/roles',RolesViewSet,basename='roles')
router.register('admin/menu-items',MenusViewSet,basename='menus')
for key in RESOURCES:
    view=type(key.replace('/','_').replace('-','_')+'ViewSet',(ResourceViewSet,),{'resource_key':key})
    router.register(key,view,basename=key.replace('/','-'))
urlpatterns=[
    path('api/v1/employees/next-id/',NextId.as_view()),
    path('api/v1/employees/check-email/',CheckEmail.as_view()),
    path('api/v1/employees/export.csv',EmployeeExport.as_view()),
    path('api/v1/employees/<int:employee_id>/emergency-contact.pdf',EmergencyPDF.as_view()),
    path('api/v1/employees/<int:employee_id>/job/',JobReporting.as_view(),{'section':'job'}),
    path('api/v1/employees/<int:employee_id>/supervisors/',JobReporting.as_view(),{'section':'supervisors'}),
    path('api/v1/employees/<int:employee_id>/subordinates/',JobReporting.as_view(),{'section':'subordinates'}),
    path('api/v1/leave/details/export.<str:extension>',LeaveDetailsExport.as_view()),
    path('api/v1/leave-years/<int:pk>/copy/',HolidayYearCopy.as_view()),
    path('api/v1/leave-years/<int:parent_id>/leave-types/',LeaveTypes.as_view({'get':'list','post':'create'})),
    path('api/v1/leave-years/<int:parent_id>/leave-types/<int:pk>/',LeaveTypes.as_view({'get':'retrieve','patch':'partial_update','delete':'destroy'})),
    path('api/v1/holiday-years/<int:parent_id>/holidays/',Holidays.as_view({'get':'list','post':'create'})),
    path('api/v1/holiday-years/<int:parent_id>/holidays/<int:pk>/',Holidays.as_view({'get':'retrieve','patch':'partial_update','delete':'destroy'})),
    path('api/v1/rms/applicants/<int:pk>/parse-cv/',ParseCV.as_view()),
    path('api/v1/rms/applicants/<int:pk>/documents/',ApplicantSection.as_view(),{'section':'documents'}),
    path('api/v1/rms/applicants/<int:pk>/interviews/<int:panel>/',ApplicantSection.as_view(),{'section':'interviews'}),
    path('api/v1/rms/applicants/<int:pk>/technical-test/send/',CandidateSend.as_view(),{'kind':'test'}),
    path('api/v1/rms/applicants/<int:pk>/cif/request/',CandidateSend.as_view(),{'kind':'cif'}),
    path('api/v1/branding/',Branding.as_view()),
    path('api/v1/audit-events/',AuditList.as_view()),
    path('api/v1/projects/<int:pk>/documents/',ProjectChildren.as_view(),{'kind':'documents'}),
    path('api/v1/tasks/<int:pk>/comments/',ProjectChildren.as_view(),{'kind':'comments'}),
    path('api/v1/whos-where/',WhosWhere.as_view()),
    path('api/v1/newsletters/<int:pk>/send/',NewsletterSend.as_view()),
    path('api/v1/attendance/grid/',AttendanceGrid.as_view()),
    path('api/v1/health/',HealthView.as_view()),path('api/v1/auth/csrf/',csrf_token),
    path('api/v1/auth/login/',LoginView.as_view()),path('api/v1/auth/logout/',LogoutView.as_view()),
    path('api/v1/session/',SessionView.as_view()),path('api/v1/auth/password/forgot/',ForgotPasswordView.as_view()),
    path('api/v1/auth/password/reset/',ResetPasswordView.as_view()),path('api/v1/auth/password/change/',ChangePasswordView.as_view()),
    path('api/v1/ui/profile-fields/<str:section>/',ProfileMetadata.as_view()),
    path('api/v1/ui/resources/',ResourceMetadata.as_view()),path('api/v1/lookups/<str:kind>/',LookupView.as_view()),
    path('api/v1/files/',UploadView.as_view()),path('api/v1/files/<int:pk>/download/',DownloadView.as_view()),
    path('api/v1/settings/<str:section>/',SettingsView.as_view()),
    path('api/v1/dashboard/<str:variant>/',Dashboard.as_view()),path('api/v1/leave/balance/',LeaveBalance.as_view()),
    path('api/v1/employees/onboard/',EmployeeCreate.as_view()),path('api/v1/me/profile/',OwnProfile.as_view()),
    path('api/v1/employees/<int:employee_id>/documents/<int:pk>/verify/',VerifyDocument.as_view()),
    path('api/v1/employees/<int:employee_id>/<str:section>/',ProfileSection.as_view()),
    path('api/v1/employees/<int:employee_id>/<str:section>/<int:pk>/',ProfileSection.as_view()),
    path('api/v1/directory/',Directory.as_view()),
    path('api/v1/attendance/punch-in/',Punch.as_view(),{'operation':'punch-in'}),
    path('api/v1/attendance/punch-out/',Punch.as_view(),{'operation':'punch-out'}),
    path('api/v1/attendance/me/',MyAttendance.as_view()),
    path('api/v1/attendance/me/history/',MyAttendance.as_view()),
    path('api/v1/timesheets/<int:pk>/log/',LogView.as_view()),
    re_path(r'^api/v1/timesheets/(?P<user_id>[0-9]+)/(?P<week_start>[0-9]{4}-[0-9]{2}-[0-9]{2})/$',WeekView.as_view()),
    path('api/v1/queries/<int:pk>/replies/',QueryReplies.as_view()),
    path('api/v1/reports/<str:kind>/',Report.as_view()),
    path('api/v1/rms/applicants/<int:pk>/cv-evaluation/',Evaluation.as_view()),
    path('api/v1/rms/applicants/<int:pk>/invite/<str:kind>/',CandidateSend.as_view()),
    path('api/v1/candidate/<str:token>/',PublicCandidate.as_view()),
    path('api/v1/',include(router.urls)),
    re_path(r'^(?!api/|media/|private_media/|static/)(?P<path>.*)$',SpaView.as_view()),
]
handler400='apps.core.errors.bad_request'
handler403='apps.core.errors.permission_denied'
handler404='apps.core.errors.not_found'
handler500='apps.core.errors.server_error'
