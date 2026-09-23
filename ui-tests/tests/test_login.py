import pytest

from pages.login_page import LoginPage

INVALID_CREDENTIALS = "Invalid username or password"
BLOCKED_PREFIX = "Your account has been blocked. Reason:"


@pytest.fixture
def login_page(driver, base_url):
    return LoginPage(driver, base_url)


def test_successful_login_as_client(login_page, accounts):
    account = accounts["client"]

    login_page.open().login_as(account.username, account.password)
    login_page.wait_for_redirect_to("/")

    stored = login_page.stored_user()
    assert stored is not None
    assert stored["userType"] == "CLIENT"
    assert stored["username"] == account.username
    assert login_page.has_link("/profile")
    assert not login_page.has_link("/clinics")
    assert not login_page.has_link("/admin/clients")


def test_successful_login_as_admin(login_page, accounts):
    account = accounts["admin"]

    login_page.open().login_as(account.username, account.password)
    login_page.wait_for_redirect_to("/")

    stored = login_page.stored_user()
    assert stored is not None
    assert stored["userType"] == "ADMIN"
    assert login_page.has_link("/admin/clinics")
    assert login_page.has_link("/admin/clients")
    assert login_page.has_link("/admin/listings")


def test_successful_login_as_clinic(login_page, accounts):
    account = accounts["clinic"]

    login_page.open().login_as(account.username, account.password)
    login_page.wait_for_redirect_to("/")

    stored = login_page.stored_user()
    assert stored is not None
    assert stored["userType"] == "CLINIC"
    assert login_page.has_link("/clinics")
    assert not login_page.has_link("/admin/clients")


def test_login_by_username(login_page, accounts):
    account = accounts["client"]

    login_page.open().login_as(account.username, account.password)
    login_page.wait_for_redirect_to("/")

    stored = login_page.stored_user()
    assert stored["username"] == account.username
    assert stored["email"] == account.email


def test_login_by_email(login_page, accounts):
    account = accounts["client"]

    login_page.open().login_as(account.email, account.password)
    login_page.wait_for_redirect_to("/")

    stored = login_page.stored_user()
    assert stored["username"] == account.username
    assert stored["email"] == account.email


def test_invalid_credentials_wrong_password(login_page, accounts):
    account = accounts["client"]

    login_page.open().login_as(account.username, "definitely-not-the-password")

    assert login_page.error_message() == INVALID_CREDENTIALS
    assert login_page.is_on_login()
    assert login_page.stored_user() is None


def test_invalid_credentials_unknown_user(login_page, accounts):
    account = accounts["client"]

    login_page.open().login_as("no.such.user.exists", account.password)

    assert login_page.error_message() == INVALID_CREDENTIALS
    assert login_page.is_on_login()
    assert login_page.stored_user() is None


def test_blocked_account_shows_reason(login_page, accounts, blocked_reason):
    account = accounts["blocked"]

    login_page.open().login_as(account.username, account.password)

    message = login_page.error_message()
    assert message.startswith(BLOCKED_PREFIX)
    assert blocked_reason in message
    assert login_page.is_on_login()
    assert login_page.stored_user() is None


def test_empty_fields_block_submission(login_page):
    login_page.open().submit()
    login_page.wait_until_settled()

    assert login_page.is_value_missing(LoginPage.USERNAME)
    assert login_page.is_on_login()
    assert not login_page.has_error()
    assert login_page.stored_user() is None


def test_whitespace_only_fields_do_not_authenticate(login_page):
    login_page.open().login_as("   ", "      ")
    login_page.wait_until_settled()

    assert login_page.is_on_login()
    assert login_page.stored_user() is None
