import base64

import pytest

from pages.login_page import LoginPage
from pages.profile_page import (
    FAVORITES_URL,
    LISTINGS_URL,
    MY_LISTINGS_URL,
    ProfilePage,
    route,
    stub_listing,
    stub_pet,
)
from pages.top_nav import TopNav

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwAD"
    "hgGAWjR9awAAAABJRU5ErkJggg=="
)
FIVE_MB = 5 * 1024 * 1024
OWNER_TABS = ["My Listings", "My Pets", "Favorites", "Create Listing", "Appointments"]
CLIENT_TABS = ["My Listings", "My Pets", "Favorites"]
NO_LISTINGS_TEXT = "You haven't created any listings yet."
NO_PETS_TEXT = "You don't have any pets yet."
NO_FAVORITES_TEXT = "You haven't added any favorites yet."
NEED_PET_TEXT = "You need to have at least one pet to create a listing."
REQUIRED_FIELDS_ERROR = "Please fill in all required fields"
WRONG_TYPE_ERROR = "Pet photo must be a JPG, PNG, WEBP, or GIF image"
TOO_LARGE_ERROR = "Pet photo must be 5MB or smaller"
STATUS_ERROR = "Listing cannot be marked as sold"
PET_PLACEHOLDER = "all_outline"
BROKEN_PHOTO_URL = "http://127.0.0.1:9/broken-favorite.jpg"
REX = stub_pet(94101, "Rex")
MILO = stub_pet(94102, "Milo", species="Cat", breed="Siamese", sex="MALE")
LISTING = stub_listing(94201, 94101)


@pytest.fixture
def profile_page(driver, base_url):
    return ProfilePage(driver, base_url)


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
def owner_profile(profile_page, sign_in, account_ids):
    def run(routes=(), **data):
        sign_in("owner")
        data.setdefault("pets", [REX, MILO])
        return profile_page.open_stubbed(account_ids("owner"), routes=routes, **data)

    return run


@pytest.fixture
def client_profile(profile_page, sign_in, account_ids):
    def run(routes=(), **data):
        sign_in("client")
        return profile_page.open_stubbed(account_ids("client"), routes=routes, **data)

    return run


@pytest.fixture
def photo_file(tmp_path):
    def make(name, size=len(PNG_BYTES)):
        path = tmp_path / name
        path.write_bytes(PNG_BYTES + b"\0" * max(0, size - len(PNG_BYTES)))
        return path

    return make


def pets_url(account_ids, name="owner"):
    return "/api/users/%s/pets" % account_ids(name)


def test_guest_is_redirected_to_login(profile_page):
    profile_page.open().wait_for_path("/login")

    assert profile_page.tab_labels() == []


def test_authenticated_user_sees_profile_header(profile_page, sign_in):
    sign_in("owner")
    profile_page.open_from_nav()

    assert profile_page.header() == {
        "name": "Olive Owner",
        "username": "@ui.owner",
        "email": "ui.owner@petify.test",
        "type": "OWNER",
    }
    assert not profile_page.is_not_logged_in_shown()


def test_listings_tab_is_selected_by_default(owner_profile, profile_page):
    owner_profile()

    assert profile_page.tab_labels() == OWNER_TABS
    assert profile_page.active_tab() == "My Listings"
    assert profile_page.section_titles() == ["My Listings"]


def test_pets_tab_can_be_selected(owner_profile, profile_page):
    owner_profile().select_tab("My Pets")

    assert profile_page.section_titles() == ["My Pets"]
    assert profile_page.pet_names() == ["Rex", "Milo"]


def test_favorites_tab_can_be_selected(owner_profile, profile_page):
    owner_profile().select_tab("Favorites")

    assert profile_page.section_titles() == ["Favorite Listings"]
    assert profile_page.pet_cards() == []


def test_create_listing_tab_can_be_selected(owner_profile, profile_page):
    owner_profile().select_tab("Create Listing")

    assert profile_page.section_titles() == ["Create New Listing"]
    assert profile_page.listing_pet_options() == [
        "Choose a pet...",
        "Rex (Dog)",
        "Milo (Cat)",
    ]


