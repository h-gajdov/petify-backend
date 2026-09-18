import pytest

from pages.listings_page import ListingsPage, stub_row
from pages.login_page import LoginPage

BEAGLE = "UiBeagle"
CORGI = "UiCorgi"
SIAMESE = "UiSiamese"
CANARY = "UiCanary"

FAVORITE_LOGIN_ALERT = "Please log in to save favorites"
FAVORITE_FAILURE_ALERT = "Failed to update favorite. Please try again."
NO_EMAIL_ALERT = "This owner does not have a contact email available."
API_ERROR_BANNER = "Couldn't load from API."


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


def test_pet_type_all_shows_every_species(listings_page):
    listings_page.open()

    assert listings_page.active_pet_type() == "All pets"
    assert listings_page.has_card(BEAGLE)
    assert listings_page.has_card(SIAMESE)
    assert listings_page.has_card(CANARY)


def test_pet_type_dogs_shows_only_dogs(listings_page):
    listings_page.open().select_pet_type("Dogs")

    assert listings_page.active_pet_type() == "Dogs"
    assert listings_page.has_card(BEAGLE)
    assert listings_page.has_card(CORGI)
    assert not listings_page.has_card(SIAMESE)
    assert not listings_page.has_card(CANARY)
    assert set(listings_page.species_shown()) == {"Dog"}


def test_pet_type_cats_shows_only_cats(listings_page):
    listings_page.open().select_pet_type("Cats")

    assert listings_page.has_card(SIAMESE)
    assert not listings_page.has_card(BEAGLE)
    assert not listings_page.has_card(CANARY)
    assert set(listings_page.species_shown()) == {"Cat"}


def test_pet_type_other_excludes_dogs_and_cats(listings_page):
    listings_page.open().select_pet_type("Other")

    assert listings_page.has_card(CANARY)
    assert not listings_page.has_card(BEAGLE)
    assert not listings_page.has_card(SIAMESE)
    assert not {"Dog", "Cat"} & set(listings_page.species_shown())


def test_pet_type_without_matches_shows_empty_state(listings_page):
    listings_page.open()
    listings_page.stub_listings([stub_row(animal_name="StubDog", species="Dog")])
    listings_page.reload()

    assert listings_page.has_card("StubDog")

    listings_page.select_pet_type("Cats")

    assert listings_page.is_empty()
    assert listings_page.titles() == []


def test_breed_options_are_scoped_to_pet_type(listings_page):
    listings_page.open().select_pet_type("Dogs")
    dog_breeds = listings_page.breed_options()

    assert "Beagle" in dog_breeds
    assert "Corgi" in dog_breeds
    assert "Siamese" not in dog_breeds
    assert "Canary" not in dog_breeds

    listings_page.select_pet_type("Cats")
    cat_breeds = listings_page.breed_options()

    assert "Siamese" in cat_breeds
    assert "Beagle" not in cat_breeds


def test_breed_filter_narrows_results(listings_page):
    listings_page.open().select_pet_type("Dogs").select_breed("Beagle")

    assert listings_page.has_card(BEAGLE)
    assert not listings_page.has_card(CORGI)
    assert listings_page.titles() == [BEAGLE]


def test_breed_filter_reset_restores_results(listings_page):
    listings_page.open().select_pet_type("Dogs").select_breed("Beagle")
    assert not listings_page.has_card(CORGI)

    listings_page.select_breed("")

    assert listings_page.selected_breed() == ""
    assert listings_page.has_card(BEAGLE)
    assert listings_page.has_card(CORGI)


def test_breed_filter_clears_when_pet_type_changes(listings_page):
    listings_page.open().select_pet_type("Dogs").select_breed("Beagle")
    assert listings_page.selected_breed() == "Beagle"

    listings_page.select_pet_type("Cats")

    assert listings_page.selected_breed() == ""
    assert listings_page.has_card(SIAMESE)


def test_city_filter_selects_one_city(listings_page):
    listings_page.open().select_city("struga")

    assert listings_page.has_card(CANARY)
    assert not listings_page.has_card(BEAGLE)
    assert not listings_page.has_card(CORGI)
    assert set(listings_page.cities_shown()) == {"Struga"}


def test_city_filter_matches_case_insensitively(listings_page):
    listings_page.open()

    assert "ohrid" in listings_page.city_options()
    assert "OHRID" not in listings_page.city_options()

    listings_page.select_city("ohrid")

    assert listings_page.has_card(BEAGLE)
    assert listings_page.has_card(SIAMESE)
    assert set(listings_page.cities_shown()) == {"Ohrid", "OHRID"}


def test_city_filter_combined_with_type_and_breed(listings_page):
    listings_page.open().select_pet_type("Dogs").select_breed("Beagle")
    listings_page.select_city("ohrid")

    assert listings_page.titles() == [BEAGLE]

    listings_page.select_city("bitola")

    assert listings_page.is_empty()


