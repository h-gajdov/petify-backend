import pytest

from pages.listing_details_page import ListingDetailsPage, route
from pages.listings_page import ListingsPage, stub_row
from pages.login_page import LoginPage

BEAGLE = "UiBeagle"
CORGI = "UiCorgi"
SIAMESE = "UiSiamese"
CANARY = "UiCanary"

BEAGLE_TITLE = "UI test beagle from Ohrid."
CORGI_TITLE = "UI test corgi from Bitola."
OWNER_NAME = "Olive Owner"

FAVORITE_LOGIN_ALERT = "Please log in to save favorites"
FAVORITE_FAILURE_ALERT = "Failed to update favorite. Please try again."
NO_EMAIL_ALERT = "Owner contact email is not available"
NO_OWNER_ALERT = "Owner information not available"
COPY_FAILURE_ALERT = "Failed to copy link"
COPY_IDLE_LABEL = "Copy link"
COPY_DONE_LABEL = "✓ Copied!"
LOAD_ERROR_TITLE = "Failed to load listing"
NOT_FOUND_DETAIL = "Failed to load listing (404)"
HEALTH_EMPTY_TEXT = "No health records have been added yet."
HEALTH_ERROR_TEXT = "Simulated health record failure"
MISSING_LISTING_ID = 999999
OWNER_EMAIL = "ui.owner@petify.test"
PET_PLACEHOLDER = "all_outline"
BROKEN_PHOTO_URL = "http://127.0.0.1:9/broken-photo.jpg"


@pytest.fixture
def details_page(driver, base_url):
    return ListingDetailsPage(driver, base_url)


@pytest.fixture
def listings_page(driver, base_url):
    return ListingsPage(driver, base_url)


@pytest.fixture
def sign_in(driver, base_url, accounts):
    def run(name):
        account = accounts[name]
        page = LoginPage(driver, base_url)
        page.open().login_as(account.username, account.password)
        page.wait_for_redirect_to("/")

    return run


def stub_pet(animal_id, name="StubPet"):
    return {
        "animalId": animal_id,
        "name": name,
        "sex": "FEMALE",
        "type": "Dog",
        "species": "Dog",
        "breed": "Beagle",
    }


def test_valid_listing_opens_from_listings(listings_page, details_page, listing_ids):
    listings_page.open().open_card(BEAGLE)
    details_page.wait_for_listing(listing_ids[BEAGLE]).wait_until_loaded()

    assert details_page.title() == BEAGLE_TITLE
    assert BEAGLE in details_page.kicker()
    assert OWNER_NAME in details_page.kicker()


def test_invalid_listing_id_shows_error(details_page):
    details_page.open(MISSING_LISTING_ID).wait_for_error()

    assert LOAD_ERROR_TITLE in details_page.error_text()
    assert details_page.error_detail() == NOT_FOUND_DETAIL


def test_direct_deep_link_renders_listing(details_page, listing_ids):
    details_page.open(listing_ids[SIAMESE]).wait_until_loaded()

    assert details_page.title() == "UI test siamese from Ohrid."
    assert SIAMESE in details_page.kicker()
    assert details_page.has_related_section()


