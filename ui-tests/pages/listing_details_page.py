from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .listings_page import HIDE_DEV_OVERLAY, IN_VIEWPORT, ListingsPage

ROUTES_STUB = """
const routes = arguments[0];
const original = window.fetch;
window.fetch = function (input, init) {
  const url = typeof input === 'string' ? input : String(input.url);
  for (let index = 0; index < routes.length; index += 1) {
    const route = routes[index];
    if (url.indexOf(route.match) !== -1) {
      return Promise.resolve(
        new Response(route.body === null ? '' : JSON.stringify(route.body), {
          status: route.status,
          headers: { 'Content-Type': 'application/json' },
        })
      );
    }
  }
  return original.apply(this, arguments);
};
"""

CLIPBOARD_STUB = """
const succeeds = arguments[0];
window.__uiTestCopiedText = null;
Object.defineProperty(navigator, 'clipboard', {
  configurable: true,
  value: {
    writeText: function (text) {
      window.__uiTestCopiedText = text;
      return succeeds
        ? Promise.resolve()
        : Promise.reject(new Error('Clipboard unavailable'));
    },
  },
});
"""

ELEMENT_TOP = "return arguments[0].getBoundingClientRect().top;"


def route(match, body=None, status=200):
    return {"match": match, "status": status, "body": body}


