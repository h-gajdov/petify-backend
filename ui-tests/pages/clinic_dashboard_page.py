from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .listings_page import HIDE_DEV_OVERLAY, IN_VIEWPORT

ROUTES_STUB = """
const routes = arguments[0];
const original = window.fetch;
window.__uiTestRequests = [];
window.fetch = function (input, init) {
  const url = typeof input === 'string' ? input : String(input.url);
  const method = String((init && init.method) || 'GET').toUpperCase();
  window.__uiTestRequests.push(method + ' ' + url);
  for (let index = 0; index < routes.length; index += 1) {
    const route = routes[index];
    if (url.indexOf(route.match) === -1) continue;
    if (route.method && route.method !== method) continue;
    return Promise.resolve(
      new Response(route.body === null ? '' : JSON.stringify(route.body), {
        status: route.status,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  }
  return original.apply(this, arguments);
};
"""

SET_DATE = """
const input = arguments[0];
input.value = arguments[1];
input.dispatchEvent(new Event('input', { bubbles: true }));
input.dispatchEvent(new Event('change', { bubbles: true }));
"""

APPOINTMENTS_URL = "/api/appointments/my-clinic?date"
UNAVAILABLE_URL = "/api/appointments/my-clinic/unavailable-slots"
NO_SHOW_URL = "/no-show"
NOTIFICATIONS_URL = "/api/notifications/my"


def route(match, body=None, status=200, method=None):
    return {"match": match, "status": status, "body": body, "method": method}


def stub_appointment(date, label, **overrides):
    appointment = {
        "appointmentId": 90801,
        "clinicId": 90800,
        "animalId": 90802,
        "petName": "StubPet",
        "petSpecies": "Dog",
        "ownerId": 90803,
        "ownerName": "Stub Owner",
        "status": "CONFIRMED",
        "dateTime": "%sT%s:00" % (date, label),
        "label": label,
        "notes": None,
    }
    appointment.update(overrides)
    return appointment


def stub_blocked_slot(date, label, **overrides):
    slot = {
        "slotId": 90901,
        "clinicId": 90800,
        "dateTime": "%sT%s:00" % (date, label),
        "label": label,
        "reason": "Staff training",
    }
    slot.update(overrides)
    return slot


def stub_notification(notification_id, message, **overrides):
    notification = {
        "notificationId": notification_id,
        "type": "APPOINTMENT_CANCELLED",
        "message": message,
        "isRead": False,
        "createdAt": "2026-03-04T09:15:00",
    }
    notification.update(overrides)
    return notification


