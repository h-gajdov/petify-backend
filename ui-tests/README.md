# Petify UI tests

Selenium + pytest coverage of `ui-testing-plan.md`. Currently implemented: section 2.2
Login — successful login per role, login by username vs email, invalid credentials,
blocked account, and empty/whitespace fields (10 scenarios).

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Selenium Manager resolves the browser driver automatically; Chrome or Firefox must be
installed.

## Services these tests need

| Service  | Port | Start with |
|:---------|:-----|:-----------|
| Postgres | 5432 | `docker compose up -d` in `petify-backend` |
| Backend  | 8081 | `./mvnw spring-boot:run` in `petify-backend` |
| Frontend | 5173 | `npm run dev` in `petify-frontend` |

The frontend proxies `/api` to `http://localhost:8081`, so the backend must be up or
every login attempt fails with a network error rather than the assertion under test.

## Accounts

Defaults match the seed data in `V2__Insert_initial_data.sql`:

Migration `V13__Seed_ui_test_accounts.sql` in `petify-backend` seeds these dedicated
accounts, so no password guessing is needed — Flyway applies it on backend startup.

| Role    | Username      | Email                    | Password       |
|:--------|:--------------|:-------------------------|:---------------|
| CLIENT  | `ui.client`   | `ui.client@petify.test`  | `TestPass123!` |
| ADMIN   | `ui.admin`    | `ui.admin@petify.test`   | `TestPass123!` |
| CLINIC  | `ui.clinic`   | `ui.clinic@petify.test`  | `TestPass123!` |
| BLOCKED | `ui.blocked`  | `ui.blocked@petify.test` | `TestPass123!` |

`ui.blocked` is seeded with `is_blocked = TRUE` and reason `Repeated policy violations`,
which is the default asserted by `PETIFY_BLOCKED_REASON`.

The passwords are stored as plain text by the migration. `AuthService.login` treats a
`password_hash` equal to the submitted password as a legacy credential and re-hashes it
with bcrypt on the first successful login, so the plaintext seed works on the normal
login path and is upgraded transparently the first time each account signs in.

## Configuration

| Variable | Default | Purpose |
|:---------|:--------|:--------|
| `PETIFY_BASE_URL` | `http://localhost:5173` | Frontend origin |
| `PETIFY_BROWSER` | `chrome` | `chrome` or `firefox` |
| `PETIFY_HEADLESS` | `1` | `0` to watch the run |
| `PETIFY_DEFAULT_PASSWORD` | `TestPass123!` | Fallback password for every account |
| `PETIFY_<ROLE>_USERNAME` / `_EMAIL` / `_PASSWORD` | seed values | Per-account override, `<ROLE>` in CLIENT, ADMIN, CLINIC, BLOCKED |
| `PETIFY_BLOCKED_REASON` | `Repeated policy violations` | Substring asserted in the blocked-account message |

## Run

All three services (Postgres, backend, frontend) must be up first — a browser that
cannot reach `http://localhost:5173` fails every test in fixture setup with
`ERR_CONNECTION_REFUSED`.

```bash
pytest
pytest tests/test_login.py::test_blocked_account_shows_reason
pytest --headed
```

`--headed` shows the browser while the tests run (equivalent to `PETIFY_HEADLESS=0`).

## Scenario map

| Plan row | Test |
|:---------|:-----|
| Successful login per role | `test_successful_login_as_client`, `..._admin`, `..._clinic` |
| Login by username vs by email | `test_login_by_username`, `test_login_by_email` |
| Invalid credentials | `test_invalid_credentials_wrong_password`, `..._unknown_user` |
| Blocked account → reason shown | `test_blocked_account_shows_reason` |
| Empty / whitespace fields | `test_empty_fields_block_submission`, `test_whitespace_only_fields_do_not_authenticate` |

## Notes on two assertions

`test_empty_fields_block_submission` asserts native constraint validation, not an app
error: both inputs carry `required`, so the browser stops the submit and no alert is
rendered.

`test_whitespace_only_fields_do_not_authenticate` asserts only that the user stays on
`/login` unauthenticated. The username field uses `v-model.trim`, so whitespace reaches
the model as an empty string while the DOM may still hold the spaces — whether the
browser blocks the submit or the backend rejects it depends on when Vue syncs the input.
Both outcomes are correct; the test pins the invariant rather than the mechanism.
