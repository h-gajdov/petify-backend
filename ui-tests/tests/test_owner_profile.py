import pytest

from pages.login_page import LoginPage
from pages.owner_profile_page import (
    OwnerProfilePage,
    REVIEWS_URL,
    owner_routes,
    route,
    stub_owner,
    stub_owner_listing,
    stub_owner_pet,
    stub_owner_review,
)

OWNER_NAME = "Olive Owner"
OWNER_EMAIL = "ui.owner@petify.test"
SEEDED_PETS = ["UiBeagle", "UiCorgi", "UiSiamese", "UiCanary"]
LOAD_ERROR_TITLE = "Failed to load owner profile"
NO_LISTINGS_TEXT = "This owner doesn't have active listings right now."
NO_PETS_TEXT = "This owner hasn't added any pets yet."
NO_REVIEWS_TEXT = "No reviews yet. Be the first to leave a review!"
DUPLICATE_REVIEW_ERROR = "You have already reviewed this user"
NO_EMAIL_ALERT = "Owner email not available"
BROKEN_PHOTO_URL = "http://127.0.0.1:9/broken-pet.jpg"
STUB_OWNER_ID = 93001
MISSING_OWNER_ID = 999999


@pytest.fixture
def owner_page(driver, base_url):
    return OwnerProfilePage(driver, base_url)


@pytest.fixture
def sign_in(driver, base_url, accounts):
    def run(name):
        account = accounts[name]
        page = LoginPage(driver, base_url)
        page.open().login_as(account.username, account.password)
        page.wait_for_redirect_to("/")

    return run


@pytest.fixture
def sign_in_as(driver, base_url):
    def run(account):
        page = LoginPage(driver, base_url)
        page.open().login_as(account.username, account.password)
        page.wait_for_redirect_to("/")

    return run


@pytest.fixture
def owner_id(account_ids):
    return account_ids("owner")


def test_valid_owner_profile_loads(owner_page, owner_id):
    owner_page.open(owner_id).wait_until_loaded()

    assert owner_page.name() == OWNER_NAME
    assert owner_page.username() == "@ui.owner"
    assert owner_page.email() == OWNER_EMAIL
    assert owner_page.tab_labels()[:2] == ["Active Listings (4)", "Pets (4)"]
    assert sorted(owner_page.listing_pets()) == sorted(SEEDED_PETS)


def test_non_existent_owner_shows_error(owner_page):
    owner_page.open(MISSING_OWNER_ID).wait_for_error()

    assert owner_page.error_title() == LOAD_ERROR_TITLE
    assert owner_page.error_detail() != ""
    assert owner_page.name() == ""


def test_load_error_can_be_retried(owner_page):
    owner = stub_owner(STUB_OWNER_ID)
    owner_page.open_home().install_routes(
        [route(REVIEWS_URL + str(STUB_OWNER_ID), {"error": "down"}, 500)]
        + owner_routes(owner)
    )
    owner_page.navigate(STUB_OWNER_ID).wait_for_error()

    assert owner_page.error_title() == LOAD_ERROR_TITLE
    assert owner_page.error_detail().startswith("Failed to fetch reviews: 500")

    owner_page.install_routes(owner_routes(owner)).retry()

    assert owner_page.name() == "Stub Owner"
    assert owner_page.tab_labels() == [
        "Active Listings (0)",
        "Pets (0)",
        "Reviews (0)",
    ]


def test_listings_tab_is_selected_by_default(owner_page, owner_id):
    owner_page.open(owner_id).wait_until_loaded()

    assert owner_page.active_tab() == "Active Listings (4)"
    assert owner_page.section_title() == "Active Listings"


def test_pets_tab_can_be_selected(owner_page, owner_id):
    owner_page.open(owner_id).wait_until_loaded().select_tab("Pets")

    assert owner_page.active_tab() == "Pets (4)"
    assert owner_page.section_title() == "Owner's Pets"
    assert owner_page.listing_cards() == []


def test_reviews_tab_can_be_selected(owner_page):
    owner_page.open_stubbed(
        stub_owner(STUB_OWNER_ID), reviews=[stub_owner_review(93701)]
    ).select_tab("Reviews")

    assert owner_page.active_tab() == "Reviews (1)"
    assert owner_page.section_title() == "Reviews (1)"
    assert owner_page.pet_cards() == []