def test_appointments_tab_can_be_selected(owner_profile, profile_page):
    owner_profile().select_tab("Appointments")
    profile_page.wait_for_appointments_loaded()

    assert profile_page.section_titles() == ["Create Appointment"]


def test_client_without_pets_sees_only_basic_tabs(client_profile, profile_page):
    client_profile(pets=[])

    assert profile_page.tab_labels() == CLIENT_TABS
    assert profile_page.header()["type"] == "CLIENT"


def test_verified_user_sees_badge(owner_profile, profile_page):
    owner_profile(verified=True)
    profile_page.wait_for_verified_badge()

    assert profile_page.verified_text() == "Top 10"


def test_unverified_user_has_no_badge(owner_profile, profile_page):
    owner_profile(verified=False)

    assert not profile_page.has_verified_badge()


def test_my_listings_empty_state_links_to_create_listing(owner_profile, profile_page):
    owner_profile(listings=[])

    assert profile_page.listing_cards() == []
    assert NO_LISTINGS_TEXT in profile_page.empty_texts()

    profile_page.click_link("Create your first listing")
    profile_page.wait_for_active_tab("Create Listing")

    assert profile_page.section_titles() == ["Create New Listing"]


def test_my_listings_are_listed(owner_profile, profile_page):
    owner_profile(
        listings=[
            LISTING,
            stub_listing(
                94202, 94102, status="SOLD", price=80.5, description="Sold cat."
            ),
        ]
    )

    assert profile_page.listing_cards() == [
        {
            "pet": "Rex",
            "status": "ACTIVE",
            "description": "Stubbed profile listing.",
            "price": "$120.00",
            "date": "May 6, 2026",
            "select": "ACTIVE",
        },
        {
            "pet": "Milo",
            "status": "SOLD",
            "description": "Sold cat.",
            "price": "$80.50",
            "date": "May 6, 2026",
            "select": "SOLD",
        },
    ]


def test_listing_status_update_is_saved(owner_profile, profile_page):
    owner_profile(
        routes=[
            route(
                "/status",
                dict(LISTING, status="SOLD"),
                method="PATCH",
            )
        ],
        listings=[LISTING],
    )
    profile_page.change_listing_status(LISTING["description"], "SOLD")
    profile_page.wait_for_listing_statuses(["SOLD"]).wait_until_settled()

    assert profile_page.request_bodies("/api/listings/94201/status", "PATCH") == [
        {"status": "SOLD"}
    ]
    assert profile_page.request_count(MY_LISTINGS_URL, "GET") == 1


def test_listing_status_update_failure_reverts(owner_profile, profile_page):
    owner_profile(
        routes=[route("/status", {"error": STATUS_ERROR}, 400, method="PATCH")],
        listings=[LISTING],
    )
    profile_page.change_listing_status(LISTING["description"], "SOLD")
    profile_page.wait.until(
        lambda d: profile_page.request_count(MY_LISTINGS_URL, "GET") == 2
    )
    profile_page.wait_until_settled().wait_for_listing_statuses(["ACTIVE"])

    assert profile_page.listing_cards()[0]["select"] == "ACTIVE"

    profile_page.select_tab("Create Listing")

    assert profile_page.listing_form_error() == STATUS_ERROR


def test_delete_listing_after_confirm(owner_profile, profile_page):
    owner_profile(
        routes=[
            route(MY_LISTINGS_URL, [LISTING], method="GET", times=1),
            route(LISTINGS_URL + "94201", None, method="DELETE"),
        ],
        listings=[],
    )
    profile_page.wait_for_listing_count(1)
    profile_page.delete_listing(LISTING["description"]).accept_dialog()
    profile_page.wait_for_listing_count(0)

    assert profile_page.request_count(LISTINGS_URL + "94201", "DELETE") == 1
    assert NO_LISTINGS_TEXT in profile_page.empty_texts()


