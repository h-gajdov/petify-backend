import json

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .listings_page import HIDE_DEV_OVERLAY

ROUTES_STUB = """
const routes = arguments[0];
const original = window.fetch;
window.__uiTestRequests = [];
window.__uiTestBodies = [];
window.__uiTestPending = 0;
window.fetch = function (input, init) {
  const url = typeof input === 'string' ? input : String(input.url);
  const method = String((init && init.method) || 'GET').toUpperCase();
  const body = init && init.body;
  window.__uiTestRequests.push(method + ' ' + url);
  window.__uiTestBodies.push({
    method: method,
    url: url,
    body: typeof body === 'string' ? body : null,
  });
  window.__uiTestPending += 1;
  const done = function (value) {
    window.__uiTestPending -= 1;
    return value;
  };
  const fail = function (error) {
    window.__uiTestPending -= 1;
    throw error;
  };
  for (let index = 0; index < routes.length; index += 1) {
    const route = routes[index];
    if (url.indexOf(route.match) === -1) continue;
    if (route.method && route.method !== method) continue;
    if (route.times === 0) continue;
    if (route.times) route.times -= 1;
    return Promise.resolve(
      new Response(route.body === null ? '' : JSON.stringify(route.body), {
        status: route.status,
        headers: { 'Content-Type': 'application/json' },
      })
    ).then(done, fail);
  }
  return original.apply(this, arguments).then(done, fail);
};
"""

ROUTER_PUSH = """
document.querySelector('#app').__vue_app__.config.globalProperties.$router.push(arguments[0]);
"""

SET_VALUE = """
const input = arguments[0];
input.value = arguments[1];
input.dispatchEvent(new Event('input', { bubbles: true }));
input.dispatchEvent(new Event('change', { bubbles: true }));
"""

ELEMENT_TOP = "return arguments[0].getBoundingClientRect().top;"

CENTER_AND_CHECK = """
const element = arguments[0];
element.scrollIntoView({ block: 'center', behavior: 'instant' });
const rect = element.getBoundingClientRect();
const hit = document.elementFromPoint(
  rect.left + rect.width / 2,
  rect.top + rect.height / 2
);
return !!hit && (hit === element || element.contains(hit));
"""

ANIMATIONS_DONE = """
return document.getAnimations().every(function (animation) {
  return animation.playState !== 'running';
});
"""

MY_LISTINGS_URL = "/api/listings/my-listings"
LISTINGS_URL = "/api/listings/"
FAVORITES_URL = "/api/favorites"
CLINICS_URL = "/api/clinics"
APPOINTMENTS_URL = "/api/appointments"
MY_APPOINTMENTS_URL = "/api/appointments/my"
HEALTH_RECORDS_URL = "/api/health-records"
CLINIC_REVIEWS_URL = "/api/reviews/clinics/"
REVIEWS_URL = "/api/reviews/"


def route(match, body=None, status=200, method=None, times=None):
    return {
        "match": match,
        "status": status,
        "body": body,
        "method": method,
        "times": times,
    }


def stub_pet(animal_id, name, **overrides):
    pet = {
        "animalId": animal_id,
        "name": name,
        "sex": "FEMALE",
        "dateOfBirth": "2021-03-04",
        "photoUrl": None,
        "type": "PET",
        "species": "Dog",
        "breed": "Beagle",
        "locatedName": "Ohrid",
    }
    pet.update(overrides)
    return pet


def stub_listing(listing_id, animal_id, **overrides):
    listing = {
        "listingId": listing_id,
        "ownerId": 94000,
        "animalId": animal_id,
        "description": "Stubbed profile listing.",
        "price": 120.0,
        "status": "ACTIVE",
        "createdAt": "2026-05-06T10:00:00",
    }
    listing.update(overrides)
    return listing


def stub_clinic(clinic_id, name, **overrides):
    clinic = {
        "clinicId": clinic_id,
        "name": name,
        "city": "Skopje",
        "address": "Testna 1",
    }
    clinic.update(overrides)
    return clinic


