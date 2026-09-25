import pytest

from pages.admin_clients_page import (
    AdminClientsPage,
    BLOCK_URL,
    REVIEWS_BY_URL,
    REVIEWS_URL,
    USERS_URL,
    route,
    stub_review,
    stub_user,
)
from pages.login_page import LoginPage

PAGE_TITLE = "Clients"
PANEL_TITLE = "Client Review Moderation"
COLUMN_TITLES = ["Reviews for them", "Reviews left by them"]
SELECT_CLIENT_TEXT = "Select a client or owner to inspect reviews."
NO_CLIENTS_TEXT = "No clients or owners found."
NO_REVIEWS_RECEIVED = "No reviews received."
NO_REVIEWS_LEFT = "No reviews left."
USERS_ERROR = "Failed to fetch all users"
BLOCKED_PREFIX = "Your account has been blocked. Reason:"
BLOCK_REASON = "Abusive reviews"
ALPHA = "Alpha Client"
BETA = "Beta Owner"


@pytest.fixture
def clients_page(driver, base_url):
    return AdminClientsPage(driver, base_url)


@pytest.fixture
def login_page(driver, base_url):
    return LoginPage(driver, base_url)


@pytest.fixture
def sign_in(driver, base_url, accounts):
    def run(name):
        account = accounts[name]
        page = LoginPage(driver, base_url)
        page.open().login_as(account.username, account.password)
        page.wait_for_redirect_to("/")

    return run


def two_users(**beta_overrides):
    return [
        stub_user(91001, "Alpha", "Client"),
        stub_user(91002, "Beta", "Owner", userType="OWNER", **beta_overrides),
    ]


def open_with_users(page, users, routes=()):
    page.install_routes(
        list(routes)
        + [
            route(USERS_URL, users, method="GET"),
            route(REVIEWS_BY_URL, [], method="GET"),
            route(REVIEWS_URL, [], method="GET"),
        ]
    )
    page.open_from_nav().wait_until_loaded()
    return page


def test_guest_is_redirected_to_login(clients_page):
    clients_page.open().wait_for_login_redirect()

    assert not clients_page.has_page()


def test_non_admin_user_is_redirected_to_listings(clients_page, sign_in):
    sign_in("client")
    clients_page.open().wait_for_listings_redirect()

    assert not clients_page.has_page()


def test_admin_sees_client_moderation_page(clients_page, sign_in):
    sign_in("admin")
    clients_page.open().wait_until_loaded()

    assert clients_page.page_title() == PAGE_TITLE
    assert clients_page.panel_title() == PANEL_TITLE
    assert clients_page.placeholder_text() == SELECT_CLIENT_TEXT
    assert "Uma Client" in clients_page.client_names()
    assert clients_page.errors() == []


def test_client_list_is_populated(clients_page, sign_in):
    sign_in("admin")
    open_with_users(clients_page, two_users())

    assert clients_page.client_rows() == [
        {
            "name": ALPHA,
            "handle": "@alpha.client | CLIENT",
            "stats": "0 reviews for them | 0.0 stars",
            "blocked": "",
        },
        {
            "name": BETA,
            "handle": "@beta.owner | OWNER",
            "stats": "0 reviews for them | 0.0 stars",
            "blocked": "",
        },
    ]
    assert clients_page.errors() == []


def test_empty_client_list_shows_placeholder(clients_page, sign_in):
    sign_in("admin")
    open_with_users(clients_page, [])

    assert clients_page.client_rows() == []
    assert clients_page.list_empty_text() == NO_CLIENTS_TEXT
    assert clients_page.errors() == []


def test_client_list_error_is_shown(clients_page, sign_in):
    sign_in("admin")
    clients_page.install_routes(
        [route(USERS_URL, {"error": "down"}, 500, method="GET")]
    )
    clients_page.open_from_nav().wait_for_error(USERS_ERROR)

    assert clients_page.client_rows() == []
    assert clients_page.list_empty_text() == NO_CLIENTS_TEXT


def test_search_matches_client(clients_page, sign_in):
    sign_in("admin")
    open_with_users(clients_page, two_users())
    clients_page.search("alpha").wait_for_client_names([ALPHA])

    assert clients_page.client_names() == [ALPHA]


def test_search_without_match_shows_placeholder(clients_page, sign_in):
    sign_in("admin")
    open_with_users(clients_page, two_users())
    clients_page.search("nobody-matches").wait_for_client_names([])

    assert clients_page.list_empty_text() == NO_CLIENTS_TEXT