def test_listings_tab_shows_only_active_listings(owner_page):
    owner_page.open_stubbed(
        stub_owner(STUB_OWNER_ID),
        pets=[stub_owner_pet(93101, "Rex"), stub_owner_pet(93102, "Milo")],
        listings=[
            stub_owner_listing(93201, 93101),
            stub_owner_listing(93202, 93102, status="SOLD"),
            stub_owner_listing(93203, 93102, status="DRAFT"),
            stub_owner_listing(93204, 93102, status=None, price=0),
            stub_owner_listing(93205, 93109, status="active"),
        ],
    )

    assert owner_page.tab_labels()[0] == "Active Listings (3)"
    assert owner_page.listing_cards() == [
        {
            "status": "ACTIVE",
            "pet": "Rex",
            "description": "Stubbed owner listing.",
            "price": "$95.50",
            "date": "Apr 2, 2026",
        },
        {
            "status": "ACTIVE",
            "pet": "Milo",
            "description": "Stubbed owner listing.",
            "price": "",
            "date": "Apr 2, 2026",
        },
        {
            "status": "ACTIVE",
            "pet": "Unknown Pet",
            "description": "Stubbed owner listing.",
            "price": "$95.50",
            "date": "Apr 2, 2026",
        },
    ]


def test_listings_tab_empty_state(owner_page):
    owner_page.open_stubbed(
        stub_owner(STUB_OWNER_ID),
        listings=[stub_owner_listing(93202, 93101, status="SOLD")],
    )

    assert owner_page.tab_labels()[0] == "Active Listings (0)"
    assert owner_page.listing_cards() == []
    assert owner_page.empty_text() == NO_LISTINGS_TEXT


def test_listing_card_opens_listing_details(owner_page, owner_id, listing_ids):
    owner_page.open(owner_id).wait_until_loaded().open_listing("UiBeagle")

    owner_page.wait_for_path("/listing/%s" % listing_ids["UiBeagle"])


def test_pets_tab_lists_owner_pets(owner_page, owner_id):
    owner_page.open(owner_id).wait_until_loaded().select_tab("Pets")

    assert sorted(owner_page.pet_names()) == sorted(SEEDED_PETS)
    beagle = next(pet for pet in owner_page.pet_cards() if pet["name"] == "UiBeagle")
    assert beagle["details"] == {
        "Species": "Dog",
        "Breed": "Beagle",
        "Sex": "FEMALE",
        "DOB": "Mar 4, 2021",
    }
    assert owner_page.pet_image_state("UiBeagle") == "placeholder"


def test_pets_tab_empty_state(owner_page):
    owner_page.open_stubbed(stub_owner(STUB_OWNER_ID)).select_tab("Pets")

    assert owner_page.pet_cards() == []
    assert owner_page.empty_text() == NO_PETS_TEXT


def test_broken_pet_image_is_hidden(owner_page):
    owner_page.open_stubbed(
        stub_owner(STUB_OWNER_ID),
        pets=[
            stub_owner_pet(93101, "Rex", photoUrl=BROKEN_PHOTO_URL),
            stub_owner_pet(93102, "Milo"),
        ],
    ).select_tab("Pets")
    owner_page.wait_for_pet_image_state("Rex", "hidden")

    assert owner_page.pet_image_state("Milo") == "placeholder"


def test_reviews_are_listed(owner_page):
    owner_page.open_stubbed(
        stub_owner(STUB_OWNER_ID),
        reviews=[
            stub_owner_review(93701),
            stub_owner_review(
                93702,
                reviewerName="Second Reviewer",
                reviewerUsername="second.reviewer",
                rating=2,
                comment="Late reply.",
            ),
        ],
    ).select_tab("Reviews")

    assert owner_page.reviews() == [
        {
            "reviewer": "Stub Reviewer",
            "username": "@stub.reviewer",
            "stars": 4,
            "comment": "Great experience.",
            "date": "Apr 10, 2026",
            "deletable": False,
        },
        {
            "reviewer": "Second Reviewer",
            "username": "@second.reviewer",
            "stars": 2,
            "comment": "Late reply.",
            "date": "Apr 10, 2026",
            "deletable": False,
        },
    ]


def test_reviews_empty_state(owner_page):
    owner_page.open_stubbed(stub_owner(STUB_OWNER_ID)).select_tab("Reviews")

    assert owner_page.reviews() == []
    assert owner_page.empty_text() == NO_REVIEWS_TEXT


def test_submit_review_adds_it_to_the_list(
    owner_page, owner_id, sign_in_as, registered_account, review_api
):
    account, reviewer_id = registered_account()
    review_api.track(owner_id, reviewer_id)
    sign_in_as(account)
    owner_page.open(owner_id).wait_until_loaded().select_tab("Reviews")
    count = len(owner_page.reviews())
    owner_page.select_rating(4).type_comment("Very responsive owner.")
    owner_page.submit_review()
    owner_page.wait.until(lambda d: len(owner_page.reviews()) == count + 1)

    mine = next(
        review
        for review in owner_page.reviews()
        if review["username"] == "@" + account.username
    )
    assert mine["stars"] == 4
    assert mine["comment"] == "Very responsive owner."
    assert mine["deletable"]
    assert owner_page.selected_rating() == 0
    assert owner_page.comment_value() == ""
    assert not owner_page.is_submit_enabled()


