# Decisions and specification reconciliation

Parts 1 and 2 and the supplied reconstruction package were read and unpacked. Source JSON is retained in specification/schemas. Evidence personal data is not copied into the deliverable.

The latest user instruction authorizes an integrated all-module build and supersedes the earlier per-module confirmation gates. It also authorizes proposed leave defaults. This does not waive the requirement to identify incomplete work.

Stack overrides: CRA JavaScript with React 18.3.1; MUI v5 and compatible MUI X; React Router v6, TanStack Query v5, RHF/Zod, Axios and TipTap; Django 5/Python 3.12/DRF; SQLite/WAL; sessions/CSRF; synchronous email/management commands; private local files; xhtml2pdf/CSV; pytest and Jest/RTL; venv/npm, no Docker/Celery/Redis. CRA was actually invoked; React 19 peer incompatibility was resolved with React 18 pins without force. Dependency locks are delivered.

Proposed implementation choices: Employee profile is separate from the authentication User; shared master and form metadata reduce duplicated CRUD; encrypted text fields use Fernet; CSRF bootstrap returns a masked token to memory with HttpOnly cookies; MUI requires inline styles in CSP. These choices require review against full reconstruction parity.

Leave (OQ-02): administrators configure allocation per leave type/year; entitlement is pro-rated from joining through employment/year end and work capacity, and is adjustable. Pending requests reserve balance; working days exclude weekends/holidays. No automatic carry-over is assumed. Fictional demo allocation is 25 days, not company policy. OQ-03: manager recommendation then administrator final approval, with administrator direct action allowed. OQ-04: paid leave consumes balance and unpaid approval does not. Actual policy must be configured before use.

Other Part 28 defaults retained: single tenant; idle timeout 30 minutes and absolute session limit 12 hours; document expiry notification window 60 days; licences/MOD-99 and payroll integration excluded. Reference defects are not intentional target behaviour. The error envelope is {message, errors}, with non-2xx failures. Dates are ISO on the wire and DD-MM-YYYY for formatted display.

The source captures incomplete standard master lists and underspecified candidate form details; reduced behaviour is identified in RELEASE_STATUS.md rather than claimed to be verified parity. Full feature/rule traceability and exact client/server message reconciliation remain open.
