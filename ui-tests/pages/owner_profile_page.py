import json

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .admin_clinics_page import ROUTES_STUB
from .listings_page import HIDE_DEV_OVERLAY, IN_VIEWPORT, ListingsPage
from .profile_page import ANIMATIONS_DONE

ROUTER_PUSH = """
document.querySelector('#app').__vue_app__.config.globalProperties.$router.push(arguments[0]);
"""

MY_LISTINGS_URL = "/api/listings/my-listings"
REVIEWS_URL = "/api/reviews/"


def route(match, body=None, status=200, method=None):
    return {"match": match, "status": status, "body": body, "method": method}


def stub_owner(owner_id, first_name="Stub", last_name="Owner", **overrides):
    owner = {
        "userId": owner_id,
        "username": "%s.%s" % (first_name.lower(), last_name.lower()),
        "email": "%s.%s@petify.test" % (first_name.lower(), last_name.lower()),
        "firstName": first_name,
        "lastName": last_name,
    }
    owner.update(overrides)
    return owner


def stub_owner_listing(listing_id, animal_id, **overrides):
    listing = {
        "listingId": listing_id,
        "ownerId": 93001,
        "animalId": animal_id,
        "description": "Stubbed owner listing.",
        "price": 95.5,
        "status": "ACTIVE",
        "createdAt": "2026-04-02T12:00:00",
    }
    listing.update(overrides)
    return listing


def stub_owner_pet(animal_id, name, **overrides):
    pet = {
        "animalId": animal_id,
        "name": name,
        "sex": "MALE",
        "dateOfBirth": "2022-05-06",
        "photoUrl": None,
        "type": "Dog",
        "species": "Dog",
        "breed": "Corgi",
        "locatedName": "Skopje",
    }
    pet.update(overrides)
    return pet


def stub_owner_review(review_id, **overrides):
    review = {
        "reviewId": review_id,
        "reviewerId": 93901,
        "reviewerName": "Stub Reviewer",
        "reviewerUsername": "stub.reviewer",
        "rating": 4,
        "comment": "Great experience.",
        "createdAt": "2026-04-10T08:30:00",
    }
    review.update(overrides)
    return review


def owner_routes(owner, listings=(), pets=(), reviews=(), verified=False):
    owner_id = owner["userId"]
    return [
        route("/api/users/%s/pets" % owner_id, list(pets), method="GET"),
        route(
            "/api/users/%s/verified" % owner_id,
            {"userId": owner_id, "verified": verified},
            method="GET",
        ),
        route("/api/users/%s" % owner_id, owner, method="GET"),
        route(MY_LISTINGS_URL, list(listings), method="GET"),
        route(REVIEWS_URL + str(owner_id), list(reviews), method="GET"),
    ]