def stub_slot(date, label):
    return {"dateTime": "%sT%s:00" % (date, label), "label": label}


def stub_appointment(appointment_id, date_time, **overrides):
    appointment = {
        "appointmentId": appointment_id,
        "clinicId": 94501,
        "clinicName": "Stub Clinic",
        "clinicCity": "Skopje",
        "clinicAddress": "Testna 1",
        "animalId": 94101,
        "petName": "StubPet",
        "petSpecies": "Dog",
        "status": "CONFIRMED",
        "dateTime": date_time,
        "notes": None,
    }
    appointment.update(overrides)
    return appointment


def stub_health_record(record_id, appointment_id, **overrides):
    record = {
        "healthRecordId": record_id,
        "animalId": 94101,
        "animalName": "StubPet",
        "appointmentId": appointment_id,
        "clinicId": 94501,
        "clinicName": "Stub Clinic",
        "type": "Vaccination",
        "description": "Rabies booster.",
        "date": "2026-05-06",
    }
    record.update(overrides)
    return record


def stub_clinic_review(review_id, **overrides):
    review = {
        "reviewId": review_id,
        "reviewerId": 94000,
        "reviewerName": "Olive Owner",
        "reviewerUsername": "ui.owner",
        "rating": 4,
        "comment": "Kind staff.",
        "createdAt": "2026-05-07T09:00:00",
    }
    review.update(overrides)
    return review


def profile_routes(
    user_id,
    listings=(),
    pets=(),
    favorites=(),
    clinics=(),
    appointments=(),
    verified=False,
):
    return [
        route("/api/users/%s/pets" % user_id, list(pets), method="GET"),
        route(
            "/api/users/%s/verified" % user_id,
            {"userId": user_id, "verified": verified},
            method="GET",
        ),
        route(MY_LISTINGS_URL, list(listings), method="GET"),
        route(FAVORITES_URL, list(favorites), method="GET"),
        route(CLINICS_URL, list(clinics), method="GET"),
        route(MY_APPOINTMENTS_URL, list(appointments), method="GET"),
        route("/mine", None, method="GET"),
        route("/health-records", [], method="GET"),
    ]