def test_delete_listing_dismissed_keeps_it(owner_profile, profile_page):
    owner_profile(
        routes=[route(LISTINGS_URL + "94201", None, method="DELETE")],
        listings=[LISTING],
    )
    profile_page.delete_listing(LISTING["description"]).dismiss_dialog()

    assert profile_page.request_count(LISTINGS_URL + "94201", "DELETE") == 0
    assert len(profile_page.listing_cards()) == 1


def test_pets_are_listed(owner_profile, profile_page):
    owner_profile().select_tab("My Pets")

    assert profile_page.pet_cards()[0] == {
        "name": "Rex",
        "details": {
            "Species:": "Dog",
            "Type:": "PET",
            "Breed:": "Beagle",
            "Sex:": "FEMALE",
            "DOB:": "Mar 4, 2021",
            "Location:": "Ohrid",
        },
        "buttons": ["Create Listing for Rex", "Schedule Appointment for Rex"],
    }


def test_pets_empty_state(client_profile, profile_page):
    client_profile(pets=[]).select_tab("My Pets")

    assert profile_page.pet_cards() == []
    assert profile_page.empty_texts() == [
        NO_PETS_TEXT,
        "Add pets to create listings!",
    ]


def test_add_pet_panel_opens_and_scrolls_into_view(owner_profile, profile_page):
    owner_profile().select_tab("My Pets").scroll_to_top()

    assert not profile_page.has_add_pet_panel()

    profile_page.open_add_pet()
    profile_page.wait.until(
        lambda d: d.execute_script("return window.scrollY;") > 0
    )

    assert profile_page.section_titles() == ["My Pets", "Add New Pet"]
    assert 0 <= profile_page.add_pet_panel_top() < profile_page.driver.execute_script(
        "return window.innerHeight;"
    )


def test_add_pet_panel_closes_and_resets(owner_profile, profile_page):
    owner_profile().select_tab("My Pets").open_add_pet()
    profile_page.fill_pet(name="Draft", sex="MALE", species="Dog")
    profile_page.cancel_add_pet()

    assert profile_page.section_titles() == ["My Pets"]

    profile_page.open_add_pet()

    assert profile_page.pet_form_values() == {
        "name": "",
        "sex": "",
        "species": "",
        "breed": "",
        "location": "",
    }


def test_pet_name_is_required(owner_profile, profile_page, account_ids):
    owner_profile().select_tab("My Pets").open_add_pet()
    profile_page.fill_pet(sex="MALE", species="Dog").submit_pet()

    assert profile_page.validity(ProfilePage.PET_NAME, "valueMissing")
    assert profile_page.request_count(pets_url(account_ids), "POST") == 0


def test_pet_sex_is_required(owner_profile, profile_page, account_ids):
    owner_profile().select_tab("My Pets").open_add_pet()
    profile_page.fill_pet(name="Nosex", species="Dog").submit_pet()

    assert profile_page.validity(ProfilePage.PET_SEX, "valueMissing")
    assert not profile_page.validity(ProfilePage.PET_NAME, "valueMissing")
    assert profile_page.request_count(pets_url(account_ids), "POST") == 0


def test_pet_type_is_sent_automatically(profile_page, sign_in_as, registered_account):
    account = registered_account()[0]
    sign_in_as(account)
    profile_page.open_from_nav().select_tab("My Pets").open_add_pet()
    profile_page.fill_pet(name="Typed", sex="FEMALE", species="Rabbit").submit_pet()
    profile_page.wait_for_pet_names(["Typed"])

    assert profile_page.pet_cards()[0]["details"]["Type:"] == "PET"


def test_pet_species_is_required(owner_profile, profile_page, account_ids):
    owner_profile().select_tab("My Pets").open_add_pet()
    profile_page.fill_pet(name="Nospecies", sex="MALE").submit_pet()

    assert profile_page.validity(ProfilePage.PET_SPECIES, "valueMissing")
    assert profile_page.request_count(pets_url(account_ids), "POST") == 0


