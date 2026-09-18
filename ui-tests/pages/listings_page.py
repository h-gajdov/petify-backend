from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

HIDE_DEV_OVERLAY = """
const id = 'ui-test-hide-dev-overlay';
if (!document.getElementById(id)) {
  const style = document.createElement('style');
  style.id = id;
  style.textContent = '#__vue-devtools-container__ { display: none !important; }';
  document.head.appendChild(style);
}
"""

LISTINGS_STUB = """
const rows = arguments[0];
const original = window.fetch;
window.fetch = function (input, init) {
  const url = typeof input === 'string' ? input : String(input.url);
  if (url.indexOf('/api/public/listings') !== -1) {
    return Promise.resolve(
      new Response(JSON.stringify(rows), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  }
  return original.apply(this, arguments);
};
"""

FAILING_ENDPOINT_STUB = """
const marker = arguments[0];
const original = window.fetch;
window.fetch = function (input, init) {
  const url = typeof input === 'string' ? input : String(input.url);
  if (url.indexOf(marker) !== -1) {
    return Promise.resolve(
      new Response(JSON.stringify({ error: 'Simulated failure' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  }
  return original.apply(this, arguments);
};
"""

IN_VIEWPORT = """
const rect = arguments[0].getBoundingClientRect();
return rect.top >= 0 && rect.bottom <= window.innerHeight;
"""


def stub_row(**overrides):
    row = {
        "listing_id": 90001,
        "status": "ACTIVE",
        "price": 100,
        "description": "Stubbed listing.",
        "created_at": "2026-01-01T00:00:00",
        "animal_id": None,
        "owner_id": None,
        "animal_name": "StubPet",
        "species": "Dog",
        "breed": "Beagle",
        "located_name": "Ohrid",
        "photo_url": None,
        "owner_name": "Stub Owner",
        "owner_email": "stub.owner@petify.test",
    }
    row.update(overrides)
    return row


