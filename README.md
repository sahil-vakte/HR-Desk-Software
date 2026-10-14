# HRDESK — integrated development build

This source delivery implements workflows across all 16 module areas. It is **not a completed, production-approved replacement**. Read RELEASE_STATUS.md before evaluating or deploying it. No real employee information or configured secrets are included. The previous setup-only instructions are superseded.

## Requirements

Python 3.12; Node.js 24 and npm 11; local disk for SQLite; internet access for dependency installation. No Docker, Redis or Celery. Unzip, then open a terminal inside hrdesk.

## Windows — PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe scripts\init_env.py
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py seed
..\.venv\Scripts\python.exe manage.py create_demo_data
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py runserver 8000
```

In a second terminal opened inside hrdesk:

```powershell
cd frontend
npm ci
npm start
```

After completing the Windows setup once, start both servers by double-clicking
`start-hrdesk.bat` in the project folder, or run it from PowerShell:

```powershell
.\start-hrdesk.bat
```

The launcher opens separate backend and frontend terminal windows. Open
http://localhost:3000 once the frontend is ready. To stop both servers, press
Ctrl+C in each server window or close both windows. Stop an existing session
before launching another one. The launcher checks for the local environment
and dependencies; it does not install dependencies or create demo accounts.

## macOS / Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python scripts/init_env.py
cd backend
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py seed
../.venv/bin/python manage.py create_demo_data
../.venv/bin/python manage.py check
../.venv/bin/python manage.py runserver 8000
```

In a second terminal opened inside hrdesk:

```bash
cd frontend
npm ci
npm start
```

Visit http://localhost:3000. Use localhost consistently. The demo command prompts for a password satisfying the application's password rules; there is no bundled password. Demo accounts: admin@example.invalid (administrator), alex@example.invalid (manager), casey@example.invalid (employee reporting to Alex). Re-running the demo command preserves existing passwords and records. Development emails print in the backend terminal. Do not send actual email to demonstration addresses.

For a clean non-demo installation, omit create_demo_data and run `python manage.py create_superadmin` with the venv's Python executable. Seed is idempotent and installs the source roles, 75 permissions and captured master lists. Configure reference lists, leave years/types, employees and actual entitlements before operational use. `seed --check` validates the source data without seeding.

## Testing administrator setup page

The unlisted route `/testing/create-superadmin` creates an administrator from the
browser without signing in first. Run `manage.py seed` before using it. It asks
for a first name, last name, email, password and password confirmation, then
provides a link to sign in. Existing accounts cannot be overwritten.

It is temporarily enabled by default in all environments, including
`DJANGO_ENV=production`, for test-server pipeline deployments. Matching public
testing tokens are included in the backend settings and frontend source, so
Docker builds work without copying local `.env` files. To override the token,
set `BOOTSTRAP_ADMIN_TOKEN` on the backend and the same value as
`REACT_APP_BOOTSTRAP_ADMIN_TOKEN` at frontend build time. Restart the backend and
rebuild the frontend when changing these values. The frontend variable is read by
`frontend/src/features/auth/BootstrapAdminPage.js`. For local testing open
http://localhost:3000/testing/create-superadmin; with a testing tunnel, append
`/testing/create-superadmin` to its public URL.

This token is public in the browser bundle. An unlisted route is not access
control: anyone who extracts the token can create administrators while the
endpoint is enabled. Use fictional testing data, and disable the backend flag
when setup is complete by setting `BOOTSTRAP_ADMIN_ENABLED=False` in the server
environment and restarting the backend. This blocks creation in every
environment. The CLI command `manage.py create_superadmin` remains available.

## Verification

From backend, using the venv Python executable shown above:

```bash
python -m pytest
python manage.py check
python manage.py makemigrations --check --dry-run
```

From frontend:

```bash
npm test -- --watchAll=false --runInBand
npm run build
```

The delivered tests include a test for every supplied TEST-001 through TEST-055 acceptance identifier, plus infrastructure and security tests. Passing these tests does not establish exhaustive requirement coverage or browser acceptance. Tests use a separate database.

## Structure

