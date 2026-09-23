import pytest

from pages.login_page import LoginPage
from pages.top_nav import TopNav

GUEST_LINKS = [
    {"text": "Log in", "href": "/login"},
    {"text": "Sign up", "href": "/signup"},
]


@pytest.fixture
def top_nav(driver, base_url):
    return TopNav(driver, base_url)


@pytest.fixture
def sign_in(driver, base_url, accounts):
    def run(name):
        account = accounts[name]
        page = LoginPage(driver, base_url)
        page.open().login_as(account.username, account.password)
        page.wait_for_redirect_to("/")

    return run


def test_guest_sees_login_and_signup_links(top_nav):
    top_nav.open()

    assert top_nav.links() == GUEST_LINKS
    assert not top_nav.has_logout()
    assert top_nav.stored_user() is None


def test_client_sees_profile_and_logout(top_nav, sign_in):
    sign_in("client")
    top_nav.wait_for_link_texts(["Uma's Profile"])

    assert top_nav.link_targets() == ["/profile"]
    assert top_nav.has_logout()


def test_clinic_sees_dashboard_link(top_nav, sign_in):
    sign_in("clinic")
    top_nav.wait_for_link_texts(["Clinic Dashboard", "City's Profile"])

    assert top_nav.link_targets() == ["/clinics", "/profile"]
    assert top_nav.has_logout()


def test_admin_sees_three_admin_links(top_nav, sign_in):
    sign_in("admin")
    top_nav.wait_for_link_texts(["Clinics", "Clients", "Listings", "Ada's Profile"])

    assert top_nav.link_targets() == [
        "/admin/clinics",
        "/admin/clients",
        "/admin/listings",
        "/profile",
    ]
    assert top_nav.has_logout()


def test_logout_clears_session_and_redirects_home(top_nav, sign_in):
    sign_in("client")
    top_nav.open("/login").wait_for_link_texts(["Uma's Profile"])
    top_nav.logout().wait_for_path("/")
    top_nav.wait_for_link_texts(["Log in", "Sign up"])

    assert top_nav.stored_user() is None
    assert not top_nav.has_logout()


def test_logout_survives_refresh(top_nav, sign_in):
    sign_in("client")
    top_nav.logout().wait_for_link_texts(["Log in", "Sign up"])
    top_nav.refresh()

    assert top_nav.links() == GUEST_LINKS
    assert top_nav.stored_user() is None
    assert not top_nav.has_logout()


def test_brand_link_returns_to_listings(top_nav):
    top_nav.open("/signup")

    assert top_nav.brand_text() == "Petify"

    top_nav.click_brand().wait_for_path("/")


def test_mobile_toggle_opens_and_closes_menu(top_nav):
    top_nav.use_mobile_window().open()

    assert top_nav.is_toggler_visible()
    assert not top_nav.is_menu_visible()
    assert not top_nav.is_menu_expanded()

    top_nav.toggle_menu().wait_for_menu_visible(True)

    assert top_nav.is_menu_expanded()

    top_nav.toggle_menu().wait_for_menu_visible(False)

    assert not top_nav.is_menu_expanded()


def test_mobile_menu_collapses_on_route_change(top_nav):
    top_nav.use_mobile_window().open()
    top_nav.toggle_menu().wait_for_menu_visible(True)
    top_nav.click_link("Log in").wait_for_path("/login")
    top_nav.wait_for_menu_visible(False)

    assert not top_nav.is_menu_expanded()