def test_valid_pet_photo_shows_preview(owner_profile, profile_page, photo_file):
    owner_profile().select_tab("My Pets").open_add_pet()
    profile_page.choose_pet_photo(photo_file("pet.png"))
    profile_page.wait.until(lambda d: profile_page.has_pet_preview())

    assert profile_page.pet_preview_src().startswith("blob:")
    assert profile_page.pet_form_error() == ""


def test_wrong_photo_type_is_rejected(owner_profile, profile_page, photo_file):
    owner_profile().select_tab("My Pets").open_add_pet()
    profile_page.choose_pet_photo(photo_file("notes.txt"))

    assert profile_page.pet_form_error() == WRONG_TYPE_ERROR
    assert not profile_page.has_pet_preview()
    assert profile_page.pet_photo_value() == ""


def test_photo_over_five_megabytes_is_rejected(owner_profile, profile_page, photo_file):
    owner_profile().select_tab("My Pets").open_add_pet()
    profile_page.choose_pet_photo(photo_file("large.png", FIVE_MB + 1))

    assert profile_page.pet_form_error() == TOO_LARGE_ERROR
    assert not profile_page.has_pet_preview()
    assert profile_page.pet_photo_value() == ""


def test_photo_of_exactly_five_megabytes_is_accepted(
    owner_profile, profile_page, photo_file
):
    owner_profile().select_tab("My Pets").open_add_pet()
    profile_page.choose_pet_photo(photo_file("exact.png", FIVE_MB))
    profile_page.wait.until(lambda d: profile_page.has_pet_preview())

    assert profile_page.pet_form_error() == ""


def test_selected_photo_can_be_cleared(owner_profile, profile_page, photo_file):
    owner_profile().select_tab("My Pets").open_add_pet()
    profile_page.choose_pet_photo(photo_file("pet.png"))
    profile_page.wait.until(lambda d: profile_page.has_pet_preview())
    profile_page.remove_pet_photo()

    assert profile_page.pet_photo_value() == ""
    assert profile_page.pet_form_error() == ""


def test_added_pet_appears_in_list(profile_page, sign_in_as, registered_account):
    account = registered_account()[0]
    sign_in_as(account)
    profile_page.open_from_nav().select_tab("My Pets").open_add_pet()
    profile_page.fill_pet(
        name="Biscuit", sex="MALE", species="Dog", breed="Pug", location="Skopje"
    )
    profile_page.set_pet_birth_date("2023-02-01").submit_pet()
    profile_page.wait_for_pet_names(["Biscuit"])

    assert not profile_page.has_add_pet_panel()
    assert profile_page.active_tab() == "My Pets"
    assert profile_page.pet_cards()[0]["details"] == {
        "Species:": "Dog",
        "Type:": "PET",
        "Breed:": "Pug",
        "Sex:": "MALE",
        "DOB:": "Feb 1, 2023",
        "Location:": "Skopje",
    }


def test_first_pet_unlocks_create_listing_tab(
    client_profile, profile_page, account_ids
):
    client_profile(
        routes=[
            route(pets_url(account_ids, "client"), [], method="GET", times=1),
            route(pets_url(account_ids, "client"), REX, 201, method="POST"),
        ],
        pets=[REX],
    ).select_tab("My Pets")

    assert profile_page.tab_labels() == CLIENT_TABS

    profile_page.open_add_pet()
    profile_page.fill_pet(name="Rex", sex="FEMALE", species="Dog").submit_pet()
    profile_page.wait_for_pet_names(["Rex"])

    assert profile_page.tab_labels() == CLIENT_TABS + ["Create Listing"]
    assert profile_page.active_tab() == "My Pets"


def test_client_is_promoted_to_owner_after_first_pet(
    profile_page, driver, base_url, sign_in_as, registered_account
):
    account = registered_account()[0]
    sign_in_as(account)
    profile_page.open_from_nav()

    assert profile_page.header()["type"] == "CLIENT"

    profile_page.select_tab("My Pets").open_add_pet()
    profile_page.fill_pet(name="Promo", sex="MALE", species="Cat").submit_pet()
    profile_page.wait_for_pet_names(["Promo"])
    TopNav(driver, base_url).logout().wait_for_path("/")
    sign_in_as(account)
    profile_page.open_from_nav()

    assert profile_page.header()["type"] == "OWNER"
    assert profile_page.tab_labels() == OWNER_TABS


