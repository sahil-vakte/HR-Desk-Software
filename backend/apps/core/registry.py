from dataclasses import dataclass

@dataclass(frozen=True)
class Resource:
    model: str
    menu: int
    scope: str = "admin"
    title: str = ""
    owner: str = "user"
    parent: str = ""

RESOURCES = {
    "employees": Resource("employees.Employee",29,"admin","Employees"),
    "holiday-years": Resource("holidays.HolidayYear",84,title="Holiday years"),
    "holidays": Resource("holidays.Holiday",16,"read_all","Holidays"),
    "leave-years": Resource("leave.LeaveYear",57,title="Leave years"),
    "leave-types": Resource("leave.LeaveType",57,title="Leave types"),
    "leave/entitlements": Resource("leave.LeaveEntitlement",31,title="Leave entitlements"),
    "leave/requests": Resource("leave.LeaveRequest",55,"leave","Leave requests"),
    "leave/rota": Resource("leave.LeaveRota",31,title="Leave rota"),
    "wfh-requests": Resource("wfh.WfhRequest",52,"self","Work from home"),
    "attendance/records": Resource("attendance.AttendanceSession",28,title="Attendance records"),
    "attendance/punch-settings": Resource("attendance.PunchSetting",28,title="Punch settings"),
    "projects": Resource("projects.Project",65,"projects","Projects"),
    "tasks": Resource("projects.Task",66,"tasks","Tasks"),
    "policies": Resource("documents.Policy",30,"read_all","Policies"),
    "ho-documents": Resource("documents.HoDocument",83,title="HO documents"),
    "hierarchy-documents": Resource("employees.OrgDocument",75,title="Hierarchy documents"),
    "hiring-documents": Resource("employees.OrgDocument",81,title="Hiring documents"),
    "newsletters": Resource("employees.OrgDocument",77,"read_all","Newsletters"),
    "wsr": Resource("pmo.WeeklyStatusReport",78,"self","Weekly status reports"),
    "queries": Resource("pmo.Query",79,"self","Queries","employee"),
    "whos-where": Resource("pmo.WhosWhereEntry",80,"read_all","Who's Where"),
    "timesheets": Resource("timesheets.Timesheet",82,"self","Timesheets"),
    "rms/roles": Resource("recruitment.JobRole",45,title="Recruitment roles"),
    "rms/applicants": Resource("recruitment.Applicant",47,title="Applicants"),
    "rms/pipeline": Resource("recruitment.Applicant",86,"readonly","Pipeline"),
    "masters/technical-questions": Resource("recruitment.TechnicalQuestion",54,title="Technical questions"),
    "masters/interview-questions": Resource("recruitment.InterviewQuestion",53,title="Interview questions"),
    "masters/work-week": Resource("masters.WorkWeek",15,title="Work week"),
}
MASTERS = {
    "skills": (7,"Skills"), "education-levels": (8,"Education"), "document-types": (74,"Document types"),
    "clients": (67,"Clients"), "working-modes": (60,"Working modes"), "employment-statuses": (43,"Employment statuses"),
    "processes": (39,"Processes"), "document-list": (32,"Documents list"), "countries": (26,"Countries"),
    "sub-units": (22,"Sub units"), "job-titles": (20,"Job titles"), "customers": (19,"Customers"),
    "reporting-managers": (17,"Reporting managers"), "designations": (21,"Designations"),
    "languages": (10,"Languages"), "termination-reasons": (13,"Termination reasons"), "nationalities": (12,"Nationalities"),
    "currency-codes": (73,"Currency codes"), "work-authorizations": (72,"Work authorizations"), "locations": (70,"Locations"),
    "technical-statuses": (51,"Technical statuses"), "interview-statuses": (50,"Interview statuses"), "evaluation-statuses": (49,"Evaluation statuses"),
    "letters": (19,"Letters"), "salary-slabs": (59,"Salary slabs"),
}
for slug, (menu, title) in MASTERS.items():
    RESOURCES["masters/"+slug] = Resource("masters.MasterItem",menu,title=title)
PROFILE = {"dependents":"Dependent", "emergency-contacts":"EmergencyContact", "addresses":"Address", "contact-details":"Address",
    "education":"Education", "experience":"Experience", "skills":"Skill", "languages":"Language", "memberships":"Membership",
    "circumstance-changes":"ChangeOfCircumstance", "documents":"EmployeeDocument", "paperwork":"PaperworkDocument", "salary":"Salary"}