def test_rating_is_required_to_submit(owner_page, sign_in):
    sign_in("client")
    owner_page.open_stubbed(stub_owner(STUB_OWNER_ID)).select_tab("Reviews")
    owner_page.type_comment("No rating selected.")

    assert owner_page.selected_rating() == 0
    assert not owner_page.is_submit_enabled()

    owner_page.select_rating(3)

    assert owner_page.selected_rating() == 3
    assert owner_page.is_submit_enabled()
    assert owner_page.request_bodies(REVIEWS_URL) == []


def test_guest_cannot_leave_or_delete_reviews(owner_page):
    owner_page.open_stubbed(
        stub_owner(STUB_OWNER_ID), reviews=[stub_owner_review(93701)]
    ).select_tab("Reviews")

    assert not owner_page.has_review_form()
    assert [review["deletable"] for review in owner_page.reviews()] == [False]


def test_duplicate_review_is_blocked(
    owner_page, owner_id, sign_in_as, registered_account, review_api
):
    account, reviewer_id = registered_account()
    review_api.create(owner_id, reviewer_id, 5, "First review.")
    sign_in_as(account)
    owner_page.open(owner_id).wait_until_loaded().select_tab("Reviews")
    owner_page.select_rating(2).type_comment("Second review.").submit_review()
    owner_page.wait_for_review_error(DUPLICATE_REVIEW_ERROR)

    mine = [
        review
        for review in owner_page.reviews()
        if review["username"] == "@" + account.username
    ]
    assert [review["comment"] for review in mine] == ["First review."]


def test_delete_own_review_after_confirm(
    owner_page, owner_id, sign_in_as, registered_account, review_api
):
    account, reviewer_id = registered_account()
    review_api.create(owner_id, reviewer_id, 3, "Review to delete.")
    handle = "@" + account.username
    sign_in_as(account)
    owner_page.open(owner_id).wait_until_loaded().select_tab("Reviews")
    owner_page.delete_review(handle).dismiss_dialog()

    assert handle in owner_page.reviewer_usernames()

    owner_page.delete_review(handle).accept_dialog()
    owner_page.wait.until(lambda d: handle not in owner_page.reviewer_usernames())

    assert all(
        int(review["reviewerId"]) != reviewer_id
        for review in review_api.reviews(owner_id)
    )


def test_cannot_delete_other_users_reviews(
    owner_page, sign_in_as, registered_account
):
    account, reviewer_id = registered_account()
    sign_in_as(account)
    owner_page.open_stubbed(
        stub_owner(STUB_OWNER_ID),
        reviews=[
            stub_owner_review(93701),
            stub_owner_review(
                93702,
                reviewerId=reviewer_id,
                reviewerUsername=account.username,
            ),
        ],
    ).select_tab("Reviews")

    assert [
        (review["username"], review["deletable"]) for review in owner_page.reviews()
    ] == [("@stub.reviewer", False), ("@" + account.username, True)]


def test_contact_owner_opens_mailto(owner_page, owner_id):
    owner_page.open(owner_id).wait_until_loaded()
    owner_page.record_navigations().contact_owner()

    assert owner_page.recorded_mailto() == {
        "to": OWNER_EMAIL,
        "subject": "",
        "body": "",
    }


def test_contact_owner_without_email_shows_alert(owner_page):
    owner_page.open_stubbed(stub_owner(STUB_OWNER_ID, email=None))
    owner_page.contact_owner()

    assert owner_page.alert_text() == NO_EMAIL_ALERT


def test_verified_owner_shows_badge(owner_page):
    owner_page.open_stubbed(stub_owner(STUB_OWNER_ID), verified=True)
    owner_page.wait_for_verified_badge()

    assert owner_page.verified_text() == "Top 10"


def test_unverified_owner_has_no_badge(owner_page):
    owner_page.open_stubbed(stub_owner(STUB_OWNER_ID), verified=False)

    assert not owner_page.has_verified_badge()


def test_navigating_to_another_owner_reloads_profile(owner_page):
    first = stub_owner(STUB_OWNER_ID)
    second = stub_owner(93002, "Second", "Seller")
    owner_page.open_home().install_routes(
        owner_routes(first, reviews=[stub_owner_review(93701)])
        + owner_routes(second, pets=[stub_owner_pet(93101, "Rex")])
    )
    owner_page.navigate(STUB_OWNER_ID).wait_until_loaded().select_tab("Reviews")

    assert owner_page.name() == "Stub Owner"

    owner_page.navigate(93002).wait_for_path("/owner/93002")
    owner_page.wait_for_name("Second Seller")

    assert owner_page.username() == "@second.seller"
    assert owner_page.tab_labels() == [
        "Active Listings (0)",
        "Pets (1)",
        "Reviews (0)",
    ]