def test_pet_is_preselected_from_pets_tab(owner_profile, profile_page):
    owner_profile().select_tab("My Pets").pet_card_button("Create Listing for Milo")
    profile_page.wait_for_active_tab("Create Listing")

    assert profile_page.listing_form_values()["pet"] == "94102"


def test_create_listing_requires_pet(owner_profile, profile_page):
    owner_profile().select_tab("Create Listing")
    profile_page.fill_listing(description="No pet chosen.", price="100")
    profile_page.submit_listing()

    assert profile_page.validity(ProfilePage.LISTING_PET, "valueMissing")
    assert profile_page.request_count("/api/listings", "POST") == 0


def test_create_listing_requires_description_and_price(owner_profile, profile_page):
    owner_profile().select_tab("Create Listing")
    profile_page.fill_listing(pet_id=94101).submit_listing()

    assert profile_page.validity(ProfilePage.LISTING_DESCRIPTION, "valueMissing")
    assert profile_page.validity(ProfilePage.LISTING_PRICE, "valueMissing")

    profile_page.fill_listing(description="Price missing.").submit_listing()

    assert profile_page.validity(ProfilePage.LISTING_PRICE, "valueMissing")
    assert profile_page.request_count("/api/listings", "POST") == 0


def test_create_listing_with_integer_price(owner_profile, profile_page):
    owner_profile(routes=[route("/api/listings", LISTING, 201, method="POST")])
    profile_page.select_tab("Create Listing")
    profile_page.fill_listing(pet_id=94101, description="Whole price.", price="150")
    profile_page.submit_listing().wait_for_active_tab("My Listings")

    assert profile_page.request_bodies("/api/listings", "POST") == [
        {"animalId": 94101, "description": "Whole price.", "price": 150}
    ]


def test_create_listing_with_decimal_price(owner_profile, profile_page):
    owner_profile(routes=[route("/api/listings", LISTING, 201, method="POST")])
    profile_page.select_tab("Create Listing")
    profile_page.fill_listing(pet_id=94102, description="Cents price.", price="99.99")
    profile_page.submit_listing().wait_for_active_tab("My Listings")

    assert profile_page.request_bodies("/api/listings", "POST") == [
        {"animalId": 94102, "description": "Cents price.", "price": 99.99}
    ]


def test_create_listing_rejects_zero_or_negative_price(owner_profile, profile_page):
    owner_profile(routes=[route("/api/listings", LISTING, 201, method="POST")])
    profile_page.select_tab("Create Listing")
    profile_page.fill_listing(pet_id=94101, description="Free pet.", price="0")
    profile_page.submit_listing().wait_for_listing_form_error(REQUIRED_FIELDS_ERROR)

    profile_page.fill_listing(description="Negative pet.", price="-5").submit_listing()

    assert profile_page.validity(ProfilePage.LISTING_PRICE, "rangeUnderflow")
    assert profile_page.request_count("/api/listings", "POST") == 0
    assert profile_page.active_tab() == "Create Listing"


def test_create_listing_success_resets_form(owner_profile, profile_page):
    owner_profile(routes=[route("/api/listings", LISTING, 201, method="POST")])
    profile_page.select_tab("Create Listing")
    profile_page.fill_listing(pet_id=94101, description="Reset me.", price="120")
    profile_page.submit_listing().wait_for_active_tab("My Listings")
    profile_page.select_tab("Create Listing")

    assert profile_page.listing_form_values() == {
        "pet": "",
        "description": "",
        "price": "",
    }
    assert profile_page.listing_form_error() == ""


