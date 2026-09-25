from urllib.parse import parse_qs, urlsplit

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .admin_clinics_page import ROUTES_STUB
from .listings_page import HIDE_DEV_OVERLAY, IN_VIEWPORT

LISTINGS_URL = "/api/users/admin/listings"
USERS_URL = "/api/users/admin/all"
PETS_URL = "/api/pets/"


def route(match, body=None, status=200, method=None):
    return {"match": match, "status": status, "body": body, "method": method}


def stub_listing(listing_id, **overrides):
    listing = {
        "listingId": listing_id,
        "ownerId": 92001,
        "animalId": 92101,
        "description": "Stubbed admin listing.",
        "price": 100.0,
        "status": "ACTIVE",
        "createdAt": "2026-03-05T10:00:00",
    }
    listing.update(overrides)
    return listing


def stub_page(items, **overrides):
    page = {
        "items": items,
        "page": 0,
        "size": 500,
        "totalItems": len(items),
        "totalPages": 1 if items else 0,
        "hasNext": False,
        "hasPrevious": False,
        "activeListings": len([item for item in items if item["status"] == "ACTIVE"]),
        "soldListings": len([item for item in items if item["status"] == "SOLD"]),
    }
    page.update(overrides)
    return page


def stub_owner(user_id, first_name, last_name, **overrides):
    owner = {
        "userId": user_id,
        "username": "%s.%s" % (first_name.lower(), last_name.lower()),
        "email": "%s.%s@petify.test" % (first_name.lower(), last_name.lower()),
        "firstName": first_name,
        "lastName": last_name,
        "userType": "OWNER",
        "isBlocked": False,
    }
    owner.update(overrides)
    return owner


def stub_pet(animal_id, name):
    return {
        "animalId": animal_id,
        "name": name,
        "sex": "FEMALE",
        "type": "Dog",
        "species": "Dog",
        "breed": "Beagle",
    }


