import pytest

from pages.admin_clinics_page import (
    AdminClinicsPage,
    APPLICATIONS_URL,
    APPROVE_URL,
    CLINICS_URL,
    CLINIC_REVIEWS_URL,
    DENY_URL,
    route,
    stub_application,
    stub_clinic,
    stub_clinic_review,
)
from pages.login_page import LoginPage

PAGE_TITLE = "Clinics"
PANEL_TITLES = ["Clinic Applications", "Clinic Reviews"]
NO_APPLICATIONS_TEXT = "No clinic applications found."
SELECT_CLINIC_TEXT = "Select a clinic to inspect its reviews."
NO_REVIEWS_TEXT = "No reviews for this clinic."
NOT_FOUND_ERROR = "Application not found"
PENDING_CLINIC = "Pending Paws"
DENIAL_REASON = "Incomplete documents"


@pytest.fixture
def admin_page(driver, base_url):
    return AdminClinicsPage(driver, base_url)


@pytest.fixture
def sign_in(driver, base_url, accounts):
    def run(name):
        account = accounts[name]
        page = LoginPage(driver, base_url)
        page.open().login_as(account.username, account.password)
        page.wait_for_redirect_to("/")

    return run


def test_guest_is_redirected_to_login(admin_page):
    admin_page.open().wait_for_login_redirect()

    assert not admin_page.has_page()


def test_non_admin_user_is_redirected_to_listings(admin_page, sign_in):
    sign_in("client")
    admin_page.open().wait_for_listings_redirect()

    assert not admin_page.has_page()


def test_admin_sees_moderation_page(admin_page, sign_in):
    sign_in("admin")
    admin_page.open().wait_until_loaded()

    assert admin_page.page_title() == PAGE_TITLE
    assert admin_page.panel_titles() == PANEL_TITLES
    assert admin_page.review_panel_placeholder() == SELECT_CLINIC_TEXT
    assert admin_page.errors() == []


def test_applications_are_listed(admin_page, sign_in):
    sign_in("admin")
    admin_page.install_routes(
        [
            route(
                APPLICATIONS_URL,
                [
                    stub_application(90501, PENDING_CLINIC),
                    stub_application(90502, "Approved Paws", status="APPROVED"),
                    stub_application(
                        90503,
                        "Denied Paws",
                        status="DENIED",
                        denialReason=DENIAL_REASON,
                    ),
                ],
                method="GET",
            )
        ]
    )
    admin_page.open_from_nav().wait_for_application_names(
        [PENDING_CLINIC, "Approved Paws", "Denied Paws"]
    )

    assert admin_page.application(PENDING_CLINIC) == {
        "name": PENDING_CLINIC,
        "location": "Skopje - Testna 1",
        "contact": "stub.clinic@petify.test | 070111222",
        "status": "PENDING",
        "submitted": "Submitted Feb 18, 2026",
        "denial": "",
    }
    assert admin_page.application_status("Approved Paws") == "APPROVED"
    assert admin_page.application_denial("Denied Paws") == "Denied: %s" % DENIAL_REASON
    assert admin_page.errors() == []


def test_empty_applications_show_placeholder(admin_page, sign_in):
    sign_in("admin")
    admin_page.install_routes([route(APPLICATIONS_URL, [], method="GET")])
    admin_page.open_from_nav().wait_until_loaded()

    assert admin_page.applications() == []
    assert admin_page.applications_empty_text() == NO_APPLICATIONS_TEXT
    assert admin_page.errors() == []


def test_approve_application_marks_it_approved(admin_page, sign_in):
    application = stub_application(90501, PENDING_CLINIC)
    sign_in("admin")
    admin_page.install_routes(
        [
            route(APPROVE_URL, dict(application, status="APPROVED"), method="PATCH"),
            route(APPLICATIONS_URL, [application], method="GET"),
            route(CLINICS_URL, [stub_clinic(90601, PENDING_CLINIC)], method="GET"),
            route(CLINIC_REVIEWS_URL, [], method="GET"),
        ]
    )
    admin_page.open_from_nav().wait_for_application_names([PENDING_CLINIC])
    admin_page.approve(PENDING_CLINIC)
    admin_page.wait_for_application_status(PENDING_CLINIC, "APPROVED")

    assert not admin_page.approve_enabled(PENDING_CLINIC)
    assert admin_page.deny_enabled(PENDING_CLINIC)
    assert admin_page.clinic_names() == [PENDING_CLINIC]
    assert admin_page.request_count(APPROVE_URL, "PATCH") == 1
    assert admin_page.request_count(CLINICS_URL, "GET") == 2
    assert admin_page.errors() == []