class ClinicDashboardPage:
    LOADING = (By.XPATH, "//div[normalize-space()='Loading clinic schedule...']")
    ALERT = (By.CSS_SELECTOR, ".dashboard-body .alert-danger")
    SUBTITLE = (By.CSS_SELECTOR, ".clinic-subtitle")
    EMPTY_STATE = (By.CSS_SELECTOR, ".empty-state h2")
    NAV_LINK = (By.CSS_SELECTOR, "a[href='/clinics']")
    DATE_INPUT = (By.CSS_SELECTOR, "input.date-input")
    HEADING = (By.CSS_SELECTOR, ".schedule-section .section-heading h2")
    REFRESH_SCHEDULE = (By.CSS_SELECTOR, ".schedule-section .section-heading button")
    SUMMARY_ITEM = (By.CSS_SELECTOR, ".summary-item")
    SLOT_CARD = (By.CSS_SELECTOR, ".slot-card")
    SLOT_TIME = (By.CSS_SELECTOR, ".slot-time")
    SLOT_STATUS = (By.CSS_SELECTOR, ".slot-status")
    SLOT_DETAIL = (By.CSS_SELECTOR, ".slot-detail")
    BLOCK_BUTTON = (By.CSS_SELECTOR, ".btn-outline-danger")
    UNBLOCK_BUTTON = (By.CSS_SELECTOR, ".btn-outline-secondary")
    APPOINTMENT_ROW = (By.CSS_SELECTOR, ".appointment-row")
    APPOINTMENTS_EMPTY = (By.CSS_SELECTOR, ".appointments-panel > .panel-empty")
    NOTIFICATION_ROW = (By.CSS_SELECTOR, ".notification-row")
    NOTIFICATIONS_EMPTY = (By.CSS_SELECTOR, ".notifications-panel .panel-empty")

    def __init__(self, driver, base_url, timeout=20):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(
            driver, timeout, ignored_exceptions=(StaleElementReferenceException,)
        )

    def open(self):
        self.driver.get(self.base_url + "/clinics")
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

    def wait_until_loaded(self):
        try:
            WebDriverWait(self.driver, 3, poll_frequency=0.05).until(
                EC.presence_of_element_located(self.LOADING)
            )
        except TimeoutException:
            pass
        self.wait.until(
            lambda d: not d.find_elements(*self.LOADING)
            and d.find_elements(*self.SLOT_CARD)
        )
        return self

    def wait_for_login_redirect(self):
        target = self.base_url + "/login"
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

    def clinic_subtitle(self):
        return self._text(self.SUBTITLE)

    def empty_state_title(self):
        return self._text(self.EMPTY_STATE)

    def has_dashboard(self):
        return len(self.driver.find_elements(*self.SLOT_CARD)) > 0

    def errors(self):
        return [
            element.text.strip()
            for element in self.driver.find_elements(*self.ALERT)
        ]

    def wait_for_error(self, expected):
        self.wait.until(lambda d: expected in self.errors())
        return self

    def wait_for_error_starting_with(self, prefix):
        self.wait.until(
            lambda d: any(text.startswith(prefix) for text in self.errors())
        )
        return self

    def selected_date(self):
        return self.driver.find_element(*self.DATE_INPUT).get_attribute("value")

    def select_date(self, value):
        self.driver.execute_script(
            SET_DATE, self.driver.find_element(*self.DATE_INPUT), value
        )
        self.wait.until(lambda d: self.selected_date() == value)
        return self.wait_until_loaded()

    def heading(self):
        return self._text(self.HEADING)

    def refresh_schedule(self):
        self._click(self.driver.find_element(*self.REFRESH_SCHEDULE))
        return self.wait_until_loaded()

    def summary(self):
        totals = {}
        for item in self.driver.find_elements(*self.SUMMARY_ITEM):
            label = item.find_element(By.CSS_SELECTOR, ".summary-label").text.strip()
            value = item.find_element(By.CSS_SELECTOR, ".summary-value").text.strip()
            totals[label] = int(value)
        return totals

    def slot(self, label):
        locator = (
            By.XPATH,
            "//div[contains(@class,'slot-card')]"
            "[div[contains(@class,'slot-time')][normalize-space()='%s']]" % label,
        )
        return self.wait.until(EC.presence_of_element_located(locator))

    def slot_labels(self):
        return [
            element.text.strip()
            for element in self.driver.find_elements(*self.SLOT_TIME)
        ]

    def slot_statuses(self):
        return [
            element.text.strip()
            for element in self.driver.find_elements(*self.SLOT_STATUS)
        ]

    def slot_kinds(self):
        kinds = []
        for card in self.driver.find_elements(*self.SLOT_CARD):
            classes = card.get_attribute("class").split()
            kinds.append(next(name for name in classes if name != "slot-card"))
        return kinds

    def slot_kind(self, label):
        classes = self.slot(label).get_attribute("class").split()
        return next(name for name in classes if name != "slot-card")

    def slot_status(self, label):
        return self._text(self.SLOT_STATUS, self.slot(label))

    def slot_detail(self, label):
        return self._text(self.SLOT_DETAIL, self.slot(label))

    def wait_for_slot_kind(self, label, expected):
        self.wait.until(lambda d: self.slot_kind(label) == expected)
        return self

    def has_block_button(self, label):
        return len(self.slot(label).find_elements(*self.BLOCK_BUTTON)) > 0

    def has_unblock_button(self, label):
        return len(self.slot(label).find_elements(*self.UNBLOCK_BUTTON)) > 0

    def block_slot(self, label):
        self._click(self.slot(label).find_element(*self.BLOCK_BUTTON))
        return self

    def unblock_slot(self, label):
        self._click(self.slot(label).find_element(*self.UNBLOCK_BUTTON))
        return self

    def accept_dialog(self, text=None):
        alert = self.wait.until(EC.alert_is_present())
        if text is not None:
            alert.send_keys(text)
        alert.accept()
        return self

    def dismiss_dialog(self):
        self.wait.until(EC.alert_is_present()).dismiss()
        return self

    def appointment_row(self, pet_name):
        locator = (
            By.XPATH,
            "//article[contains(@class,'appointment-row')]"
            "[.//div[contains(@class,'appointment-title')][normalize-space()='%s']]"
            % pet_name,
        )
        return self.wait.until(EC.presence_of_element_located(locator))

    def appointments(self):
        rows = []
        for row in self.driver.find_elements(*self.APPOINTMENT_ROW):
            rows.append(
                {
                    "time": row.find_element(
                        By.CSS_SELECTOR, ".appointment-time"
                    ).text.strip(),
                    "pet": row.find_element(
                        By.CSS_SELECTOR, ".appointment-title"
                    ).text.strip(),
                    "meta": row.find_element(
                        By.CSS_SELECTOR, ".appointment-meta"
                    ).text.strip(),
                    "status": row.find_element(By.CSS_SELECTOR, ".badge").text.strip(),
                }
            )
        return rows

    def appointments_empty_text(self):
        return self._text(self.APPOINTMENTS_EMPTY)

    def appointment_status(self, pet_name):
        return (
            self.appointment_row(pet_name)
            .find_element(By.CSS_SELECTOR, ".badge")
            .text.strip()
        )

    def wait_for_appointment_status(self, pet_name, expected):
        self.wait.until(lambda d: self.appointment_status(pet_name) == expected)
        return self

    def has_no_show_button(self, pet_name):
        return (
            len(
                self.appointment_row(pet_name).find_elements(
                    By.CSS_SELECTOR, ".appointment-action"
                )
            )
            > 0
        )

    def mark_no_show(self, pet_name):
        self._click(
            self.appointment_row(pet_name).find_element(
                By.CSS_SELECTOR, ".appointment-action"
            )
        )
        return self

    def notifications(self):
        rows = []
        for row in self.driver.find_elements(*self.NOTIFICATION_ROW):
            rows.append(
                {
                    "message": row.find_element(
                        By.CSS_SELECTOR, ".notification-message"
                    ).text.strip(),
                    "date": row.find_element(
                        By.CSS_SELECTOR, ".notification-date"
                    ).text.strip(),
                }
            )
        return rows

    def notifications_empty_text(self):
        return self._text(self.NOTIFICATIONS_EMPTY)

    def wait_for_notification_messages(self, expected):
        self.wait.until(
            lambda d: [row["message"] for row in self.notifications()] == expected
        )
        return self
