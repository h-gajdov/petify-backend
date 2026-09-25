import pytest

from pages.signup_page import SignupPage

PASSWORD_MISMATCH = "Passwords do not match"
ACCOUNT_CREATED = "Account created. Redirecting to login…"
SUBMIT_LABEL = "Create account"
LOADING_LABEL = "Creating…"
PROFILE_LINK = "Ui's Profile"


@pytest.fixture
def signup_page(driver, base_url):
    return SignupPage(driver, base_url)


def test_success_with_auto_login(signup_page, new_account):
    account = new_account()

    signup_page.open().register_as(account)
    signup_page.wait_for_redirect_to("/")

    stored = signup_page.stored_user()
    assert stored is not None
    assert stored["username"] == account.username
    assert stored["email"] == account.email
    assert stored["userType"] == "CLIENT"
    assert not signup_page.has_error()


def test_success_without_token_redirects_to_login(signup_page, new_account):
    account = new_account()

    signup_page.open().stub_success_without_user()
    signup_page.record_success_alert()
    signup_page.register_as(account)
    signup_page.wait_for_redirect_to("/login")

    assert signup_page.recorded_success_alert() == ACCOUNT_CREATED
    assert signup_page.stored_user() is None


def test_password_mismatch_blocks_submission(signup_page, new_account):
    account = new_account()

    signup_page.open().count_signup_requests()
    signup_page.register_as(account, confirm=account.password + "-different")
    signup_page.wait_until_settled()

    assert signup_page.error_message() == PASSWORD_MISMATCH
    assert signup_page.is_on_signup()
    assert signup_page.stored_user() is None
    assert signup_page.signup_requests() == 0


def test_password_mismatch_then_fixed_succeeds(signup_page, new_account):
    account = new_account()

    signup_page.open()
    signup_page.register_as(account, confirm=account.password + "-different")
    assert signup_page.error_message() == PASSWORD_MISMATCH

    signup_page.type_into(SignupPage.CONFIRM, account.password).submit()
    signup_page.wait_for_redirect_to("/")

    stored = signup_page.stored_user()
    assert stored is not None
    assert stored["username"] == account.username


def test_duplicate_username_is_rejected(signup_page, new_account, accounts):
    fresh = new_account()

    signup_page.open().register_as(fresh, username=accounts["client"].username)
    signup_page.wait_until_settled()

    assert signup_page.has_error()
    assert signup_page.error_message() != ""
    assert signup_page.is_on_signup()
    assert signup_page.stored_user() is None


def test_duplicate_email_is_rejected(signup_page, new_account, accounts):
    fresh = new_account()

    signup_page.open().register_as(fresh, email=accounts["client"].email)
    signup_page.wait_until_settled()

    assert signup_page.has_error()
    assert signup_page.error_message() != ""
    assert signup_page.is_on_signup()
    assert signup_page.stored_user() is None


def test_empty_form_blocks_submission(signup_page):
    signup_page.open().submit()
    signup_page.wait_until_settled()

    assert signup_page.is_value_missing(SignupPage.USERNAME)
    assert signup_page.is_on_signup()
    assert not signup_page.has_error()
    assert not signup_page.has_success()
    assert signup_page.stored_user() is None


def test_missing_email_blocks_submission(signup_page, new_account):
    account = new_account()

    signup_page.open().register_as(account, email="")
    signup_page.wait_until_settled()

    assert signup_page.is_value_missing(SignupPage.EMAIL)
    assert not signup_page.is_value_missing(SignupPage.USERNAME)
    assert signup_page.is_on_signup()
    assert not signup_page.has_error()
    assert signup_page.stored_user() is None


def test_missing_confirm_password_blocks_submission(signup_page, new_account):
    account = new_account()

    signup_page.open().register_as(account, confirm="")
    signup_page.wait_until_settled()

    assert signup_page.is_value_missing(SignupPage.CONFIRM)
    assert signup_page.is_on_signup()
    assert not signup_page.has_error()
    assert signup_page.stored_user() is None


def test_invalid_email_format_blocks_submission(signup_page, new_account):
    account = new_account()

    signup_page.open().register_as(account, email="not-an-email")
    signup_page.wait_until_settled()

    assert signup_page.is_type_mismatch(SignupPage.EMAIL)
    assert signup_page.is_on_signup()
    assert not signup_page.has_error()
    assert signup_page.stored_user() is None


def test_valid_email_format_is_accepted(signup_page, new_account):
    account = new_account()
    tagged = "%s+tag@mail.petify.test" % account.username

    signup_page.open().fill_from(account, email=tagged)

    assert not signup_page.is_type_mismatch(SignupPage.EMAIL)
    assert signup_page.is_field_valid(SignupPage.EMAIL)

    signup_page.submit()
    signup_page.wait_for_redirect_to("/")

    stored = signup_page.stored_user()
    assert stored is not None
    assert stored["email"] == tagged


def test_show_password_toggles_both_fields(signup_page, new_account):
    account = new_account()

    signup_page.open().fill_from(account)

    assert signup_page.field_type(SignupPage.PASSWORD) == "password"
    assert signup_page.field_type(SignupPage.CONFIRM) == "password"
    assert signup_page.toggle_labels() == ["Show password", "Show password"]

    signup_page.toggle_password(1)

    assert signup_page.field_type(SignupPage.PASSWORD) == "text"
    assert signup_page.field_type(SignupPage.CONFIRM) == "text"
    assert signup_page.toggle_labels() == ["Hide password", "Hide password"]

    signup_page.toggle_password(0)

    assert signup_page.field_type(SignupPage.PASSWORD) == "password"
    assert signup_page.field_type(SignupPage.CONFIRM) == "password"


def test_loading_state_is_shown_while_submitting(signup_page, new_account):
    account = new_account()

    signup_page.open().delay_signup(1500)

    assert signup_page.submit_label() == SUBMIT_LABEL

    signup_page.register_as(account)
    signup_page.wait_for_submit_label(LOADING_LABEL)

    assert signup_page.is_submit_disabled()

    signup_page.wait_for_redirect_to("/")

    assert signup_page.stored_user()["username"] == account.username


def test_double_submit_sends_single_request(signup_page, new_account):
    account = new_account()

    signup_page.open().delay_signup(1500)
    signup_page.register_as(account)
    signup_page.wait_for_submit_label(LOADING_LABEL)
    signup_page.press_enter()
    signup_page.wait_for_redirect_to("/")

    assert signup_page.delayed_requests() == 1
    assert not signup_page.has_error()
    assert signup_page.stored_user()["username"] == account.username


def test_session_is_visible_in_nav_after_signup(signup_page, new_account):
    account = new_account()

    signup_page.open()

    assert signup_page.has_nav_login()

    signup_page.register_as(account)
    signup_page.wait_for_redirect_to("/").wait_for_nav_profile()

    assert signup_page.nav_profile_text() == PROFILE_LINK
    assert signup_page.has_nav_logout()
    assert not signup_page.has_nav_login()


def test_session_survives_refresh(signup_page, new_account):
    account = new_account()

    signup_page.open().register_as(account)
    signup_page.wait_for_redirect_to("/")
    signup_page.refresh().wait_for_nav_profile()

    assert signup_page.stored_user()["username"] == account.username
    assert signup_page.nav_profile_text() == PROFILE_LINK
    assert signup_page.has_nav_logout()