class OwnerProfilePage:
    LOADING = (By.XPATH, "//p[normalize-space()='Loading owner profile…']")
    ERROR = (By.CSS_SELECTOR, ".alert.alert-danger[role='alert']")
    ERROR_TITLE = (By.CSS_SELECTOR, ".alert.alert-danger[role='alert'] .fw-semibold")
    ERROR_DETAIL = (By.CSS_SELECTOR, ".alert.alert-danger[role='alert'] .small")
    RETRY = (By.CSS_SELECTOR, ".alert.alert-danger[role='alert'] button")
    NAME = (By.CSS_SELECTOR, ".profile-name")
    USERNAME = (By.CSS_SELECTOR, ".profile-username")
    EMAIL = (By.CSS_SELECTOR, ".profile-email a")
    VERIFIED = (By.CSS_SELECTOR, ".verified-badge")
    CONTACT = (By.CSS_SELECTOR, ".profile-badge button")
    TAB = (By.CSS_SELECTOR, ".nav-tabs .nav-link")
    ACTIVE_TAB = (By.CSS_SELECTOR, ".nav-tabs .nav-link.active")
    SECTION_TITLE = (By.CSS_SELECTOR, ".tab-content-section > h2.section-title")
    EMPTY_STATE = (By.CSS_SELECTOR, ".tab-content-section > .empty-state")
    LISTING_CARD = (By.CSS_SELECTOR, ".listing-card")
    PET_CARD = (By.CSS_SELECTOR, ".pet-card")
    REVIEW_FORM = (By.CSS_SELECTOR, ".form-card form")
    STAR = (By.CSS_SELECTOR, ".form-card .star-btn")
    COMMENT = (By.ID, "comment")
    SUBMIT = (By.CSS_SELECTOR, ".form-card button[type='submit']")
    REVIEW_ERROR = (By.CSS_SELECTOR, ".form-card .alert-danger")
    REVIEW_CARD = (By.CSS_SELECTOR, ".review-card")

    def __init__(self, driver, base_url, timeout=20):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(
            driver, timeout, ignored_exceptions=(StaleElementReferenceException,)
        )
        self.listings = ListingsPage(driver, base_url, timeout)

    def open(self, owner_id):
        self.driver.get("%s/owner/%s" % (self.base_url, owner_id))
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        return self

    def open_home(self):
        self.driver.get(self.base_url + "/")
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        return self

    def navigate(self, owner_id):
        self.driver.execute_script(ROUTER_PUSH, "/owner/%s" % owner_id)
        return self

    def open_stubbed(self, owner, **data):
        self.open_home().install_routes(owner_routes(owner, **data))
        return self.navigate(owner["userId"]).wait_until_loaded()

    def install_routes(self, routes):
        self.driver.execute_script(ROUTES_STUB, list(routes))
        return self

    def request_bodies(self, match):
        rows = self.driver.execute_script("return window.__uiTestBodies || [];")
        return [
            json.loads(row["body"])
            for row in rows
            if match in row["url"] and row["body"]
        ]

    def wait_until_loaded(self):
        self.wait.until(
            lambda d: not d.find_elements(*self.LOADING)
            and (d.find_elements(*self.NAME) or d.find_elements(*self.ERROR))
        )
        return self.wait_for_animations()

    def wait_for_error(self):
        self.wait.until(EC.visibility_of_element_located(self.ERROR))
        return self

    def wait_for_path(self, path):
        target = (self.base_url + path).rstrip("/")
        self.wait.until(lambda d: d.current_url.rstrip("/") == target)
        return self

    def _click(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )
        self.wait.until(lambda d: d.execute_script(IN_VIEWPORT, element))
        element.click()
        return self

    def _text(self, locator, context=None):
        source = context if context is not None else self.driver
        elements = source.find_elements(*locator)
        return elements[0].text.strip() if elements else ""

    def error_title(self):
        return self._text(self.ERROR_TITLE)

    def error_detail(self):
        return self._text(self.ERROR_DETAIL)

    def retry(self):
        self._click(self.driver.find_element(*self.RETRY))
        return self.wait_until_loaded()

    def name(self):
        return self._text(self.NAME)

    def wait_for_name(self, expected):
        self.wait.until(lambda d: self.name() == expected)
        return self

    def username(self):
        return self._text(self.USERNAME)

    def email(self):
        return self._text(self.EMAIL)

    def has_verified_badge(self):
        return len(self.driver.find_elements(*self.VERIFIED)) > 0

    def verified_text(self):
        return self._text(self.VERIFIED)

    def wait_for_verified_badge(self):
        self.wait.until(EC.presence_of_element_located(self.VERIFIED))
        return self

    def tab_labels(self):
        return [
            " ".join(element.text.split())
            for element in self.driver.find_elements(*self.TAB)
        ]

    def active_tab(self):
        return " ".join(self._text(self.ACTIVE_TAB).split())

    def select_tab(self, prefix):
        tab = next(
            element
            for element in self.driver.find_elements(*self.TAB)
            if element.text.strip().startswith(prefix)
        )
        self._click(tab)
        self.wait.until(lambda d: self.active_tab().startswith(prefix))
        return self.wait_for_animations()

    def wait_for_animations(self):
        self.wait.until(lambda d: d.execute_script(ANIMATIONS_DONE))
        return self

    def section_title(self):
        return self._text(self.SECTION_TITLE)

    def empty_text(self):
        return self._text(self.EMPTY_STATE)

    def listing_cards(self):
        rows = []
        for card in self.driver.find_elements(*self.LISTING_CARD):
            rows.append(
                {
                    "status": self._text((By.CSS_SELECTOR, ".listing-status"), card),
                    "pet": self._text((By.CSS_SELECTOR, ".listing-title"), card),
                    "description": self._text(
                        (By.CSS_SELECTOR, ".listing-description"), card
                    ),
                    "price": self._text((By.CSS_SELECTOR, ".listing-price"), card),
                    "date": self._text((By.CSS_SELECTOR, ".listing-date"), card),
                }
            )
        return rows

    def listing_pets(self):
        return [row["pet"] for row in self.listing_cards()]

    def open_listing(self, pet_name):
        locator = (
            By.XPATH,
            "//div[contains(@class,'listing-card')]"
            "[h3[normalize-space()='%s']]" % pet_name,
        )
        self._click(self.driver.find_element(*locator))
        return self

    def pet_cards(self):
        rows = []
        for card in self.driver.find_elements(*self.PET_CARD):
            details = {}
            for row in card.find_elements(By.CSS_SELECTOR, ".pet-detail-row"):
                label = row.find_element(By.CSS_SELECTOR, ".label").text.strip()
                details[label] = row.find_element(By.CSS_SELECTOR, ".value").text.strip()
            rows.append(
                {
                    "name": self._text((By.CSS_SELECTOR, ".pet-name"), card),
                    "details": details,
                }
            )
        return rows

    def pet_names(self):
        return [row["name"] for row in self.pet_cards()]

    def _pet_card(self, name):
        locator = (
            By.XPATH,
            "//div[contains(@class,'pet-card')][.//h3[normalize-space()='%s']]" % name,
        )
        return self.driver.find_element(*locator)

    def pet_image_state(self, name):
        card = self._pet_card(name)
        photos = card.find_elements(By.CSS_SELECTOR, "img.pet-image")
        if photos:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", photos[0]
            )
            return "photo" if photos[0].is_displayed() else "hidden"
        if card.find_elements(By.CSS_SELECTOR, "img.pet-image-placeholder-img"):
            return "placeholder"
        return "none"

    def wait_for_pet_image_state(self, name, expected):
        self.wait.until(lambda d: self.pet_image_state(name) == expected)
        return self

    def has_review_form(self):
        return len(self.driver.find_elements(*self.REVIEW_FORM)) > 0

    def select_rating(self, rating):
        self._click(self.driver.find_elements(*self.STAR)[rating - 1])
        return self

    def selected_rating(self):
        stars = self.driver.find_elements(*self.STAR)
        active = [
            index + 1
            for index, star in enumerate(stars)
            if "active" in star.get_attribute("class").split()
        ]
        return active[0] if active else 0

    def type_comment(self, text):
        field = self.driver.find_element(*self.COMMENT)
        field.clear()
        field.send_keys(text)
        return self

    def comment_value(self):
        return self.driver.find_element(*self.COMMENT).get_attribute("value")

    def is_submit_enabled(self):
        return self.driver.find_element(*self.SUBMIT).is_enabled()

    def submit_review(self):
        self._click(self.driver.find_element(*self.SUBMIT))
        return self

    def review_error(self):
        return self._text(self.REVIEW_ERROR)

    def wait_for_review_error(self, expected):
        self.wait.until(lambda d: self.review_error() == expected)
        return self

    def reviews(self):
        rows = []
        for card in self.driver.find_elements(*self.REVIEW_CARD):
            rows.append(
                {
                    "reviewer": self._text((By.CSS_SELECTOR, ".reviewer-name"), card),
                    "username": self._text(
                        (By.CSS_SELECTOR, ".reviewer-username"), card
                    ),
                    "stars": len(card.find_elements(By.CSS_SELECTOR, ".review-star")),
                    "comment": self._text((By.CSS_SELECTOR, ".review-comment"), card),
                    "date": self._text((By.CSS_SELECTOR, ".review-date"), card),
                    "deletable": len(card.find_elements(By.CSS_SELECTOR, ".delete-btn"))
                    > 0,
                }
            )
        return rows

    def reviewer_usernames(self):
        return [row["username"] for row in self.reviews()]

    def wait_for_reviewer_usernames(self, expected):
        self.wait.until(lambda d: self.reviewer_usernames() == expected)
        return self

    def delete_review(self, username):
        locator = (
            By.XPATH,
            "//div[contains(@class,'review-card')]"
            "[.//p[contains(@class,'reviewer-username')][normalize-space()='%s']]"
            "//button[contains(@class,'delete-btn')]" % username,
        )
        self._click(self.driver.find_element(*locator))
        return self

    def accept_dialog(self):
        self.wait.until(EC.alert_is_present()).accept()
        return self

    def dismiss_dialog(self):
        self.wait.until(EC.alert_is_present()).dismiss()
        return self

    def alert_text(self):
        alert = self.wait.until(EC.alert_is_present())
        text = alert.text
        alert.accept()
        return text

    def contact_owner(self):
        self._click(self.driver.find_element(*self.CONTACT))
        return self

    def record_navigations(self):
        self.listings.record_navigations()
        return self

    def recorded_mailto(self):
        return self.listings.recorded_mailto()