def test_approve_failure_shows_error(admin_page, sign_in):
    sign_in("admin")
    admin_page.install_routes(
        [
            route(APPROVE_URL, {"error": NOT_FOUND_ERROR}, 400, method="PATCH"),
            route(
                APPLICATIONS_URL,
                [stub_application(90501, PENDING_CLINIC)],
                method="GET",
            ),
        ]
    )
    admin_page.open_from_nav().wait_for_application_names([PENDING_CLINIC])
    admin_page.approve(PENDING_CLINIC)
    admin_page.wait_for_error(NOT_FOUND_ERROR)

    assert admin_page.application_status(PENDING_CLINIC) == "PENDING"
    assert admin_page.approve_enabled(PENDING_CLINIC)


def test_already_approved_application_cannot_be_approved_again(admin_page, sign_in):
    sign_in("admin")
    admin_page.install_routes(
        [
            route(
                APPLICATIONS_URL,
                [stub_application(90502, "Approved Paws", status="APPROVED")],
                method="GET",
            )
        ]
    )
    admin_page.open_from_nav().wait_for_application_names(["Approved Paws"])

    assert admin_page.application_status("Approved Paws") == "APPROVED"
    assert not admin_page.approve_enabled("Approved Paws")
    assert admin_page.deny_enabled("Approved Paws")
    assert admin_page.request_count(APPROVE_URL, "PATCH") == 0


def test_deny_application_with_reason(admin_page, sign_in):
    application = stub_application(90501, PENDING_CLINIC)
    sign_in("admin")
    admin_page.install_routes(
        [
            route(
                DENY_URL,
                dict(application, status="DENIED", denialReason=DENIAL_REASON),
                method="PATCH",
            ),
            route(APPLICATIONS_URL, [application], method="GET"),
        ]
    )
    admin_page.open_from_nav().wait_for_application_names([PENDING_CLINIC])
    admin_page.deny(PENDING_CLINIC).accept_dialog(DENIAL_REASON)
    admin_page.wait_for_application_status(PENDING_CLINIC, "DENIED")

    assert admin_page.application_denial(PENDING_CLINIC) == "Denied: %s" % DENIAL_REASON
    assert not admin_page.deny_enabled(PENDING_CLINIC)
    assert admin_page.approve_enabled(PENDING_CLINIC)
    assert admin_page.request_bodies(DENY_URL) == [{"denialReason": DENIAL_REASON}]
    assert admin_page.errors() == []


def test_deny_with_empty_reason_is_still_sent(admin_page, sign_in):
    application = stub_application(90501, PENDING_CLINIC)
    sign_in("admin")
    admin_page.install_routes(
        [
            route(
                DENY_URL,
                dict(application, status="DENIED", denialReason=""),
                method="PATCH",
            ),
            route(APPLICATIONS_URL, [application], method="GET"),
        ]
    )
    admin_page.open_from_nav().wait_for_application_names([PENDING_CLINIC])
    admin_page.deny(PENDING_CLINIC).accept_dialog()
    admin_page.wait_for_application_status(PENDING_CLINIC, "DENIED")

    assert admin_page.application_denial(PENDING_CLINIC) == ""
    assert admin_page.request_bodies(DENY_URL) == [{"denialReason": ""}]
    assert admin_page.errors() == []


def test_deny_failure_shows_error(admin_page, sign_in):
    sign_in("admin")
    admin_page.install_routes(
        [
            route(DENY_URL, {"error": NOT_FOUND_ERROR}, 400, method="PATCH"),
            route(
                APPLICATIONS_URL,
                [stub_application(90501, PENDING_CLINIC)],
                method="GET",
            ),
        ]
    )
    admin_page.open_from_nav().wait_for_application_names([PENDING_CLINIC])
    admin_page.deny(PENDING_CLINIC).accept_dialog(DENIAL_REASON)
    admin_page.wait_for_error(NOT_FOUND_ERROR)

    assert admin_page.application_status(PENDING_CLINIC) == "PENDING"
    assert admin_page.application_denial(PENDING_CLINIC) == ""
    assert admin_page.deny_enabled(PENDING_CLINIC)