class ListingsPage:
    ACTIVE_PET_BUTTON = (By.CSS_SELECTOR, ".pet-btn.active")
    BREED = (By.CSS_SELECTOR, "select[aria-label='Filter by breed']")
    CITY = (By.CSS_SELECTOR, "select[aria-label='Filter by location']")
    VIEW_MODE = (By.CSS_SELECTOR, ".view-mode-btn")
    ACTIVE_VIEW_MODE = (By.CSS_SELECTOR, ".view-mode-btn.active")
    RELOAD = (By.CSS_SELECTOR, ".listings-header button.btn-outline-secondary")
    TITLE = (By.CSS_SELECTOR, ".listings-title")
    CARD = (By.CSS_SELECTOR, ".listing-card")
    CARD_TITLE = (By.CSS_SELECTOR, ".listing-card .title")
    ERROR = (By.CSS_SELECTOR, ".alert.alert-warning[role='alert']")
    LOADING = (By.XPATH, "//p[normalize-space()='Loading listings…']")
    EMPTY = (By.XPATH, "//p[normalize-space()='No listings match your filters.']")

    def __init__(self, driver, base_url, timeout=20):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)

    def open(self):
        self.driver.get(self.base_url + "/")
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        return self.wait_until_loaded()

    def wait_until_loaded(self):
        self.wait.until(
            lambda d: not d.find_elements(*self.LOADING)
            and (d.find_elements(*self.CARD) or d.find_elements(*self.EMPTY))
        )
        return self

    def reload(self):
        self._click(self.driver.find_element(*self.RELOAD))
        return self.wait_until_loaded()

    def _click(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )
        self.wait.until(lambda d: d.execute_script(IN_VIEWPORT, element))
        element.click()
        return self

    def card(self, title):
        locator = (
            By.XPATH,
            "//article[contains(@class,'listing-card')][.//h3[normalize-space()='%s']]"
            % title,
        )
        return self.wait.until(EC.presence_of_element_located(locator))

    def titles(self):
        return [
            element.text.strip()
            for element in self.driver.find_elements(*self.CARD_TITLE)
        ]

    def has_card(self, title):
        return title in self.titles()

    def pet_names(self):
        return [
            chip.text.strip()
            for chip in self.driver.find_elements(
                By.CSS_SELECTOR, ".listing-card .chips .chip:first-child"
            )
        ]

    def species_shown(self):
        shown = []
        for card in self.driver.find_elements(*self.CARD):
            spans = card.find_elements(By.CSS_SELECTOR, ".meta span")
            shown.append(spans[0].text.strip() if spans else "")
        return shown

    def cities_shown(self):
        shown = []
        for card in self.driver.find_elements(*self.CARD):
            location = card.find_elements(By.CSS_SELECTOR, ".location")
            shown.append(location[0].text.strip() if location else "")
        return shown

    def select_pet_type(self, label):
        locator = (
            By.XPATH,
            "//button[contains(@class,'pet-btn')][.//span[normalize-space()='%s']]"
            % label,
        )
        self._click(self.driver.find_element(*locator))
        return self

    def active_pet_type(self):
        return self.driver.find_element(*self.ACTIVE_PET_BUTTON).text.strip()

    def _select(self, locator):
        return Select(self.driver.find_element(*locator))

    def breed_options(self):
        return [
            option.get_attribute("value")
            for option in self._select(self.BREED).options
        ]

    def select_breed(self, value):
        self._select(self.BREED).select_by_value(value)
        return self

    def selected_breed(self):
        return self._select(self.BREED).first_selected_option.get_attribute("value")

    def city_options(self):
        return [
            option.get_attribute("value") for option in self._select(self.CITY).options
        ]

    def select_city(self, value):
        self._select(self.CITY).select_by_value(value)
        return self

    def selected_city(self):
        return self._select(self.CITY).first_selected_option.get_attribute("value")

    def view_modes(self):
        return [
            button.text.strip() for button in self.driver.find_elements(*self.VIEW_MODE)
        ]

    def select_view_mode(self, label):
        locator = (
            By.XPATH,
            "//button[contains(@class,'view-mode-btn')][normalize-space()='%s']" % label,
        )
        self._click(self.driver.find_element(*locator))
        return self.wait_until_loaded()

    def active_view_mode(self):
        return self.driver.find_element(*self.ACTIVE_VIEW_MODE).text.strip()

    def listings_title(self):
        return self.driver.find_element(*self.TITLE).text.strip()

    def is_empty(self):
        return len(self.driver.find_elements(*self.EMPTY)) > 0

    def error_message(self):
        element = self.wait.until(EC.visibility_of_element_located(self.ERROR))
        return element.text.strip()

    def has_error(self):
        return len(self.driver.find_elements(*self.ERROR)) > 0

    def toggle_favorite(self, title):
        button = self.card(title).find_element(By.CSS_SELECTOR, "button.favorite")
        self._click(button)
        return self

    def is_favorited(self, title):
        button = self.card(title).find_element(By.CSS_SELECTOR, "button.favorite")
        return button.get_attribute("aria-pressed") == "true"

    def wait_until_favorited(self, title, expected):
        self.wait.until(lambda d: self.is_favorited(title) == expected)
        return self

    def open_card(self, title):
        self._click(self.card(title).find_element(By.CSS_SELECTOR, ".title"))
        return self

    def click_view(self, title):
        self._click(self.card(title).find_element(By.CSS_SELECTOR, "button.primary"))
        return self

    def click_contact(self, title):
        self._click(self.card(title).find_element(By.CSS_SELECTOR, "button.secondary"))
        return self

    def wait_for_details(self, listing_id):
        target = "%s/listing/%s" % (self.base_url, listing_id)
        self.wait.until(lambda d: d.current_url.rstrip("/") == target)
        return self

    def stub_listings(self, rows):
        self.driver.execute_script(LISTINGS_STUB, rows)
        return self

    def fail_endpoint(self, marker):
        self.driver.execute_script(FAILING_ENDPOINT_STUB, marker)
        return self

    def alert_text(self):
        alert = self.wait.until(EC.alert_is_present())
        text = alert.text
        alert.accept()
        return text