class AdminListingsPage:
    MAIN = (By.CSS_SELECTOR, "main.admin-listings")
    PAGE_TITLE = (By.CSS_SELECTOR, ".page-title")
    PANEL_TITLE = (By.CSS_SELECTOR, ".panel-header h2")
    SUMMARY = (By.CSS_SELECTOR, ".panel-subtitle")
    ALERT = (By.CSS_SELECTOR, ".listings-body .alert-danger")
    LOADING = (By.CSS_SELECTOR, ".listings-body .alert-info")
    NAV_LINK = (By.CSS_SELECTOR, "a[href='/admin/listings']")
    SEARCH = (By.ID, "listingSearch")
    STATUS = (By.ID, "listingStatus")
    MIN_PRICE = (By.ID, "minPrice")
    MAX_PRICE = (By.ID, "maxPrice")
    CLEAR = (By.CSS_SELECTOR, ".clear-filters")
    FILTER_BAR = (By.CSS_SELECTOR, ".filter-bar")
    FILTER_SUMMARY = (By.CSS_SELECTOR, ".filter-summary")
    EMPTY_STATE = (By.CSS_SELECTOR, ".panel .empty-state")
    CARD = (By.CSS_SELECTOR, ".listing-card")
    PAGINATION = (By.CSS_SELECTOR, ".pagination-bar")
    PAGE_META = (By.CSS_SELECTOR, ".pagination-bar .page-meta")

    def __init__(self, driver, base_url, timeout=20):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(
            driver, timeout, ignored_exceptions=(StaleElementReferenceException,)
        )

    def open(self):
        self.driver.get(self.base_url + "/admin/listings")
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        return self

    def open_from_nav(self):
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        self._click(self.driver.find_element(*self.NAV_LINK))
        return self

    def install_routes(self, routes):
        self.driver.execute_script(ROUTES_STUB, list(routes))
        return self

    def requests(self):
        return self.driver.execute_script("return window.__uiTestRequests || [];")

    def listing_queries(self):
        queries = []
        for request in self.requests():
            method, url = request.split(" ", 1)
            if method == "GET" and LISTINGS_URL in url:
                query = parse_qs(urlsplit(url).query)
                queries.append({key: values[0] for key, values in query.items()})
        return queries

    def last_listing_query(self):
        return self.listing_queries()[-1]

    def wait_for_listing_query_count(self, expected):
        self.wait.until(lambda d: len(self.listing_queries()) == expected)
        return self

    def wait_until_loaded(self):
        self.wait.until(EC.presence_of_element_located(self.MAIN))
        self.wait.until(
            lambda d: not d.find_elements(*self.LOADING)
            and (
                d.find_elements(*self.CARD)
                or d.find_elements(*self.EMPTY_STATE)
                or d.find_elements(*self.ALERT)
            )
        )
        return self

    def wait_for_login_redirect(self):
        target = self.base_url + "/login"
        self.wait.until(lambda d: d.current_url.rstrip("/") == target)
        return self

    def wait_for_listings_redirect(self):
        target = self.base_url.rstrip("/")
        self.wait.until(lambda d: d.current_url.rstrip("/") == target)
        return self

    def has_page(self):
        return len(self.driver.find_elements(*self.MAIN)) > 0

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

    def page_title(self):
        return self._text(self.PAGE_TITLE)

    def panel_title(self):
        return self._text(self.PANEL_TITLE)

    def summary(self):
        return self._text(self.SUMMARY)

    def errors(self):
        return [
            element.text.strip() for element in self.driver.find_elements(*self.ALERT)
        ]

    def wait_for_error(self, expected):
        self.wait.until(lambda d: expected in self.errors())
        return self

    def empty_text(self):
        return self._text(self.EMPTY_STATE)

    def has_filters(self):
        return len(self.driver.find_elements(*self.FILTER_BAR)) > 0

    def has_pagination(self):
        return len(self.driver.find_elements(*self.PAGINATION)) > 0

    def filter_summary(self):
        return self._text(self.FILTER_SUMMARY)

    def cards(self):
        rows = []
        for card in self.driver.find_elements(*self.CARD):
            rows.append(
                {
                    "pet": self._text((By.CSS_SELECTOR, ".listing-title"), card),
                    "owner": self._text((By.CSS_SELECTOR, ".listing-owner"), card),
                    "status": self._text((By.CSS_SELECTOR, ".badge"), card),
                    "description": self._text(
                        (By.CSS_SELECTOR, ".listing-description"), card
                    ),
                    "price": self._text((By.CSS_SELECTOR, ".listing-price"), card),
                    "date": self._text((By.CSS_SELECTOR, ".listing-date"), card),
                }
            )
        return rows

    def pet_names(self):
        return [row["pet"] for row in self.cards()]

    def wait_for_pet_names(self, expected):
        self.wait.until(
            lambda d: not d.find_elements(*self.LOADING)
            and self.pet_names() == expected
        )
        return self

    def card_link(self, pet_name):
        locator = (
            By.XPATH,
            "//a[contains(@class,'listing-title')][normalize-space()='%s']" % pet_name,
        )
        href = self.driver.find_element(*locator).get_attribute("href")
        return href.replace(self.base_url, "")

    def status_badge_class(self, pet_name):
        locator = (
            By.XPATH,
            "//article[contains(@class,'listing-card')]"
            "[.//*[contains(@class,'listing-title')][normalize-space()='%s']]"
            "//span[contains(@class,'badge')]" % pet_name,
        )
        classes = self.driver.find_element(*locator).get_attribute("class").split()
        return next(name for name in classes if name.startswith("bg-"))

    def search(self, text):
        field = self.driver.find_element(*self.SEARCH)
        field.clear()
        field.send_keys(text)
        return self

    def select_status(self, value):
        Select(self.driver.find_element(*self.STATUS)).select_by_value(value)
        return self

    def status_options(self):
        return [
            option.get_attribute("value")
            for option in Select(self.driver.find_element(*self.STATUS)).options
        ]

    def _set_price(self, locator, value):
        field = self.driver.find_element(*locator)
        field.clear()
        field.send_keys(value)
        field.send_keys(Keys.TAB)
        return self

    def set_min_price(self, value):
        return self._set_price(self.MIN_PRICE, value)

    def set_max_price(self, value):
        return self._set_price(self.MAX_PRICE, value)

    def filter_values(self):
        return {
            "search": self.driver.find_element(*self.SEARCH).get_attribute("value"),
            "status": self.driver.find_element(*self.STATUS).get_attribute("value"),
            "minPrice": self.driver.find_element(*self.MIN_PRICE).get_attribute("value"),
            "maxPrice": self.driver.find_element(*self.MAX_PRICE).get_attribute("value"),
        }

    def clear_filters(self):
        self._click(self.driver.find_element(*self.CLEAR))
        return self

    def page_meta(self):
        return [
            element.text.strip()
            for element in self.driver.find_elements(*self.PAGE_META)
        ]

    def wait_for_page_meta(self, expected):
        self.wait.until(lambda d: self.page_meta() and self.page_meta()[0] == expected)
        return self

    def _pagination_button(self, label):
        locator = (
            By.XPATH,
            "(//div[contains(@class,'pagination-bar')])[1]"
            "//button[normalize-space()='%s']" % label,
        )
        return self.driver.find_element(*locator)

    def is_previous_enabled(self):
        return self._pagination_button("Previous").is_enabled()

    def is_next_enabled(self):
        return self._pagination_button("Next").is_enabled()

    def go_next(self):
        self._click(self._pagination_button("Next"))
        return self

    def go_previous(self):
        self._click(self._pagination_button("Previous"))
        return self
