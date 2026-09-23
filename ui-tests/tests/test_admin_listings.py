import pytest

from pages.admin_listings_page import (
    AdminListingsPage,
    LISTINGS_URL,
    PETS_URL,
    USERS_URL,
    route,
    stub_listing,
    stub_owner,
    stub_page,
    stub_pet,
)
from pages.login_page import LoginPage

PAGE_TITLE = "Listings"
PANEL_TITLE = "All Listings"
NO_LISTINGS_TEXT = "No listings found."
NO_MATCHES_TEXT = "No listings match the selected filters."
FORBIDDEN_ERROR = "Admin access required"
STATUS_BADGES = {
    "ACTIVE": "bg-success",
    "SOLD": "bg-secondary",
    "DRAFT": "bg-dark",
    "ARCHIVED": "bg-dark",
}


@pytest.fixture
def listings_page(driver, base_url):
    return AdminListingsPage(driver, base_url)


@pytest.fixture
def sign_in(driver, base_url, accounts):
    def run(name):
        account = accounts[name]
        page = LoginPage(driver, base_url)
        page.open().login_as(account.username, account.password)
        page.wait_for_redirect_to("/")

    return run


def three_listings():
    return [
        stub_listing(92201, animalId=92101, ownerId=92001, price=120),
        stub_listing(
            92202,
            animalId=92102,
            ownerId=92002,
            price=250.5,
            status="SOLD",
            description="Calm senior cat.",
        ),
        stub_listing(
            92203,
            animalId=92103,
            ownerId=92001,
            price=80,
            description="Tiny parrot.",
        ),
    ]


def name_routes():
    return [
        route(
            USERS_URL,
            [stub_owner(92001, "Olive", "Owner"), stub_owner(92002, "Sam", "Seller")],
            method="GET",
        ),
        route(PETS_URL + "92101", stub_pet(92101, "Rex"), method="GET"),
        route(PETS_URL + "92102", stub_pet(92102, "Whiskers"), method="GET"),
        route(PETS_URL + "92103", stub_pet(92103, "Kiwi"), method="GET"),
    ]


def open_with_pages(page, pages):
    page.install_routes(pages + name_routes())
    page.open_from_nav().wait_until_loaded()
    return page


def open_with_listings(page, items=None, **overrides):
    items = three_listings() if items is None else items
    return open_with_pages(
        page, [route(LISTINGS_URL, stub_page(items, **overrides), method="GET")]
    )


def two_pages():
    return [
        route(
            "page=1",
            stub_page(
                [stub_listing(92204, animalId=92103, price=60)],
                page=1,
                totalItems=2,
                totalPages=2,
                hasPrevious=True,
            ),
            method="GET",
        ),
        route(
            LISTINGS_URL,
            stub_page(
                [stub_listing(92201, animalId=92101)],
                totalItems=2,
                totalPages=2,
                hasNext=True,
            ),
            method="GET",
        ),
    ]


def test_guest_is_redirected_to_login(listings_page):
    listings_page.open().wait_for_login_redirect()

    assert not listings_page.has_page()


def test_non_admin_user_is_redirected_to_listings(listings_page, sign_in):
    sign_in("client")
    listings_page.open().wait_for_listings_redirect()

    assert not listings_page.has_page()


def test_admin_sees_all_listings(listings_page, sign_in):
    sign_in("admin")
    listings_page.open().wait_until_loaded()

    assert listings_page.page_title() == PAGE_TITLE
    assert listings_page.panel_title() == PANEL_TITLE
    assert listings_page.summary().startswith("Total: ")
    assert "UiBeagle" in listings_page.pet_names()
    assert {
        "pet": "UiBeagle",
        "owner": "Olive Owner",
        "status": "ACTIVE",
        "description": "UI test beagle from Ohrid.",
        "price": "$120.00",
    }.items() <= next(
        card for card in listings_page.cards() if card["pet"] == "UiBeagle"
    ).items()
    assert listings_page.errors() == []


def test_listings_table_is_populated(listings_page, sign_in):
    sign_in("admin")
    open_with_listings(listings_page)

    assert listings_page.summary() == "Total: 3 | Active: 2 | Sold: 1"
    assert listings_page.page_meta() == ["Page 1 / 1 (size: 500)", "Page 1 / 1"]
    assert listings_page.cards() == [
        {
            "pet": "Rex",
            "owner": "Olive Owner",
            "status": "ACTIVE",
            "description": "Stubbed admin listing.",
            "price": "$120.00",
            "date": "Mar 5, 2026",
        },
        {
            "pet": "Whiskers",
            "owner": "Sam Seller",
            "status": "SOLD",
            "description": "Calm senior cat.",
            "price": "$250.50",
            "date": "Mar 5, 2026",
        },
        {
            "pet": "Kiwi",
            "owner": "Olive Owner",
            "status": "ACTIVE",
            "description": "Tiny parrot.",
            "price": "$80.00",
            "date": "Mar 5, 2026",
        },
    ]
    assert listings_page.card_link("Rex") == "/listing/92201"
    assert listings_page.filter_summary() == ""
    assert listings_page.errors() == []