def test_clearing_search_restores_all_clients(clients_page, sign_in):
    sign_in("admin")
    open_with_users(clients_page, two_users())
    clients_page.search("beta").wait_for_client_names([BETA])
    clients_page.clear_search().wait_for_client_names([ALPHA, BETA])

    assert clients_page.search_value() == ""


def test_search_is_case_insensitive(clients_page, sign_in):
    sign_in("admin")
    open_with_users(clients_page, two_users())
    clients_page.search("ALPHA.CLIENT@PETIFY").wait_for_client_names([ALPHA])

    clients_page.search("bEtA oWnEr").wait_for_client_names([BETA])


def test_selecting_client_lists_reviews_about_them(clients_page, sign_in):
    sign_in("admin")
    open_with_users(
        clients_page,
        two_users(),
        routes=[
            route(
                REVIEWS_URL + "91001",
                [
                    stub_review(91101),
                    stub_review(
                        91102,
                        reviewerUsername="second.reviewer",
                        rating=2,
                        comment="",
                    ),
                ],
                method="GET",
            )
        ],
    )
    clients_page.select_client(ALPHA).wait_for_review_counts(2, 0)

    assert clients_page.selected_details() == "@alpha.client | alpha.client@petify.test"
    assert clients_page.active_client_names() == [ALPHA]
    assert clients_page.column_titles() == COLUMN_TITLES
    assert clients_page.reviews_for() == [
        {
            "rating": "★★★★★",
            "comment": "Friendly and honest.",
            "meta": "By @stub.reviewer on Feb 20, 2026",
        },
        {
            "rating": "★★",
            "comment": "No comment",
            "meta": "By @second.reviewer on Feb 20, 2026",
        },
    ]
    assert clients_page.reviews_by_empty_text() == NO_REVIEWS_LEFT
    assert clients_page.errors() == []


def test_selecting_client_lists_reviews_left_by_them(clients_page, sign_in):
    sign_in("admin")
    open_with_users(
        clients_page,
        two_users(),
        routes=[
            route(
                REVIEWS_BY_URL + "91002",
                [stub_review(91103, rating=4, comment="Smooth handover.")],
                method="GET",
            )
        ],
    )
    clients_page.select_client(BETA).wait_for_review_counts(0, 1)

    assert clients_page.reviews_by() == [
        {"rating": "★★★★", "comment": "Smooth handover.", "meta": "Feb 20, 2026"}
    ]
    assert clients_page.reviews_for_empty_text() == NO_REVIEWS_RECEIVED
    assert clients_page.request_count(REVIEWS_BY_URL + "91002", "GET") == 1


def test_client_rows_show_review_count_and_average(clients_page, sign_in):
    sign_in("admin")
    open_with_users(
        clients_page,
        two_users(),
        routes=[
            route(
                REVIEWS_URL + "91001",
                [stub_review(91101, rating=5), stub_review(91102, rating=2)],
                method="GET",
            ),
            route(REVIEWS_URL + "91002", [stub_review(91103, rating=4)], method="GET"),
        ],
    )
    clients_page.wait_for_client_stats(ALPHA, "2 reviews for them | 3.5 stars")

    assert clients_page.client_row_data(BETA)["stats"] == "1 reviews for them | 4.0 stars"


def test_client_without_reviews_shows_empty_columns(clients_page, sign_in):
    sign_in("admin")
    open_with_users(clients_page, two_users())
    clients_page.select_client(ALPHA).wait_for_review_counts(0, 0)

    assert clients_page.reviews_for_empty_text() == NO_REVIEWS_RECEIVED
    assert clients_page.reviews_by_empty_text() == NO_REVIEWS_LEFT
    assert clients_page.errors() == []


def test_block_with_reason_sends_request(clients_page, sign_in):
    sign_in("admin")
    open_with_users(
        clients_page, two_users(), routes=[route(BLOCK_URL, None, method="PATCH")]
    )
    clients_page.select_client(ALPHA)

    assert clients_page.has_block_button()

    clients_page.block().accept_dialog(BLOCK_REASON)
    clients_page.wait_for_unblock_button()

    assert not clients_page.has_block_button()
    assert clients_page.request_bodies(BLOCK_URL) == [
        {"isBlocked": True, "blockedReason": BLOCK_REASON}
    ]
    assert clients_page.request_count("/api/users/admin/91001/block", "PATCH") == 1


def test_block_with_empty_reason_shows_no_reason(clients_page, sign_in):
    sign_in("admin")
    open_with_users(
        clients_page, two_users(), routes=[route(BLOCK_URL, None, method="PATCH")]
    )
    clients_page.select_client(ALPHA).block().accept_dialog("")
    clients_page.wait_for_client_blocked(ALPHA, "Blocked: No reason")

    assert clients_page.has_unblock_button()
    assert clients_page.request_bodies(BLOCK_URL) == [
        {"isBlocked": True, "blockedReason": ""}
    ]