def test_recommended_toggle_hidden_for_guest(listings_page):
    listings_page.open()

    assert listings_page.view_modes() == ["All Listings"]
    assert listings_page.listings_title() == "Browse all listings"


def test_recommended_toggle_shows_recommendations(listings_page, sign_in):
    sign_in("recommended")
    listings_page.open()

    assert listings_page.view_modes() == ["All Listings", "Recommended"]

    listings_page.select_view_mode("Recommended")

    assert listings_page.active_view_mode() == "Recommended"
    assert listings_page.listings_title() == "Your recommended listings"
    assert CORGI in listings_page.pet_names()
    assert BEAGLE not in listings_page.pet_names()
    assert CANARY not in listings_page.pet_names()


def test_recommended_toggle_without_recommendations_is_empty(listings_page, sign_in):
    sign_in("unrecommended")
    listings_page.open()
    listings_page.select_view_mode("Recommended")

    assert listings_page.is_empty()
    assert listings_page.titles() == []
    assert not listings_page.has_error()

    listings_page.select_view_mode("All Listings")

    assert listings_page.has_card(BEAGLE)


def test_recommended_toggle_api_error_shows_banner(listings_page, sign_in):
    sign_in("recommended")
    listings_page.open()
    listings_page.fail_endpoint("/api/listings/recommendations")
    listings_page.select_view_mode("Recommended")

    assert API_ERROR_BANNER in listings_page.error_message()
    assert CORGI not in listings_page.pet_names()


def test_guest_favorite_shows_login_alert(listings_page):
    listings_page.open().toggle_favorite(BEAGLE)

    assert listings_page.alert_text() == FAVORITE_LOGIN_ALERT

    listings_page.open()

    assert not listings_page.is_favorited(BEAGLE)


def test_favorite_from_card_is_saved(listings_page, sign_in, favorite_api, listing_ids):
    sign_in("favorites")
    listings_page.open()

    assert not listings_page.is_favorited(BEAGLE)

    listings_page.toggle_favorite(BEAGLE)
    listings_page.wait_until_favorited(BEAGLE, True)

    assert favorite_api.wait_for({listing_ids[BEAGLE]}) == {listing_ids[BEAGLE]}


def test_favorite_from_card_is_removed(
    listings_page, sign_in, favorite_api, listing_ids
):
    favorite_api.add(listing_ids[BEAGLE])
    sign_in("favorites")
    listings_page.open()

    assert listings_page.is_favorited(BEAGLE)

    listings_page.toggle_favorite(BEAGLE)
    listings_page.wait_until_favorited(BEAGLE, False)

    assert favorite_api.wait_for(set()) == set()


def test_favorite_survives_reload(listings_page, sign_in, favorite_api, listing_ids):
    sign_in("favorites")
    listings_page.open().toggle_favorite(BEAGLE)
    listings_page.wait_until_favorited(BEAGLE, True)

    listings_page.open()

    assert listings_page.is_favorited(BEAGLE)
    assert not listings_page.is_favorited(CORGI)
    assert favorite_api.wait_for({listing_ids[BEAGLE]}) == {listing_ids[BEAGLE]}


def test_favorite_api_failure_shows_alert(listings_page, sign_in, favorite_api):
    sign_in("favorites")
    listings_page.open()
    listings_page.fail_endpoint("/api/favorites/")
    listings_page.toggle_favorite(BEAGLE)

    assert listings_page.alert_text() == FAVORITE_FAILURE_ALERT
    assert favorite_api.ids() == set()


def test_owner_does_not_see_own_listings(listings_page, sign_in):
    sign_in("owner")
    listings_page.open()

    assert not listings_page.has_card(BEAGLE)
    assert not listings_page.has_card(CORGI)
    assert not listings_page.has_card(SIAMESE)
    assert not listings_page.has_card(CANARY)


def test_guest_sees_every_listing(listings_page):
    listings_page.open()

    assert listings_page.has_card(BEAGLE)
    assert listings_page.has_card(CORGI)
    assert listings_page.has_card(SIAMESE)
    assert listings_page.has_card(CANARY)


def test_card_click_opens_details(listings_page, listing_ids):
    listings_page.open().open_card(BEAGLE)

    listings_page.wait_for_details(listing_ids[BEAGLE])


def test_view_button_opens_details(listings_page, listing_ids):
    listings_page.open().click_view(CORGI)

    listings_page.wait_for_details(listing_ids[CORGI])


def test_contact_owner_without_email_shows_alert(listings_page):
    listings_page.open()
    listings_page.stub_listings(
        [stub_row(animal_name="StubNoEmail", owner_email=None, owner_name=None)]
    )
    listings_page.reload()
    listings_page.click_contact("StubNoEmail")

    assert listings_page.alert_text() == NO_EMAIL_ALERT
