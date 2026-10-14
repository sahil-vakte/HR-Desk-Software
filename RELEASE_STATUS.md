# Release status

Status: integrated development build; production release blocked. This archive is substantial working source, not a claim that the complete reconstruction specification has been fulfilled.

## Implemented module areas

| Module | Implemented workflows |
|---|---|
| MOD-01 Authentication | Email/session login, logout, reset/change password, lockout, idle/absolute session expiry and CSRF |
| MOD-02 Dashboards | Role-dependent summaries and dashboard data |
| MOD-03 Employees | Account/profile onboarding, profile sections, reporting links, documents and directory |
| MOD-04 Attendance | Punch in/out, history, administrative records and monthly grid |
| MOD-05 Leave | Years/types, configurable pro-rated entitlements, requests, manager/admin decisions and balance |
| MOD-06 WFH | Requests, validation and approval workflow |
| MOD-07 Holidays | Holiday years, lists and management |
| MOD-08 Documents | Policy/HO document records, private files and archive actions |
| MOD-09 Projects/tasks | Membership, tasks, board, comments and project documents |
| MOD-10 PMO | Weekly status records, queries/replies, newsletters and Who's Where |
| MOD-11 Timesheets | Weekly entry, project membership, disabled days, decision actions and logs |
| MOD-12 Reports | Leave, attendance and PMO data; CSV/PDF exports |
| MOD-13 Recruitment | Applicants, CV text extraction, evaluation, question banks, candidate links and responses |
| MOD-14 Masters | Source-driven master records and administrative editing |
| MOD-15 Settings | Company, localisation, branding and email configuration |
| MOD-16 Users/roles | User and role administration, source menu grants and audit viewer |

## Outstanding implementation and release gaps

- Complete screen-by-screen, field-by-field and interaction parity has not been established. Several modules use shared metadata-driven screens instead of all distinct reference screens. Client validation does not yet mirror every server rule/message.
- Recruitment does not implement the full documented external CV parsing integration, bulk CV processing or complete hire-conversion pipeline. Local PDF/DOCX text extraction is available. Candidate information collection uses a proposed reduced form that needs specification reconciliation.
- Reports do not yet reproduce every specified pivot/layout or Excel export. Timesheet administration and some employee deactivation/profile operations need complete UI flows. Manual attendance entry needs full duration consistency verification.
- Master seeds preserve captured lists; complete standard country/nationality datasets have not been installed. Source permissions with zero grants remain zero; no undocumented recruiter rights were invented.
- Email delivery logging/retries exist for workflow notifications, but password-reset, recruitment invitation and newsletter paths are not fully unified with the configurable SMTP profile and delivery log.
- Encryption is applied to selected sensitive fields, not yet demonstrated for every sensitive field named by the security specification. Upload validation checks format/content but does not include deployed malware scanning or quarantine.
- Some profile-file authorization relationships and endpoint scopes need exhaustive negative coverage. Existing tests do not prove every endpoint/role/object combination.
- Full browser end-to-end, accessibility, responsive-layout, concurrency/load, Windows/macOS installation, dependency vulnerability and independent security reviews remain outstanding. Browser download failed in the execution environment; no browser pass is claimed.
- A disposable local database encountered an integrity error during development. It is excluded from the ZIP. A newly migrated database was used for subsequent validation; the original corruption's cause has not been established. Backup/restore and filesystem durability require further investigation before release.
- No deployed HTTPS environment, production SMTP, retention policy, restore drill or production operational acceptance has been completed.

These are development gaps, not requests for the user to implement missing features. The delivered source is suitable for evaluation and continued development; it must not be described as production-ready.

## Company decisions/configuration needed for launch

Domain/hosting; SMTP sender; initial administrators; actual leave allowances/year boundaries/carry-over and part-time rules; working patterns; approvers; retention and backup requirements; and credentials for any external CV parser. None prevented building this development version. No production secrets should be pasted into chat.