class ProfilePage:
    NOT_LOGGED_IN = (By.CSS_SELECTOR, ".profile-container .alert-warning")
    NAME = (By.CSS_SELECTOR, ".profile-name")
    USERNAME = (By.CSS_SELECTOR, ".profile-username")
    EMAIL = (By.CSS_SELECTOR, ".profile-email")
    TYPE_BADGE = (By.CSS_SELECTOR, ".profile-badge .badge")
    VERIFIED = (By.CSS_SELECTOR, ".verified-badge")
    NAV_LINK = (By.CSS_SELECTOR, "nav a[href='/profile']")
    TAB = (By.CSS_SELECTOR, ".nav-tabs .nav-link")
    ACTIVE_TAB = (By.CSS_SELECTOR, ".nav-tabs .nav-link.active")
    SECTION_TITLE = (By.CSS_SELECTOR, ".tab-content-section h2.section-title")
    EMPTY_TEXT = (By.CSS_SELECTOR, ".tab-content-section > .empty-state p")
    LISTING_CARD = (By.CSS_SELECTOR, ".listing-card:not(.favorite-listing)")
    PET_CARD = (By.CSS_SELECTOR, ".pet-card")
    ADD_PET = (By.CSS_SELECTOR, ".section-header-row button")
    ADD_PET_PANEL = (By.CSS_SELECTOR, ".add-pet-panel")
    PET_NAME = (By.ID, "petName")
    PET_SEX = (By.ID, "petSex")
    PET_SPECIES = (By.ID, "petSpecies")
    PET_BREED = (By.ID, "petBreed")
    PET_DOB = (By.ID, "petDateOfBirth")
    PET_LOCATION = (By.ID, "petLocatedName")
    PET_PHOTO = (By.ID, "petPhoto")
    PET_PREVIEW = (By.CSS_SELECTOR, ".pet-photo-preview img")
    PET_FORM_ERROR = (By.CSS_SELECTOR, ".add-pet-panel .alert-danger")
    PET_SUBMIT = (By.CSS_SELECTOR, ".add-pet-panel button[type='submit']")
    LISTING_PET = (By.ID, "petSelect")
    LISTING_DESCRIPTION = (By.ID, "description")
    LISTING_PRICE = (By.ID, "price")
    LISTING_FORM_ERROR = (By.CSS_SELECTOR, ".form-card .alert-danger")
    LISTING_SUBMIT = (By.CSS_SELECTOR, ".form-card button[type='submit']")
    FAVORITE_CARD = (By.CSS_SELECTOR, ".favorite-listing")
    CALENDAR_TITLE = (By.CSS_SELECTOR, ".calendar-title")
    CALENDAR_BUTTON = (By.CSS_SELECTOR, ".calendar-header > button")
    MONTH_SELECT = (By.CSS_SELECTOR, ".month-year-editor select")
    YEAR_INPUT = (By.CSS_SELECTOR, ".month-year-editor input")
    DAY = (By.CSS_SELECTOR, ".calendar-day")
    DAY_TITLE = (By.CSS_SELECTOR, ".appointments-day-title")
    DAY_EMPTY = (By.CSS_SELECTOR, ".appointments-empty")
    APPOINTMENT_CARD = (By.CSS_SELECTOR, ".appointment-card")
    APPOINTMENTS_LOADING = (By.CSS_SELECTOR, ".tab-content-section > .alert-info")
    APPOINTMENT_PET = (By.ID, "appointmentPet")
    APPOINTMENT_CLINIC = (By.ID, "appointmentClinic")
    APPOINTMENT_DATE = (By.ID, "appointmentDate")
    APPOINTMENT_SLOT = (By.ID, "appointmentSlot")
    APPOINTMENT_NOTES = (By.ID, "appointmentNotes")
    BOOKING_FORM = (
        By.XPATH,
        "//h2[normalize-space()='Create Appointment']"
        "/following-sibling::div[contains(@class,'form-card')]//form",
    )

    def __init__(self, driver, base_url, timeout=20):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(
            driver, timeout, ignored_exceptions=(StaleElementReferenceException,)
        )

    def open(self, path="/profile"):
        self.driver.get(self.base_url + path)
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        return self

    def open_from_nav(self):
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        self._click(self.wait.until(EC.presence_of_element_located(self.NAV_LINK)))
        return self.wait_until_loaded()

    def navigate(self, path):
        self.driver.execute_script(ROUTER_PUSH, path)
        return self

    def open_stubbed(self, user_id, routes=(), **data):
        self.install_routes(list(routes) + profile_routes(user_id, **data))
        return self.open_from_nav()

    def install_routes(self, routes):
        self.driver.execute_script(ROUTES_STUB, list(routes))
        return self

    def requests(self):
        return self.driver.execute_script("return window.__uiTestRequests || [];")

    def request_count(self, match, method=None):
        return len(
            [
                request
                for request in self.requests()
                if match in request
                and (method is None or request.startswith(method + " "))
            ]
        )

    def request_bodies(self, match, method=None):
        rows = self.driver.execute_script("return window.__uiTestBodies || [];")
        return [
            json.loads(row["body"])
            for row in rows
            if match in row["url"]
            and row["body"]
            and (method is None or row["method"] == method)
        ]

    def wait_until_settled(self):
        self.wait.until(
            lambda d: d.execute_script("return window.__uiTestPending || 0;") == 0
        )
        return self

    def wait_until_loaded(self):
        self.wait.until(lambda d: d.find_elements(*self.TAB))
        return self.wait_until_settled().wait_for_animations()

    def wait_for_path(self, path):
        target = (self.base_url + path).rstrip("/")
        self.wait.until(lambda d: d.current_url.rstrip("/") == target)
        return self

    def _click(self, element):
        self.wait.until(lambda d: d.execute_script(CENTER_AND_CHECK, element))
        element.click()
        return self

    def _text(self, locator, context=None):
        source = context if context is not None else self.driver
        elements = source.find_elements(*locator)
        return elements[0].text.strip() if elements else ""

    def _button(self, text, context=None):
        source = context if context is not None else self.driver
        locator = (By.XPATH, ".//button[normalize-space()='%s']" % text)
        return source.find_element(*locator)

    def _has_button(self, text, context=None):
        source = context if context is not None else self.driver
        locator = (By.XPATH, ".//button[normalize-space()='%s']" % text)
        return len(source.find_elements(*locator)) > 0

    def _type(self, locator, value):
        field = self.driver.find_element(*locator)
        field.clear()
        if value:
            field.send_keys(value)
        return self

    def _set_value(self, locator, value):
        self.driver.execute_script(SET_VALUE, self.driver.find_element(*locator), value)
        return self

    def _select(self, locator, value):
        Select(self.driver.find_element(*locator)).select_by_value(str(value))
        return self

    def selected_value(self, locator):
        return self.driver.find_element(*locator).get_attribute("value")

    def validity(self, locator, key):
        element = self.driver.find_element(*locator)
        return self.driver.execute_script(
            "return arguments[0].validity[arguments[1]];", element, key
        )

    def accept_dialog(self):
        self.wait.until(EC.alert_is_present()).accept()
        return self

    def dismiss_dialog(self):
        self.wait.until(EC.alert_is_present()).dismiss()
        return self

    def is_not_logged_in_shown(self):
        return len(self.driver.find_elements(*self.NOT_LOGGED_IN)) > 0

    def header(self):
        return {
            "name": self._text(self.NAME),
            "username": self._text(self.USERNAME),
            "email": self._text(self.EMAIL),
            "type": self._text(self.TYPE_BADGE),
        }

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

    def wait_for_tab_labels(self, expected):
        self.wait.until(lambda d: self.tab_labels() == expected)
        return self

    def active_tab(self):
        return " ".join(self._text(self.ACTIVE_TAB).split())

    def select_tab(self, label):
        tab = next(
            element
            for element in self.driver.find_elements(*self.TAB)
            if " ".join(element.text.split()) == label
        )
        self._click(tab)
        return self.wait_for_active_tab(label)

    def wait_for_active_tab(self, label):
        self.wait.until(lambda d: self.active_tab() == label)
        return self.wait_for_animations()

    def wait_for_animations(self):
        self.wait.until(lambda d: d.execute_script(ANIMATIONS_DONE))
        return self

    def section_titles(self):
        return [
            element.text.strip()
            for element in self.driver.find_elements(*self.SECTION_TITLE)
        ]

    def empty_texts(self):
        return [
            element.text.strip()
            for element in self.driver.find_elements(*self.EMPTY_TEXT)
            if element.text.strip()
        ]

    def click_link(self, text):
        locator = (
            By.XPATH,
            "//div[contains(@class,'tab-content-section')]//a[normalize-space()='%s']"
            % text,
        )
        link = self.driver.find_element(*locator)
        self._click(link)
        self.wait.until(EC.staleness_of(link))
        return self.wait_for_animations()

    def listing_cards(self):
        rows = []
        for card in self.driver.find_elements(*self.LISTING_CARD):
            rows.append(
                {
                    "pet": self._text((By.CSS_SELECTOR, ".listing-title"), card),
                    "status": self._text((By.CSS_SELECTOR, ".badge"), card),
                    "description": self._text(
                        (By.CSS_SELECTOR, ".listing-description"), card
                    ),
                    "price": self._text((By.CSS_SELECTOR, ".listing-price"), card),
                    "date": self._text((By.CSS_SELECTOR, ".listing-date"), card),
                    "select": card.find_element(By.CSS_SELECTOR, "select").get_attribute(
                        "value"
                    ),
                }
            )
        return rows

    def wait_for_listing_statuses(self, expected):
        self.wait.until(
            lambda d: [row["status"] for row in self.listing_cards()] == expected
        )
        return self

    def wait_for_listing_count(self, expected):
        self.wait.until(lambda d: len(self.listing_cards()) == expected)
        return self

    def _listing_card(self, description):
        locator = (
            By.XPATH,
            "//div[contains(@class,'listing-card')"
            " and not(contains(@class,'favorite-listing'))]"
            "[p[normalize-space()='%s']]" % description,
        )
        return self.driver.find_element(*locator)

    def change_listing_status(self, description, status):
        select = self._listing_card(description).find_element(By.CSS_SELECTOR, "select")
        Select(select).select_by_value(status)
        return self

    def delete_listing(self, description):
        self._click(
            self._listing_card(description).find_element(By.CSS_SELECTOR, ".btn-danger")
        )
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
                    "buttons": [
                        button.text.strip()
                        for button in card.find_elements(By.CSS_SELECTOR, "button")
                    ],
                }
            )
        return rows

    def pet_names(self):
        return [row["name"] for row in self.pet_cards()]

    def wait_for_pet_names(self, expected):
        self.wait.until(lambda d: self.pet_names() == expected)
        return self

    def pet_card_button(self, text):
        self._click(self._button(text))
        return self

    def open_add_pet(self):
        self._click(self.driver.find_element(*self.ADD_PET))
        self.wait.until(EC.visibility_of_element_located(self.ADD_PET_PANEL))
        return self.wait_for_animations()

    def has_add_pet_panel(self):
        return len(self.driver.find_elements(*self.ADD_PET_PANEL)) > 0

    def add_pet_panel_top(self):
        return self.driver.execute_script(
            ELEMENT_TOP, self.driver.find_element(*self.ADD_PET_PANEL)
        )

    def wait_until_add_pet_panel_at_top(self, tolerance=5):
        self.wait.until(lambda d: abs(self.add_pet_panel_top()) <= tolerance)
        return self

    def scroll_to_top(self):
        self.driver.execute_script("window.scrollTo(0, 0);")
        self.wait.until(lambda d: d.execute_script("return window.scrollY;") == 0)
        return self

    def cancel_add_pet(self):
        panel = self.driver.find_element(*self.ADD_PET_PANEL)
        self._click(self._button("Cancel", panel))
        self.wait.until(lambda d: not self.has_add_pet_panel())
        return self

    def fill_pet(self, name="", sex="", species="", breed="", location=""):
        self._type(self.PET_NAME, name)
        self._select(self.PET_SEX, sex)
        self._select(self.PET_SPECIES, species)
        self._type(self.PET_BREED, breed)
        self._type(self.PET_LOCATION, location)
        return self

    def set_pet_birth_date(self, value):
        return self._set_value(self.PET_DOB, value)

    def pet_form_values(self):
        return {
            "name": self.selected_value(self.PET_NAME),
            "sex": self.selected_value(self.PET_SEX),
            "species": self.selected_value(self.PET_SPECIES),
            "breed": self.selected_value(self.PET_BREED),
            "location": self.selected_value(self.PET_LOCATION),
        }

    def choose_pet_photo(self, path):
        self.driver.find_element(*self.PET_PHOTO).send_keys(str(path))
        return self

    def pet_photo_value(self):
        return self.selected_value(self.PET_PHOTO)

    def has_pet_preview(self):
        return len(self.driver.find_elements(*self.PET_PREVIEW)) > 0

    def pet_preview_src(self):
        return self.driver.find_element(*self.PET_PREVIEW).get_attribute("src")

    def remove_pet_photo(self):
        self._click(self._button("Remove photo"))
        self.wait.until(lambda d: not self.has_pet_preview())
        return self

    def pet_form_error(self):
        return self._text(self.PET_FORM_ERROR)

    def submit_pet(self):
        self._click(self.driver.find_element(*self.PET_SUBMIT))
        return self

    def fill_listing(self, pet_id=None, description="", price=""):
        if pet_id is not None:
            self._select(self.LISTING_PET, pet_id)
        self._type(self.LISTING_DESCRIPTION, description)
        self._type(self.LISTING_PRICE, price)
        return self

    def listing_form_values(self):
        return {
            "pet": self.selected_value(self.LISTING_PET),
            "description": self.selected_value(self.LISTING_DESCRIPTION),
            "price": self.selected_value(self.LISTING_PRICE),
        }

    def listing_pet_options(self):
        return [
            option.text.strip()
            for option in Select(self.driver.find_element(*self.LISTING_PET)).options
        ]

    def has_listing_form(self):
        return len(self.driver.find_elements(*self.LISTING_PET)) > 0

    def listing_form_error(self):
        return self._text(self.LISTING_FORM_ERROR)

    def wait_for_listing_form_error(self, expected):
        self.wait.until(lambda d: self.listing_form_error() == expected)
        return self

    def submit_listing(self):
        self._click(self.driver.find_element(*self.LISTING_SUBMIT))
        return self

    def favorite_cards(self):
        rows = []
        for card in self.driver.find_elements(*self.FAVORITE_CARD):
            rows.append(
                {
                    "pet": self._text((By.CSS_SELECTOR, ".listing-title"), card),
                    "status": self._text((By.CSS_SELECTOR, ".badge"), card),
                    "description": self._text(
                        (By.CSS_SELECTOR, ".listing-description"), card
                    ),
                    "price": self._text((By.CSS_SELECTOR, ".listing-price"), card),
                }
            )
        return rows

    def favorite_pets(self):
        return [row["pet"] for row in self.favorite_cards()]

    def wait_for_favorite_pets(self, expected):
        self.wait.until(lambda d: self.favorite_pets() == expected)
        return self

    def _favorite_card(self, pet_name):
        locator = (
            By.XPATH,
            "//div[contains(@class,'favorite-listing')]"
            "[.//h5[normalize-space()='%s']]" % pet_name,
        )
        return self.driver.find_element(*locator)

    def open_favorite(self, pet_name):
        self._click(
            self._favorite_card(pet_name).find_element(By.CSS_SELECTOR, ".listing-title")
        )
        return self

    def remove_favorite(self, pet_name):
        self._click(
            self._favorite_card(pet_name).find_element(By.CSS_SELECTOR, "button")
        )
        return self

    def favorite_image_src(self, pet_name):
        return self._favorite_card(pet_name).find_element(
            By.CSS_SELECTOR, "img.favorite-image"
        ).get_attribute("src")

    def wait_for_favorite_image(self, pet_name, fragment):
        self.wait.until(lambda d: fragment in self.favorite_image_src(pet_name))
        return self

    def calendar_title(self):
        return self._text(self.CALENDAR_TITLE)

    def wait_for_calendar_title(self, expected):
        self.wait.until(lambda d: self.calendar_title() == expected)
        return self

    def calendar_prev(self):
        self._click(self.driver.find_elements(*self.CALENDAR_BUTTON)[0])
        return self

    def calendar_next(self):
        self._click(self.driver.find_elements(*self.CALENDAR_BUTTON)[-1])
        return self

    def open_month_editor(self):
        title = self.driver.find_element(*self.CALENDAR_TITLE)
        ActionChains(self.driver).double_click(title).perform()
        self.wait.until(EC.presence_of_element_located(self.YEAR_INPUT))
        return self

    def has_month_editor(self):
        return len(self.driver.find_elements(*self.YEAR_INPUT)) > 0

    def set_month_year(self, month_index, year):
        Select(self.driver.find_element(*self.MONTH_SELECT)).select_by_value(
            str(month_index)
        )
        field = self.driver.find_element(*self.YEAR_INPUT)
        field.clear()
        field.send_keys(str(year))
        return self

    def apply_month_year(self):
        self._click(self._button("Go"))
        return self

    def cancel_month_year(self):
        editor = self.driver.find_element(By.CSS_SELECTOR, ".month-year-editor")
        self._click(self._button("Cancel", editor))
        return self

    def go_to_month(self, value):
        label = value.strftime("%B %Y")
        if self.calendar_title() != label:
            self.open_month_editor().set_month_year(value.month - 1, value.year)
            self.apply_month_year().wait_for_calendar_title(label)
        return self

    def _day(self, number):
        locator = (
            By.XPATH,
            "//button[contains(@class,'calendar-day')]"
            "[span[contains(@class,'day-number')][normalize-space()='%s']]" % number,
        )
        return self.driver.find_element(*locator)

    def select_day(self, value):
        self.go_to_month(value)
        self._click(self._day(value.day))
        self.wait.until(
            lambda d: self.day_title() == "Appointments for %s" % value.isoformat()
        )
        return self

    def day_classes(self, value):
        self.go_to_month(value)
        return self._day(value.day).get_attribute("class").split()

    def day_title(self):
        return self._text(self.DAY_TITLE)

    def day_empty_text(self):
        return self._text(self.DAY_EMPTY)

    def wait_for_appointments_loaded(self):
        self.wait.until(lambda d: not d.find_elements(*self.APPOINTMENTS_LOADING))
        self.wait.until(EC.presence_of_element_located(self.CALENDAR_TITLE))
        return self.wait_until_settled()

    def appointment_cards(self):
        rows = []
        for card in self.driver.find_elements(*self.APPOINTMENT_CARD):
            rows.append(
                {
                    "pet": " ".join(
                        self._text((By.CSS_SELECTOR, ".appointment-title"), card).split()
                    ),
                    "status": self._text((By.CSS_SELECTOR, ".badge"), card),
                    "time": self._text((By.CSS_SELECTOR, ".appointment-time"), card),
                    "clinic": " ".join(
                        self._text((By.CSS_SELECTOR, ".appointment-clinic"), card).split()
                    ),
                    "notes": self._text((By.CSS_SELECTOR, ".appointment-notes"), card),
                }
            )
        return rows

    def _appointment(self, pet_name):
        locator = (
            By.XPATH,
            "//div[contains(@class,'appointment-card')]"
            "[div/div[contains(@class,'appointment-title')]"
            "[starts-with(normalize-space(),'%s')]]"
            % pet_name,
        )
        return self.driver.find_element(*locator)

    def appointment_status(self, pet_name):
        return self._text((By.CSS_SELECTOR, ".badge"), self._appointment(pet_name))

    def wait_for_appointment_status(self, pet_name, expected):
        self.wait.until(lambda d: self.appointment_status(pet_name) == expected)
        return self

    def appointment_buttons(self, pet_name):
        card = self._appointment(pet_name)
        return [
            button.text.strip()
            for button in card.find_elements(By.CSS_SELECTOR, "button")
        ]

    def click_appointment_button(self, pet_name, text):
        self._click(self._button(text, self._appointment(pet_name)))
        return self

    def appointment_errors(self, pet_name):
        return [
            element.text.strip()
            for element in self._appointment(pet_name).find_elements(
                By.CSS_SELECTOR, ".alert-danger"
            )
        ]

    def wait_for_appointment_error(self, pet_name, expected):
        self.wait.until(lambda d: expected in self.appointment_errors(pet_name))
        return self

    def select_review_stars(self, pet_name, rating):
        stars = self._appointment(pet_name).find_elements(
            By.CSS_SELECTOR, ".clinic-review-form .clinic-review-stars button"
        )
        self._click(stars[rating - 1])
        return self

    def type_review_comment(self, pet_name, text):
        field = self._appointment(pet_name).find_element(
            By.CSS_SELECTOR, ".clinic-review-form textarea"
        )
        field.clear()
        field.send_keys(text)
        return self

    def review_form_rating(self, pet_name):
        return len(
            self._appointment(pet_name).find_elements(
                By.CSS_SELECTOR, ".clinic-review-form .clinic-review-stars button.active"
            )
        )

    def review_form_comment(self, pet_name):
        return self._appointment(pet_name).find_element(
            By.CSS_SELECTOR, ".clinic-review-form textarea"
        ).get_attribute("value")

    def review_summary(self, pet_name):
        card = self._appointment(pet_name)
        summaries = card.find_elements(By.CSS_SELECTOR, ".clinic-review-summary")
        if not summaries:
            return None
        stars = summaries[0].find_elements(
            By.CSS_SELECTOR, ".clinic-review-stars span.active"
        )
        return {
            "stars": len(stars),
            "comment": self._text(
                (By.CSS_SELECTOR, ".clinic-review-comment"), summaries[0]
            ),
        }

    def wait_for_review_summary(self, pet_name, expected):
        self.wait.until(lambda d: self.review_summary(pet_name) == expected)
        return self

    def fill_health_record(self, pet_name, record_type, description=""):
        card = self._appointment(pet_name)
        field = card.find_element(By.CSS_SELECTOR, ".health-record-form input")
        field.clear()
        if record_type:
            field.send_keys(record_type)
        area = card.find_element(By.CSS_SELECTOR, ".health-record-form textarea")
        area.clear()
        if description:
            area.send_keys(description)
        return self

    def health_type_validity(self, pet_name, key):
        field = self._appointment(pet_name).find_element(
            By.CSS_SELECTOR, ".health-record-form input"
        )
        return self.driver.execute_script(
            "return arguments[0].validity[arguments[1]];", field, key
        )

    def health_summary(self, pet_name):
        summaries = self._appointment(pet_name).find_elements(
            By.CSS_SELECTOR, ".health-record-summary"
        )
        if not summaries:
            return None
        return {
            "type": self._text((By.CSS_SELECTOR, "strong"), summaries[0]),
            "description": self._text((By.CSS_SELECTOR, "p"), summaries[0]),
            "date": self._text((By.CSS_SELECTOR, "small"), summaries[0]),
        }

    def wait_for_health_summary(self, pet_name):
        self.wait.until(lambda d: self.health_summary(pet_name) is not None)
        return self

    def fill_booking(self, pet_id=None, clinic_id=None, date=None):
        if pet_id is not None:
            self._select(self.APPOINTMENT_PET, pet_id)
        if clinic_id is not None:
            self._select(self.APPOINTMENT_CLINIC, clinic_id)
        if date is not None:
            self._set_value(self.APPOINTMENT_DATE, date)
        return self

    def choose_slot(self, date_time):
        self.wait.until(lambda d: date_time in self.slot_values())
        return self._select(self.APPOINTMENT_SLOT, date_time)

    def type_booking_notes(self, text):
        return self._type(self.APPOINTMENT_NOTES, text)

    def _slot_options(self):
        return Select(self.driver.find_element(*self.APPOINTMENT_SLOT)).options

    def slot_values(self):
        return [option.get_attribute("value") for option in self._slot_options()]

    def slot_labels(self):
        return [option.text.strip() for option in self._slot_options()]

    def wait_for_slot_labels(self, expected):
        self.wait.until(lambda d: self.slot_labels() == expected)
        return self

    def is_slot_enabled(self):
        return self.driver.find_element(*self.APPOINTMENT_SLOT).is_enabled()

    def slot_hint(self):
        locator = (
            By.XPATH,
            "//select[@id='appointmentSlot']/following-sibling::small",
        )
        return self._text(locator)

    def wait_for_slot_hint(self, expected):
        self.wait.until(lambda d: self.slot_hint() == expected)
        return self

    def booking_values(self):
        return {
            "pet": self.selected_value(self.APPOINTMENT_PET),
            "clinic": self.selected_value(self.APPOINTMENT_CLINIC),
            "date": self.selected_value(self.APPOINTMENT_DATE),
            "slot": self.selected_value(self.APPOINTMENT_SLOT),
            "notes": self.selected_value(self.APPOINTMENT_NOTES),
        }

    def booking_error(self):
        form = self.driver.find_element(*self.BOOKING_FORM)
        return self._text((By.CSS_SELECTOR, ".alert-danger"), form)

    def wait_for_booking_error(self, expected):
        self.wait.until(lambda d: self.booking_error() == expected)
        return self

    def submit_booking(self):
        form = self.driver.find_element(*self.BOOKING_FORM)
        self._click(form.find_element(By.CSS_SELECTOR, "button[type='submit']"))
        return self