def test_create_listing_success_shows_it_in_my_listings(owner_profile, profile_page):
    owner_profile(
        routes=[
            route(MY_LISTINGS_URL, [], method="GET", times=1),
            route("/api/listings", LISTING, 201, method="POST"),
        ],
        listings=[LISTING],
    )

    assert profile_page.listing_cards() == []

    profile_page.select_tab("Create Listing")
    profile_page.fill_listing(
        pet_id=94101, description=LISTING["description"], price="120"
    )
    profile_page.submit_listing().wait_for_active_tab("My Listings")
    profile_page.wait_for_listing_count(1)

    assert profile_page.listing_cards()[0]["pet"] == "Rex"


def test_account_without_pets_cannot_create_listing(client_profile, profile_page):
    client_profile(pets=[])

    assert "Create Listing" not in profile_page.tab_labels()

    profile_page.click_link("Create your first listing")

    assert profile_page.section_titles() == ["Create New Listing"]
    assert profile_page.empty_texts() == [NEED_PET_TEXT]
    assert not profile_page.has_listing_form()


def test_favorites_empty_state(profile_page, sign_in, favorite_api):
    sign_in("favorites")
    profile_page.open_from_nav().select_tab("Favorites")

    assert profile_page.favorite_cards() == []
    assert profile_page.empty_texts() == [
        NO_FAVORITES_TEXT,
        "Browse listings and click the heart icon to save them!",
    ]


def test_favorites_are_listed(profile_page, sign_in, favorite_api, listing_ids):
    favorite_api.add(listing_ids["UiBeagle"])
    sign_in("favorites")
    profile_page.open_from_nav().select_tab("Favorites")

    assert profile_page.favorite_cards() == [
        {
            "pet": "UiBeagle",
            "status": "ACTIVE",
            "description": "UI test beagle from Ohrid.",
            "price": "$120.00",
        }
    ]


def test_favorite_can_be_removed(profile_page, sign_in, favorite_api, listing_ids):
    favorite_api.add(listing_ids["UiBeagle"])
    favorite_api.add(listing_ids["UiCorgi"])
    sign_in("favorites")
    profile_page.open_from_nav().select_tab("Favorites")
    profile_page.remove_favorite("UiBeagle").wait_for_favorite_pets(["UiCorgi"])

    assert favorite_api.wait_for({listing_ids["UiCorgi"]}) == {listing_ids["UiCorgi"]}


def test_favorite_opens_listing_details(
    profile_page, sign_in, favorite_api, listing_ids
):
    favorite_api.add(listing_ids["UiCorgi"])
    sign_in("favorites")
    profile_page.open_from_nav().select_tab("Favorites")
    profile_page.open_favorite("UiCorgi")

    profile_page.wait_for_path("/listing/%s" % listing_ids["UiCorgi"])


def test_favorite_with_broken_image_uses_placeholder(client_profile, profile_page):
    client_profile(
        routes=[
            route("/api/pets/94101", dict(REX, photoUrl=BROKEN_PHOTO_URL), method="GET")
        ],
        favorites=[LISTING],
    ).select_tab("Favorites")
    profile_page.wait_for_favorite_image("Rex", PET_PLACEHOLDER)

    assert BROKEN_PHOTO_URL not in profile_page.favorite_image_src("Rex")
    assert profile_page.request_count(FAVORITES_URL, "GET") == 1


def test_user_profile_route_renders_own_profile(
    profile_page, sign_in, account_ids
):
    sign_in("client")
    profile_page.navigate("/profile/%s" % account_ids("owner")).wait_until_loaded()

    assert profile_page.header()["name"] == "Uma Client"
    assert profile_page.header()["username"] == "@ui.client"


def test_user_profile_route_does_not_load_other_user_data(
    profile_page, sign_in, account_ids
):
    owner_id = account_ids("owner")
    client_id = account_ids("client")
    sign_in("client")
    profile_page.install_routes([])
    profile_page.navigate("/profile/%s" % owner_id).wait_until_loaded()

    assert profile_page.request_count("/api/users/%s/pets" % client_id) == 1
    assert not any(
        "/api/users/%s" % owner_id in request for request in profile_page.requests()
    )
    assert profile_page.header()["email"] == "ui.client@petify.test"