def test_empty_listings_show_placeholder(listings_page, sign_in):
    sign_in("admin")
    open_with_listings(listings_page, [])

    assert listings_page.cards() == []
    assert listings_page.empty_text() == NO_LISTINGS_TEXT
    assert listings_page.summary() == "Total: 0 | Active: 0 | Sold: 0"
    assert listings_page.page_meta()[0] == "Page 1 / 1 (size: 500)"


def test_listings_error_is_shown(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(
        listings_page,
        [route(LISTINGS_URL, {"error": FORBIDDEN_ERROR}, 403, method="GET")],
    )

    assert listings_page.errors() == [FORBIDDEN_ERROR]
    assert listings_page.cards() == []
    assert listings_page.empty_text() == NO_LISTINGS_TEXT
    assert not listings_page.has_filters()
    assert not listings_page.has_pagination()


def test_search_by_animal_name(listings_page, sign_in):
    sign_in("admin")
    open_with_listings(listings_page)
    listings_page.search("whisk").wait_for_pet_names(["Whiskers"])

    assert listings_page.filter_summary() == "Showing 1 of 3 listings."
    assert len(listings_page.listing_queries()) == 1


def test_search_by_owner_name(listings_page, sign_in):
    sign_in("admin")
    open_with_listings(listings_page)
    listings_page.search("OLIVE").wait_for_pet_names(["Rex", "Kiwi"])

    assert listings_page.filter_summary() == "Showing 2 of 3 listings."


def test_search_by_description_or_status(listings_page, sign_in):
    sign_in("admin")
    open_with_listings(listings_page)
    listings_page.search("parrot").wait_for_pet_names(["Kiwi"])
    listings_page.search("sold").wait_for_pet_names(["Whiskers"])
    listings_page.search("no such listing").wait_for_pet_names([])

    assert listings_page.empty_text() == NO_MATCHES_TEXT
    assert listings_page.filter_summary() == "Showing 0 of 3 listings."


@pytest.mark.parametrize("status", ["ACTIVE", "SOLD", "DRAFT", "ARCHIVED"])
def test_status_filter_requests_that_status(listings_page, sign_in, status):
    filtered = stub_listing(92205, animalId=92101, status=status)
    sign_in("admin")
    open_with_pages(
        listings_page,
        [
            route("status=%s" % status, stub_page([filtered]), method="GET"),
            route(LISTINGS_URL, stub_page(three_listings()), method="GET"),
        ],
    )

    assert listings_page.status_options() == ["", "ACTIVE", "SOLD", "DRAFT", "ARCHIVED"]

    listings_page.select_status(status).wait_for_listing_query_count(2)
    listings_page.wait_for_pet_names(["Rex"])

    assert listings_page.last_listing_query() == {
        "page": "0",
        "size": "500",
        "status": status,
    }
    assert listings_page.cards()[0]["status"] == status
    assert listings_page.status_badge_class("Rex") == STATUS_BADGES[status]
    assert listings_page.filter_summary() == "Showing 1 of 1 listings."


def test_min_price_only_is_sent(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(
        listings_page,
        [
            route(
                "minPrice=100",
                stub_page([stub_listing(92201, price=120)]),
                method="GET",
            ),
            route(LISTINGS_URL, stub_page(three_listings()), method="GET"),
        ],
    )
    listings_page.set_min_price("100").wait_for_listing_query_count(2)
    listings_page.wait_for_pet_names(["Rex"])

    assert listings_page.last_listing_query() == {
        "page": "0",
        "size": "500",
        "minPrice": "100",
    }


def test_max_price_only_is_sent(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(
        listings_page,
        [
            route(
                "maxPrice=100",
                stub_page([stub_listing(92203, animalId=92103, price=80)]),
                method="GET",
            ),
            route(LISTINGS_URL, stub_page(three_listings()), method="GET"),
        ],
    )
    listings_page.set_max_price("100").wait_for_listing_query_count(2)
    listings_page.wait_for_pet_names(["Kiwi"])

    assert listings_page.last_listing_query() == {
        "page": "0",
        "size": "500",
        "maxPrice": "100",
    }


def test_min_and_max_price_are_sent_together(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(
        listings_page,
        [
            route(
                "minPrice=100&maxPrice=200",
                stub_page([stub_listing(92201, price=120)]),
                method="GET",
            ),
            route(LISTINGS_URL, stub_page(three_listings()), method="GET"),
        ],
    )
    listings_page.set_min_price("100").wait_for_listing_query_count(2)
    listings_page.set_max_price("200").wait_for_listing_query_count(3)
    listings_page.wait_for_pet_names(["Rex"])

    assert listings_page.last_listing_query() == {
        "page": "0",
        "size": "500",
        "minPrice": "100",
        "maxPrice": "200",
    }
    assert listings_page.filter_summary() == "Showing 1 of 1 listings."


def test_min_price_above_max_price_shows_no_results(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(
        listings_page,
        [
            route("minPrice=300&maxPrice=100", stub_page([]), method="GET"),
            route(LISTINGS_URL, stub_page(three_listings()), method="GET"),
        ],
    )
    listings_page.set_max_price("100").wait_for_listing_query_count(2)
    listings_page.set_min_price("300").wait_for_listing_query_count(3)
    listings_page.wait_for_pet_names([])

    assert listings_page.last_listing_query() == {
        "page": "0",
        "size": "500",
        "minPrice": "300",
        "maxPrice": "100",
    }
    assert listings_page.empty_text() == NO_LISTINGS_TEXT
    assert listings_page.errors() == []


def test_non_numeric_price_is_ignored(listings_page, sign_in):
    sign_in("admin")
    open_with_listings(listings_page)
    listings_page.set_min_price("abc").set_max_price("xyz")

    assert listings_page.filter_values()["minPrice"] == ""
    assert listings_page.filter_values()["maxPrice"] == ""
    assert all(
        "minPrice" not in query and "maxPrice" not in query
        for query in listings_page.listing_queries()
    )
    assert listings_page.pet_names() == ["Rex", "Whiskers", "Kiwi"]


def test_clear_resets_every_filter(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(
        listings_page,
        [
            route("status=SOLD", stub_page([three_listings()[1]]), method="GET"),
            route(LISTINGS_URL, stub_page(three_listings()), method="GET"),
        ],
    )
    listings_page.select_status("SOLD").wait_for_pet_names(["Whiskers"])
    listings_page.search("calm").set_min_price("10").set_max_price("500")
    listings_page.clear_filters().wait_for_pet_names(["Rex", "Whiskers", "Kiwi"])

    assert listings_page.filter_values() == {
        "search": "",
        "status": "",
        "minPrice": "",
        "maxPrice": "",
    }
    assert listings_page.filter_summary() == ""


def test_clear_reloads_first_page_without_filters(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(
        listings_page,
        [route("status=ACTIVE", stub_page([three_listings()[0]]), method="GET")]
        + two_pages(),
    )
    listings_page.go_next().wait_for_page_meta("Page 2 / 2 (size: 500)")
    listings_page.select_status("ACTIVE").wait_for_pet_names(["Rex"])
    listings_page.clear_filters().wait_for_page_meta("Page 1 / 2 (size: 500)")

    assert listings_page.last_listing_query() == {"page": "0", "size": "500"}
    assert listings_page.pet_names() == ["Rex"]


def test_next_page_loads_following_results(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(listings_page, two_pages())

    assert listings_page.page_meta()[0] == "Page 1 / 2 (size: 500)"

    listings_page.go_next().wait_for_page_meta("Page 2 / 2 (size: 500)")
    listings_page.wait_for_pet_names(["Kiwi"])

    assert listings_page.last_listing_query()["page"] == "1"


def test_previous_page_returns_to_first_page(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(listings_page, two_pages())
    listings_page.go_next().wait_for_page_meta("Page 2 / 2 (size: 500)")
    listings_page.go_previous().wait_for_page_meta("Page 1 / 2 (size: 500)")
    listings_page.wait_for_pet_names(["Rex"])

    assert listings_page.last_listing_query()["page"] == "0"


def test_previous_is_disabled_on_first_page(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(listings_page, two_pages())

    assert not listings_page.is_previous_enabled()
    assert listings_page.is_next_enabled()
    assert len(listings_page.listing_queries()) == 1


def test_next_is_disabled_on_last_page(listings_page, sign_in):
    sign_in("admin")
    open_with_pages(listings_page, two_pages())
    listings_page.go_next().wait_for_page_meta("Page 2 / 2 (size: 500)")

    assert not listings_page.is_next_enabled()
    assert listings_page.is_previous_enabled()


def test_owner_and_animal_names_are_resolved(listings_page, sign_in):
    sign_in("admin")
    open_with_listings(
        listings_page,
        [
            stub_listing(92201, animalId=92101, ownerId=92001),
            stub_listing(92202, animalId=92102, ownerId=92003),
        ],
    )

    assert [(card["pet"], card["owner"]) for card in listings_page.cards()] == [
        ("Rex", "Olive Owner"),
        ("Whiskers", "Loading owner..."),
    ]


def test_missing_names_use_fallbacks(listings_page, sign_in):
    sign_in("admin")
    listings_page.install_routes(
        [
            route(
                LISTINGS_URL,
                stub_page(
                    [
                        stub_listing(92201, animalId=None, ownerId=None),
                        stub_listing(92202, animalId=92109, ownerId=92004),
                    ]
                ),
                method="GET",
            ),
            route(
                USERS_URL,
                [stub_owner(92004, "", "", username="nameless.owner")],
                method="GET",
            ),
            route(PETS_URL + "92109", {"error": "missing"}, 404, method="GET"),
        ]
    )
    listings_page.open_from_nav().wait_until_loaded()

    assert [(card["pet"], card["owner"]) for card in listings_page.cards()] == [
        ("Unknown pet", "Unknown owner"),
        ("Pet #92109", "nameless.owner"),
    ]