def test_price_and_posted_date_are_formatted(details_page, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()

    assert details_page.price_text() == "$120.00"
    assert details_page.posted_text().startswith("Posted ")
    assert "2026" in details_page.posted_text()
    assert "T" not in details_page.posted_text()


def test_missing_price_and_date_are_hidden(details_page):
    details_page.open_stubbed(
        stub_row(animal_name="StubNoPrice", price=None, created_at=None)
    )

    assert details_page.title() == "StubNoPrice"
    assert not details_page.has_price()
    assert not details_page.has_posted_date()


def test_location_is_shown_for_listing_with_city(details_page):
    details_page.open_stubbed(
        stub_row(animal_name="StubWithCity", located_name="Ohrid")
    )

    assert details_page.has_location_card()
    assert details_page.location_text() == "Ohrid"


def test_listing_without_location_hides_location_card(details_page, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()

    assert not details_page.has_location_card()


def test_guest_favorite_shows_login_alert(details_page, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    details_page.toggle_favorite()

    assert details_page.alert_text() == FAVORITE_LOGIN_ALERT
    assert not details_page.is_favorited()


def test_favorite_is_saved(details_page, sign_in, favorite_api, listing_ids):
    sign_in("favorites")
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()

    assert not details_page.is_favorited()
    assert details_page.save_label() == "Save"

    details_page.toggle_favorite().wait_until_favorited(True)

    assert details_page.save_label() == "Saved"
    assert favorite_api.wait_for({listing_ids[BEAGLE]}) == {listing_ids[BEAGLE]}


def test_favorite_is_removed(details_page, sign_in, favorite_api, listing_ids):
    favorite_api.add(listing_ids[BEAGLE])
    sign_in("favorites")
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()

    assert details_page.is_favorited()

    details_page.toggle_favorite().wait_until_favorited(False)

    assert details_page.save_label() == "Save"
    assert favorite_api.wait_for(set()) == set()


def test_favorite_survives_reload(details_page, sign_in, favorite_api, listing_ids):
    sign_in("favorites")
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    details_page.toggle_favorite().wait_until_favorited(True)

    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()

    assert details_page.is_favorited()
    assert details_page.save_label() == "Saved"
    assert favorite_api.wait_for({listing_ids[BEAGLE]}) == {listing_ids[BEAGLE]}


def test_favorite_api_failure_shows_alert(
    details_page, sign_in, favorite_api, listing_ids
):
    sign_in("favorites")
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    details_page.install_routes(
        [route("/api/favorites/", {"error": "Simulated failure"}, 500)]
    )
    details_page.toggle_favorite()

    assert details_page.alert_text() == FAVORITE_FAILURE_ALERT
    assert not details_page.is_favorited()
    assert favorite_api.ids() == set()


def test_contact_owner_without_email_shows_alert(details_page):
    details_page.open_stubbed(
        stub_row(animal_name="StubNoEmail", owner_id=90701),
        routes=[
            route(
                "/api/users/90701",
                {
                    "userId": 90701,
                    "username": "stub.owner",
                    "firstName": "Stub",
                    "lastName": "Owner",
                },
            )
        ],
    )
    details_page.contact_owner()

    assert details_page.alert_text() == NO_EMAIL_ALERT


def test_see_owner_opens_owner_profile(details_page, listing_ids, account_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    details_page.see_owner()

    details_page.wait_for_owner_profile(account_ids("owner"))


def test_see_owner_without_owner_shows_alert(details_page):
    details_page.open_stubbed(stub_row(animal_name="StubNoOwner", owner_id=None))
    details_page.see_owner()

    assert details_page.alert_text() == NO_OWNER_ALERT


def test_copy_link_copies_url_and_reverts_label(details_page, driver, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    details_page.stub_clipboard(True)

    assert details_page.copy_label() == COPY_IDLE_LABEL

    details_page.copy_link().wait_for_copy_label(COPY_DONE_LABEL)

    assert details_page.copied_text() == driver.current_url

    details_page.wait_for_copy_label(COPY_IDLE_LABEL)


def test_copy_link_failure_shows_alert(details_page, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    details_page.stub_clipboard(False)
    details_page.copy_link()

    assert details_page.alert_text() == COPY_FAILURE_ALERT
    assert details_page.copy_label() == COPY_IDLE_LABEL


def test_health_records_are_listed(details_page, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    records = details_page.health_records()

    assert len(records) == 1
    assert records[0]["type"] == "Vaccination"
    assert records[0]["description"] == "UI test rabies shot."
    assert records[0]["clinic"] == "UI Test Clinic"
    assert "2025" in records[0]["date"]
    assert "Feb" in records[0]["date"]


def test_listing_without_health_records_shows_empty_state(details_page, listing_ids):
    details_page.open(listing_ids[CORGI]).wait_until_loaded()

    assert details_page.health_records() == []
    assert details_page.health_empty_text() == HEALTH_EMPTY_TEXT


def test_health_records_error_is_shown(details_page):
    details_page.open_stubbed(
        stub_row(animal_name="StubHealth", animal_id=90501),
        routes=[
            route(
                "/api/pets/90501/health-records",
                {"error": HEALTH_ERROR_TEXT},
                500,
            ),
            route("/api/pets/90501", stub_pet(90501)),
        ],
    )

    assert details_page.health_error_text() == HEALTH_ERROR_TEXT
    assert details_page.health_records() == []


def test_pet_name_scrolls_to_health_records(details_page, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    details_page.scroll_to_top().focus_pet_name()

    assert details_page.health_card_offset() > 5

    details_page.click_pet_name().wait_until_health_card_at_top()

    assert abs(details_page.health_card_offset()) <= 5


def test_related_listings_exclude_current_listing(details_page, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    titles = details_page.related_titles()

    assert details_page.has_related_section()
    assert BEAGLE not in titles
    assert CORGI in titles
    assert SIAMESE in titles
    assert CANARY in titles


def test_related_listing_can_be_favorited(
    details_page, sign_in, favorite_api, listing_ids
):
    sign_in("favorites")
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()

    assert not details_page.is_related_favorited(CORGI)

    details_page.toggle_related_favorite(CORGI)
    details_page.wait_until_related_favorited(CORGI, True)

    assert not details_page.is_favorited()
    assert favorite_api.wait_for({listing_ids[CORGI]}) == {listing_ids[CORGI]}


def test_related_listing_click_reloads_details(details_page, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    details_page.open_related(CORGI)

    details_page.wait_for_listing(listing_ids[CORGI])
    details_page.wait_until_loaded().wait_for_title(CORGI_TITLE)

    assert CORGI in details_page.kicker()
    assert BEAGLE in details_page.related_titles()
    assert CORGI not in details_page.related_titles()


def test_related_section_hidden_without_other_listings(details_page):
    details_page.open_stubbed(stub_row(animal_name="StubOnly"))

    assert details_page.title() == "StubOnly"
    assert not details_page.has_related_section()
    assert details_page.related_titles() == []


def test_load_error_can_be_retried(details_page, listings_page):
    listing = stub_row(animal_name="StubRetry")
    listings_page.open()
    details_page.install_routes(
        [
            route("/api/public/listings", [listing]),
            route("/api/listings/%s" % listing["listing_id"], {"error": "down"}, 500),
        ]
    )
    listings_page.reload().open_card("StubRetry")
    details_page.wait_for_error()

    assert LOAD_ERROR_TITLE in details_page.error_text()
    assert details_page.error_detail() == "Failed to load listing (500)"

    details_page.install_routes(
        [route("/api/listings/%s" % listing["listing_id"], listing)]
    )
    details_page.retry().wait_until_loaded()

    assert details_page.title() == "StubRetry"


def test_contact_owner_opens_prefilled_mailto(details_page, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()
    details_page.record_navigations().contact_owner()

    assert details_page.recorded_mailto() == {
        "to": OWNER_EMAIL,
        "subject": "Question about UiBeagle on Petify",
        "body": "Hi Olive Owner,\n\nI saw your listing for UiBeagle on Petify "
        "and would like to know more.\n\nThanks!",
    }


def test_missing_photo_shows_placeholder_image(details_page, listing_ids):
    details_page.open(listing_ids[BEAGLE]).wait_until_loaded()

    assert PET_PLACEHOLDER in details_page.image_src()


def test_broken_photo_url_falls_back_to_placeholder(details_page):
    details_page.open_stubbed(
        stub_row(animal_name="StubBroken", photo_url=BROKEN_PHOTO_URL)
    )
    details_page.wait_for_image_src(PET_PLACEHOLDER)

    assert BROKEN_PHOTO_URL not in details_page.image_src()
