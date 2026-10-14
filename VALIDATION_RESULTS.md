# Validation results — 14 October 2026

Release decision: development evaluation only. Part 26 is not fully passed.

| Area | Result / evidence |
|---|---|
| Source inspection | Parts 1/2 and supporting module, form, rule, permission, API, test and assumption sources reviewed; JSON retained |
| Backend tests | 86 tests passed: 17 setup, 55 acceptance-ID tests, 14 security integration tests |
| Frontend tests | 3 suites / 5 tests passed |
| Production frontend bundle | npm run build compiled successfully |
| Django checks | manage.py check: no issues; makemigrations --check --dry-run: no changes |
| Python dependencies | pip check: no broken requirements |
| Database migration | All committed migrations applied to the validation database |
| HTTP checks | Session/CSRF login; 49 metadata-advertised resource lists; 11 additional dashboard/settings/report/admin endpoints passed |
| Database integrity | Fresh validation SQLite database PRAGMA integrity_check returned ok |
| Seeds/demo | Source roles, 75 menus, master lists and fictional demo creation executed successfully |
| Security checks | Tests cover CSRF, session expiry, one-use password reset, selected permission/object scope denials, private downloads, encryption and onboarding role escalation |
| Archive | Source-only ZIP checked for archive integrity; excludes environment secrets, database, media, dependencies and compiled assets |
| Browser/manual acceptance | Not executed; browser installation failed in the environment |
| Full specification parity | Not passed; see RELEASE_STATUS.md |
| Complete client/server validation parity | Not passed |
| All-role/all-endpoint authorization matrix | Not exhaustive; further review required |
| Windows/macOS clean installation | Commands supplied; not executed on those operating systems |
| Concurrency/performance/dependency security audit | Not completed |
| Production deployment/restore/SMTP | Not completed |

The HTTP check initially exposed missing timesheet and WFH migrations in the validation database. Applying the pending migrations resolved those errors; the subsequent complete HTTP check passed. A separate earlier disposable database integrity error remains unexplained and is documented in RELEASE_STATUS.md. No database is distributed.

The acceptance tests map to every supplied TEST identifier, but a test per identifier is not proof of every documented subcase or complete product behaviour. Passing builds do not demonstrate visual or accessibility correctness. No production-readiness certification is asserted.