def test_block_updates_badge_in_client_list(clients_page, sign_in):
    sign_in("admin")
    open_with_users(
        clients_page, two_users(), routes=[route(BLOCK_URL, None, method="PATCH")]
    )

    assert clients_page.client_row_data(ALPHA)["blocked"] == ""

    clients_page.select_client(ALPHA).block().accept_dialog(BLOCK_REASON)
    clients_page.wait_for_client_blocked(ALPHA, "Blocked: %s" % BLOCK_REASON)
    clients_page.select_client(BETA).select_client(ALPHA)

    assert clients_page.client_row_data(ALPHA)["blocked"] == "Blocked: %s" % BLOCK_REASON
    assert clients_page.client_row_data(BETA)["blocked"] == ""
    assert clients_page.has_unblock_button()


def test_blocked_user_cannot_log_in(
    clients_page, login_page, sign_in, registered_account, block_api
):
    account, user_id = registered_account()
    sign_in("admin")
    clients_page.open().wait_until_loaded()
    clients_page.search(account.username).wait_for_client_names(["Ui Registered"])
    clients_page.select_client("Ui Registered").block().accept_dialog(BLOCK_REASON)
    clients_page.wait_for_client_blocked(
        "Ui Registered", "Blocked: %s" % BLOCK_REASON
    )
    login_page.open().login_as(account.username, account.password)

    message = login_page.error_message()
    assert message.startswith(BLOCKED_PREFIX)
    assert BLOCK_REASON in message
    assert login_page.stored_user()["username"] == "ui.admin"

    block_api(user_id, False)


def test_unblock_sends_request_and_clears_badge(clients_page, sign_in):
    sign_in("admin")
    open_with_users(
        clients_page,
        two_users(isBlocked=True, blockedReason=BLOCK_REASON),
        routes=[route(BLOCK_URL, None, method="PATCH")],
    )

    assert clients_page.client_row_data(BETA)["blocked"] == "Blocked: %s" % BLOCK_REASON

    clients_page.select_client(BETA).unblock().wait_for_block_button()
    clients_page.wait_for_client_blocked(BETA, "")

    assert clients_page.request_bodies(BLOCK_URL) == [
        {"isBlocked": False, "blockedReason": ""}
    ]


def test_unblocked_user_can_log_in_again(
    clients_page, login_page, sign_in, registered_account, block_api
):
    account, user_id = registered_account()
    block_api(user_id, True, BLOCK_REASON)
    sign_in("admin")
    clients_page.open().wait_until_loaded()
    clients_page.search(account.username).wait_for_client_names(["Ui Registered"])
    clients_page.select_client("Ui Registered").unblock().wait_for_block_button()
    clients_page.wait_for_client_blocked("Ui Registered", "")
    login_page.open().login_as(account.username, account.password)
    login_page.wait_for_redirect_to("/")

    assert login_page.stored_user()["username"] == account.username


def test_client_type_is_rendered_for_clients(clients_page, sign_in):
    sign_in("admin")
    open_with_users(
        clients_page,
        [
            stub_user(91001, "Alpha", "Client"),
            stub_user(91003, "Gamma", "Client", userType="client"),
            stub_user(91004, "Delta", "Client", userType=None),
        ],
    )

    assert [row["handle"] for row in clients_page.client_rows()] == [
        "@alpha.client | CLIENT",
        "@gamma.client | CLIENT",
        "@delta.client | CLIENT",
    ]


def test_owner_type_is_rendered_for_owners(clients_page, sign_in):
    sign_in("admin")
    open_with_users(
        clients_page,
        [
            stub_user(91002, "Beta", "Owner", userType="OWNER"),
            stub_user(91005, "Omega", "Owner", userType="owner"),
        ],
    )

    assert [row["handle"] for row in clients_page.client_rows()] == [
        "@beta.owner | OWNER",
        "@omega.owner | OWNER",
    ]


def test_admin_and_clinic_accounts_are_not_listed(clients_page, sign_in):
    sign_in("admin")
    open_with_users(
        clients_page,
        [
            stub_user(91001, "Alpha", "Client"),
            stub_user(91006, "Root", "Admin", userType="ADMIN"),
            stub_user(91007, "Vet", "Clinic", userType="CLINIC"),
        ],
    )

    assert clients_page.client_names() == [ALPHA]

    clients_page.search("root").wait_for_client_names([])
    clients_page.search("vet").wait_for_client_names([])