class ListingDetailsPage:
    LOADING = (By.XPATH, "//p[normalize-space()='Loading listing details…']")
    ERROR = (By.CSS_SELECTOR, ".alert.alert-danger[role='alert']")
    ERROR_DETAIL = (By.CSS_SELECTOR, ".alert.alert-danger[role='alert'] .small")
    RETRY = (By.CSS_SELECTOR, ".alert.alert-danger[role='alert'] button")
    MAIN_IMAGE = (By.CSS_SELECTOR, ".main-image")
    TITLE = (By.CSS_SELECTOR, ".listing-title")
    KICKER = (By.CSS_SELECTOR, ".listing-kicker")
    POSTED = (By.CSS_SELECTOR, ".posted-date")
    PRICE = (By.CSS_SELECTOR, ".price-display")
    LOCATION_CARD = (By.CSS_SELECTOR, ".location-card")
    LOCATION_TEXT = (By.CSS_SELECTOR, ".location-card .location-text")
    FAVORITE = (By.CSS_SELECTOR, ".favorite-btn")
    SAVE = (By.CSS_SELECTOR, ".action-buttons .btn-secondary:last-child")
    CONTACT = (By.CSS_SELECTOR, ".action-buttons .btn-primary")
    SEE_OWNER = (
        By.XPATH,
        "//button[contains(@class,'btn-secondary')][.//span[normalize-space()='See Owner']]",
    )
    PET_LINK = (By.CSS_SELECTOR, ".pet-link")
    COPY = (By.CSS_SELECTOR, ".share-btn")
    HEALTH_CARD = (By.ID, "health-records")
    HEALTH_RECORD = (By.CSS_SELECTOR, "#health-records .health-record-item")
    HEALTH_EMPTY = (By.CSS_SELECTOR, "#health-records .muted-text")
    HEALTH_ERROR = (By.CSS_SELECTOR, "#health-records .alert-danger")
    RELATED_SECTION = (By.CSS_SELECTOR, ".related-listings-section")
    RELATED_CARD = (By.CSS_SELECTOR, ".related-listing-card")
    RELATED_TITLE = (By.CSS_SELECTOR, ".related-listing-title")

    def __init__(self, driver, base_url, timeout=20):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)
        self.listings = ListingsPage(driver, base_url, timeout)

    def open(self, listing_id):
        self.driver.get("%s/listing/%s" % (self.base_url, listing_id))
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        return self

    def open_stubbed(self, listing, related=(), routes=()):
        rows = [listing] + list(related)
        self.driver.get(self.base_url + "/")
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        self.listings.wait_until_loaded()
        self.install_routes(
            list(routes)
            + [
                route("/api/public/listings", rows),
                route("/api/listings/%s" % listing["listing_id"], listing),
            ]
        )
        self.listings.reload()
        names = sorted(row["animal_name"] for row in rows)
        self.wait.until(lambda d: sorted(self.listings.titles()) == names)
        self.listings.open_card(listing["animal_name"])
        return self.wait_until_loaded()

    def install_routes(self, routes):
        self.driver.execute_script(ROUTES_STUB, list(routes))
        return self

    def wait_until_loaded(self):
        self.wait.until(
            lambda d: not d.find_elements(*self.LOADING) and d.find_elements(*self.TITLE)
        )
        return self

    def wait_for_error(self):
        self.wait.until(EC.visibility_of_element_located(self.ERROR))
        return self

    def _click(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )
        self.wait.until(lambda d: d.execute_script(IN_VIEWPORT, element))
        element.click()
        return self

    def _text(self, locator):
        elements = self.driver.find_elements(*locator)
        return elements[0].text.strip() if elements else ""

    def title(self):
        return self._text(self.TITLE)

    def kicker(self):
        return self._text(self.KICKER)

    def wait_for_title(self, expected):
        self.wait.until(lambda d: self.title() == expected)
        return self

    def price_text(self):
        return self._text(self.PRICE).replace(" ", " ")

    def has_price(self):
        return len(self.driver.find_elements(*self.PRICE)) > 0

    def posted_text(self):
        return self._text(self.POSTED)

    def has_posted_date(self):
        return len(self.driver.find_elements(*self.POSTED)) > 0

    def location_text(self):
        return self._text(self.LOCATION_TEXT)

    def has_location_card(self):
        return len(self.driver.find_elements(*self.LOCATION_CARD)) > 0

    def error_text(self):
        element = self.wait.until(EC.visibility_of_element_located(self.ERROR))
        return element.text.strip()

    def error_detail(self):
        return self._text(self.ERROR_DETAIL)

    def wait_for_listing(self, listing_id):
        target = "%s/listing/%s" % (self.base_url, listing_id)
        self.wait.until(lambda d: d.current_url.rstrip("/") == target)
        return self

    def wait_for_owner_profile(self, owner_id):
        target = "%s/owner/%s" % (self.base_url, owner_id)
        self.wait.until(lambda d: d.current_url.rstrip("/") == target)
        return self

    def toggle_favorite(self):
        self._click(self.driver.find_element(*self.FAVORITE))
        return self

    def is_favorited(self):
        button = self.driver.find_element(*self.FAVORITE)
        return button.get_attribute("aria-pressed") == "true"

    def wait_until_favorited(self, expected):
        self.wait.until(lambda d: self.is_favorited() == expected)
        return self

    def save_label(self):
        return self._text(self.SAVE)

    def contact_owner(self):
        self._click(self.driver.find_element(*self.CONTACT))
        return self

    def see_owner(self):
        self._click(self.driver.find_element(*self.SEE_OWNER))
        return self

    def copy_link(self):
        self._click(self.driver.find_element(*self.COPY))
        return self

    def copy_label(self):
        return self.driver.find_element(*self.COPY).get_attribute("title")

    def wait_for_copy_label(self, expected, timeout=10):
        WebDriverWait(self.driver, timeout).until(
            lambda d: self.copy_label() == expected
        )
        return self

    def stub_clipboard(self, succeeds=True):
        self.driver.execute_script(CLIPBOARD_STUB, succeeds)
        return self

    def copied_text(self):
        return self.driver.execute_script("return window.__uiTestCopiedText;")

    def health_records(self):
        records = []
        for item in self.driver.find_elements(*self.HEALTH_RECORD):
            heading = item.find_elements(By.CSS_SELECTOR, ".health-record-heading > *")
            clinic = item.find_elements(By.CSS_SELECTOR, "small")
            records.append(
                {
                    "type": heading[0].text.strip() if heading else "",
                    "date": heading[1].text.strip() if len(heading) > 1 else "",
                    "description": item.find_element(By.CSS_SELECTOR, "p").text.strip(),
                    "clinic": clinic[0].text.strip() if clinic else "",
                }
            )
        return records

    def health_empty_text(self):
        return self._text(self.HEALTH_EMPTY)

    def health_error_text(self):
        return self._text(self.HEALTH_ERROR)

    def scroll_to_top(self):
        self.driver.execute_script("window.scrollTo(0, 0);")
        self.wait.until(lambda d: d.execute_script("return window.scrollY;") == 0)
        return self

    def health_card_offset(self):
        element = self.driver.find_element(*self.HEALTH_CARD)
        return self.driver.execute_script(ELEMENT_TOP, element)

    def focus_pet_name(self):
        element = self.driver.find_element(*self.PET_LINK)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )
        self.wait.until(lambda d: d.execute_script(IN_VIEWPORT, element))
        return self

    def click_pet_name(self):
        self.driver.find_element(*self.PET_LINK).click()
        return self

    def wait_until_health_card_at_top(self, tolerance=5):
        self.wait.until(lambda d: abs(self.health_card_offset()) <= tolerance)
        return self

    def has_related_section(self):
        return len(self.driver.find_elements(*self.RELATED_SECTION)) > 0

    def related_titles(self):
        return [
            element.text.strip()
            for element in self.driver.find_elements(*self.RELATED_TITLE)
        ]

    def related_card(self, title):
        locator = (
            By.XPATH,
            "//article[contains(@class,'related-listing-card')]"
            "[.//h3[normalize-space()='%s']]" % title,
        )
        return self.wait.until(EC.presence_of_element_located(locator))

    def open_related(self, title):
        self._click(self.related_card(title).find_element(*self.RELATED_TITLE))
        return self

    def toggle_related_favorite(self, title):
        button = self.related_card(title).find_element(
            By.CSS_SELECTOR, ".related-favorite-btn"
        )
        self._click(button)
        return self

    def is_related_favorited(self, title):
        button = self.related_card(title).find_element(
            By.CSS_SELECTOR, ".related-favorite-btn"
        )
        return button.get_attribute("aria-pressed") == "true"

    def wait_until_related_favorited(self, title, expected):
        self.wait.until(lambda d: self.is_related_favorited(title) == expected)
        return self

    def alert_text(self):
        alert = self.wait.until(EC.alert_is_present())
        text = alert.text
        alert.accept()
        return text

    def retry(self):
        self._click(self.driver.find_element(*self.RETRY))
        return self

    def image_src(self):
        return self.driver.find_element(*self.MAIN_IMAGE).get_attribute("src")

    def wait_for_image_src(self, fragment):
        self.wait.until(lambda d: fragment in self.image_src())
        return self

    def record_navigations(self):
        self.listings.record_navigations()
        return self

    def recorded_mailto(self):
        return self.listings.recorded_mailto()