- backend/config: environment settings, URL routing and server entry points.
- backend/apps: accounts, core, masters, employees, attendance, leave, wfh, holidays, documents, projects, pmo, timesheets, reports, recruitment.
- backend/tests: setup, acceptance and security integration tests.
- frontend/src/app: router, session context, branding and application layout.
- frontend/src/components: shared forms, rich text and navigation.
- frontend/src/features: resource screens and dedicated workflows.
- specification/schemas: supplied machine-readable requirements and reference data.
- scripts/init_env.py: generates independent local secrets without overwriting configured values.
- FILE_TREE.txt / FULL_FILE_CONTENTS.md / SHA256SUMS.txt: complete source inventory, readable source bundle and checksums.

## Security and configuration

Backend `.env.example` documents settings; init_env generates backend/frontend .env files. Keep DJANGO_SECRET_KEY and FIELD_ENCRYPTION_KEY secret and backed up separately. Losing the encryption key loses access to encrypted fields. Never expose these values through REACT_APP variables. The ZIP excludes .env, databases, uploads, dependencies and generated build files.

REST is under /api/v1/. Session authentication uses HttpOnly cookies and CSRF; Axios keeps only the masked CSRF value in memory. Menu checks and record scopes apply on API endpoints. SQLite uses WAL, foreign keys and immediate write transactions. Business changes are audited; deletion is normally soft. The audit model is append-only through application APIs, not tamper-proof against a database administrator. Files are private and retrieved through authenticated download endpoints, never direct media URLs.

## Release configuration after outstanding work is completed

Do not use Django runserver for live service. Build the frontend, run collectstatic and use a WSGI server behind an HTTPS reverse proxy. The included WhiteNoise/SPA configuration serves the compiled frontend alongside the API. For example, from backend with the venv activated:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
waitress-serve --listen=127.0.0.1:8000 config.wsgi:application
```

Set DJANGO_ENV=production, explicit DJANGO_ALLOWED_HOSTS, HTTPS DJANGO_CSRF_TRUSTED_ORIGINS and FRONTEND_ORIGIN; configure Django's SMTP backend and real sender credentials. Secure cookies and HTTPS redirects are enabled in production. Enable TRUST_HTTPS_PROXY only with a trusted proxy that strips client-supplied forwarding headers. Keep MEDIA_ROOT and backups outside the public web root. Production environment values must be established before running the commands. The development console mail backend must be replaced. No hosting or email account has been provisioned.

## Scheduled operations and backups

Run these commands through cron or Windows Task Scheduler with the backend working directory and venv executable. Schedule expiry alerts daily, email retries periodically, and entitlement allocation after creating employees or leave types:

```bash
python manage.py document_expiry_alerts
python manage.py retry_emails
python manage.py allocate_leave
python manage.py backup_database /private-backups/hrdesk-2026-10-14.sqlite3
```

On Windows use a private absolute path such as `C:\HRDESKBackups\hrdesk-2026-10-14.sqlite3`. Choose a new filename each time. The backup command uses SQLite's online backup API and verifies integrity. Back up private media and encryption keys as well; database-only backups are insufficient. Test restoration in a separate environment. Keep SQLite on local storage, not a network share. DATABASE_URL supports changing the backend; PostgreSQL also requires installing its driver and running migration/compatibility tests.

## Manual evaluation

1. Sign in as each fictional account; inspect menu differences and denied direct API access.
2. Create an employee; check their profile sections, private upload/download and manager assignment.
3. Submit leave as Casey, review as Alex, finalize as administrator, and compare balance. Test overlap and insufficient balance.
4. Submit WFH, punch attendance, create a project task, enter a weekly timesheet and review its status.
5. Create a WSR and PMO query/reply; inspect Who's Where and reports.
6. Upload an applicant CV, complete evaluation, generate candidate-test/CIF links using console email and submit a response once.
7. Check policy documents, master lists, branding, users/roles and audit history.
8. Validate narrow-screen layouts, keyboard navigation, date formats and all acceptance scenarios against the source specification.

See RELEASE_STATUS.md for missing functionality and VALIDATION_RESULTS.md for executed checks. Do not enter real personnel information until the release gaps and security review are closed.