def test_already_denied_application_cannot_be_denied_again(admin_page, sign_in):
    sign_in("admin")
    admin_page.install_routes(
        [
            route(
                APPLICATIONS_URL,
                [
                    stub_application(
                        90503,
                        "Denied Paws",
                        status="DENIED",
                        denialReason=DENIAL_REASON,
                    )
                ],
                method="GET",
            )
        ]
    )
    admin_page.open_from_nav().wait_for_application_names(["Denied Paws"])

    assert admin_page.application_status("Denied Paws") == "DENIED"
    assert not admin_page.deny_enabled("Denied Paws")
    assert admin_page.approve_enabled("Denied Paws")
    assert admin_page.request_count(DENY_URL, "PATCH") == 0


def test_selecting_clinic_lists_its_reviews(admin_page, sign_in):
    sign_in("admin")
    admin_page.install_routes(
        [
            route(APPLICATIONS_URL, [], method="GET"),
            route(
                CLINICS_URL,
                [stub_clinic(90601, "Alpha Vet"), stub_clinic(90602, "Beta Vet")],
                method="GET",
            ),
            route(
                CLINIC_REVIEWS_URL + "90601",
                [
                    stub_clinic_review(90701),
                    stub_clinic_review(
                        90702,
                        reviewerName="Second Reviewer",
                        reviewerUsername="second.reviewer",
                        rating=3,
                        comment="",
                    ),
                ],
                method="GET",
            ),
            route(CLINIC_REVIEWS_URL, [], method="GET"),
        ]
    )
    admin_page.open_from_nav().wait_for_clinic_names(["Alpha Vet", "Beta Vet"])
    admin_page.select_clinic("Alpha Vet").wait_for_review_count(2)

    assert admin_page.selected_clinic_name() == "Alpha Vet"
    assert admin_page.active_clinic_names() == ["Alpha Vet"]
    assert admin_page.reviews() == [
        {
            "reviewer": "Stub Reviewer",
            "username": "@stub.reviewer",
            "rating": "★★★★★",
            "comment": "Great care.",
            "date": "Feb 20, 2026",
        },
        {
            "reviewer": "Second Reviewer",
            "username": "@second.reviewer",
            "rating": "★★★",
            "comment": "No comment",
            "date": "Feb 20, 2026",
        },
    ]
    assert admin_page.errors() == []


def test_clinic_rows_show_review_count_and_average(admin_page, sign_in):
    sign_in("admin")
    admin_page.install_routes(
        [
            route(APPLICATIONS_URL, [], method="GET"),
            route(
                CLINICS_URL,
                [stub_clinic(90601, "Alpha Vet"), stub_clinic(90602, "Beta Vet")],
                method="GET",
            ),
            route(
                CLINIC_REVIEWS_URL + "90601",
                [
                    stub_clinic_review(90701, rating=5),
                    stub_clinic_review(90702, rating=4),
                ],
                method="GET",
            ),
            route(
                CLINIC_REVIEWS_URL + "90602",
                [stub_clinic_review(90703, rating=2)],
                method="GET",
            ),
        ]
    )
    admin_page.open_from_nav().wait_for_clinic_names(["Alpha Vet", "Beta Vet"])
    admin_page.wait_for_clinic_stats("Alpha Vet", "2 reviews | 4.5 stars")

    assert admin_page.clinic_stats("Beta Vet") == "1 reviews | 2.0 stars"
    assert admin_page.clinic_location("Alpha Vet") == "Skopje | Testna 1"
    assert admin_page.errors() == []


def test_clinic_without_reviews_shows_placeholder(admin_page, sign_in):
    sign_in("admin")
    admin_page.install_routes(
        [
            route(APPLICATIONS_URL, [], method="GET"),
            route(CLINICS_URL, [stub_clinic(90603, "Quiet Vet")], method="GET"),
            route(CLINIC_REVIEWS_URL, [], method="GET"),
        ]
    )
    admin_page.open_from_nav().wait_for_clinic_names(["Quiet Vet"])
    admin_page.wait_for_clinic_stats("Quiet Vet", "0 reviews | 0.0 stars")
    admin_page.select_clinic("Quiet Vet").wait_for_reviews_empty()

    assert admin_page.selected_clinic_name() == "Quiet Vet"
    assert admin_page.reviews() == []
    assert admin_page.reviews_empty_text() == NO_REVIEWS_TEXT
    assert admin_page.errors() == []
