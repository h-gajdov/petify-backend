import json

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .listings_page import HIDE_DEV_OVERLAY, IN_VIEWPORT

ROUTES_STUB = """
const routes = arguments[0];
const original = window.fetch;
window.__uiTestRequests = [];
window.__uiTestBodies = [];
window.fetch = function (input, init) {
  const url = typeof input === 'string' ? input : String(input.url);
  const method = String((init && init.method) || 'GET').toUpperCase();
  window.__uiTestRequests.push(method + ' ' + url);
  window.__uiTestBodies.push({
    method: method,
    url: url,
    body: init && init.body ? String(init.body) : null,
  });
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

APPLICATIONS_URL = "/api/admin/clinic-applications"
APPROVE_URL = "/approve"
DENY_URL = "/deny"
CLINICS_URL = "/api/clinics"
CLINIC_REVIEWS_URL = "/api/reviews/clinics/"


def route(match, body=None, status=200, method=None):
    return {"match": match, "status": status, "body": body, "method": method}


def stub_application(application_id, name, **overrides):
    application = {
        "applicationId": application_id,
        "name": name,
        "email": "stub.clinic@petify.test",
        "phone": "070111222",
        "city": "Skopje",
        "address": "Testna 1",
        "submittedAt": "2026-02-18T10:30:00",
        "status": "PENDING",
        "reviewedAt": None,
        "reviewedBy": None,
        "denialReason": None,
    }
    application.update(overrides)
    return application


def stub_clinic(clinic_id, name, **overrides):
    clinic = {
        "clinicId": clinic_id,
        "name": name,
        "city": "Skopje",
        "address": "Testna 1",
    }
    clinic.update(overrides)
    return clinic


def stub_clinic_review(review_id, **overrides):
    review = {
        "reviewId": review_id,
        "reviewerId": 90701,
        "reviewerName": "Stub Reviewer",
        "reviewerUsername": "stub.reviewer",
        "rating": 5,
        "comment": "Great care.",
        "createdAt": "2026-02-20T09:15:00",
    }
    review.update(overrides)
    return review


class AdminClinicsPage:
    MAIN = (By.CSS_SELECTOR, "main.admin-moderation")
    PAGE_TITLE = (By.CSS_SELECTOR, ".page-title")
    ALERT = (By.CSS_SELECTOR, ".moderation-body .alert-danger")
    NAV_LINK = (By.CSS_SELECTOR, "a[href='/admin/clinics']")
    PANEL_TITLE = (By.CSS_SELECTOR, ".panel-header h2")
    APPLICATIONS_PANEL = (
        By.XPATH,
        "//section[contains(@class,'panel')]"
        "[.//h2[normalize-space()='Clinic Applications']]",
    )
    REVIEWS_PANEL = (
        By.XPATH,
        "//section[contains(@class,'panel')]"
        "[.//h2[normalize-space()='Clinic Reviews']]",
    )
    APPLICATION_CARD = (By.CSS_SELECTOR, ".application-card")
    APPLICATION_NAME = (By.CSS_SELECTOR, ".item-header h3")
    APPLICATION_BADGE = (By.CSS_SELECTOR, ".badge")
    APPLICATION_META = (By.CSS_SELECTOR, ".meta")
    APPLICATION_DENIAL = (By.CSS_SELECTOR, ".denial")
    APPROVE_BUTTON = (By.CSS_SELECTOR, ".actions .btn-success")
    DENY_BUTTON = (By.CSS_SELECTOR, ".actions .btn-outline-danger")
    EMPTY_STATE = (By.CSS_SELECTOR, ".empty-state")
    CLINIC_LIST = (By.CSS_SELECTOR, ".client-list")
    CLINIC_ROW = (By.CSS_SELECTOR, ".client-row")
    CLINIC_NAME = (By.CSS_SELECTOR, "span")
    CLINIC_STATS = (By.CSS_SELECTOR, ".clinic-review-stats")
    SELECTED_CLINIC = (By.CSS_SELECTOR, ".review-panel h3")
    REVIEW_PLACEHOLDER = (By.CSS_SELECTOR, ".review-panel .empty-state:not(.compact)")
    REVIEWS_EMPTY = (By.CSS_SELECTOR, ".review-panel .empty-state.compact")
    REVIEW_CARD = (By.CSS_SELECTOR, ".review-card")

    def __init__(self, driver, base_url, timeout=20):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(
            driver, timeout, ignored_exceptions=(StaleElementReferenceException,)
        )

    def open(self):
        self.driver.get(self.base_url + "/admin/clinics")
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

    def request_count(self, match, method=None):
        return len(
            [
                request
                for request in self.requests()
                if match in request
                and (method is None or request.startswith(method + " "))
            ]
        )

    def request_bodies(self, match):
        rows = self.driver.execute_script("return window.__uiTestBodies || [];")
        return [
            json.loads(row["body"])
            for row in rows
            if match in row["url"] and row["body"]
        ]

    def wait_until_loaded(self):
        self.wait.until(EC.presence_of_element_located(self.MAIN))
        self.wait.until(
            lambda d: d.find_elements(*self.APPLICATIONS_PANEL)
            and d.find_elements(*self.CLINIC_LIST)
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

    def panel_titles(self):
        return [
            element.text.strip()
            for element in self.driver.find_elements(*self.PANEL_TITLE)
        ]

    def errors(self):
        return [
            element.text.strip() for element in self.driver.find_elements(*self.ALERT)
        ]

    def wait_for_error(self, expected):
        self.wait.until(lambda d: expected in self.errors())
        return self

    def application_card(self, name):
        locator = (
            By.XPATH,
            "//article[contains(@class,'application-card')]"
            "[.//h3[normalize-space()='%s']]" % name,
        )
        return self.wait.until(EC.presence_of_element_located(locator))

    def applications(self):
        rows = []
        for card in self.driver.find_elements(*self.APPLICATION_CARD):
            details = card.find_elements(By.CSS_SELECTOR, ".item-header p")
            rows.append(
                {
                    "name": self._text(self.APPLICATION_NAME, card),
                    "location": details[0].text.strip() if details else "",
                    "contact": details[1].text.strip() if len(details) > 1 else "",
                    "status": self._text(self.APPLICATION_BADGE, card),
                    "submitted": self._text(self.APPLICATION_META, card),
                    "denial": self._text(self.APPLICATION_DENIAL, card),
                }
            )
        return rows

    def application(self, name):
        return next(
            row for row in self.applications() if row["name"] == name
        )

    def application_names(self):
        return [row["name"] for row in self.applications()]

    def applications_empty_text(self):
        panel = self.wait.until(
            EC.presence_of_element_located(self.APPLICATIONS_PANEL)
        )
        return self._text(self.EMPTY_STATE, panel)

    def application_status(self, name):
        return self._text(self.APPLICATION_BADGE, self.application_card(name))

    def application_denial(self, name):
        return self._text(self.APPLICATION_DENIAL, self.application_card(name))

    def wait_for_application_names(self, expected):
        self.wait.until(lambda d: self.application_names() == expected)
        return self

    def wait_for_application_status(self, name, expected):
        self.wait.until(lambda d: self.application_status(name) == expected)
        return self

    def approve_enabled(self, name):
        return self.application_card(name).find_element(
            *self.APPROVE_BUTTON
        ).is_enabled()

    def deny_enabled(self, name):
        return self.application_card(name).find_element(*self.DENY_BUTTON).is_enabled()

    def approve(self, name):
        self._click(self.application_card(name).find_element(*self.APPROVE_BUTTON))
        return self

    def deny(self, name):
        self._click(self.application_card(name).find_element(*self.DENY_BUTTON))
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

    def clinic_row(self, name):
        locator = (
            By.XPATH,
            "//button[contains(@class,'client-row')]"
            "[span[normalize-space()='%s']]" % name,
        )
        return self.wait.until(EC.presence_of_element_located(locator))

    def clinic_names(self):
        return [
            self._text(self.CLINIC_NAME, row)
            for row in self.driver.find_elements(*self.CLINIC_ROW)
        ]

    def clinic_location(self, name):
        return self.clinic_row(name).find_elements(By.CSS_SELECTOR, "small")[0].text.strip()

    def clinic_stats(self, name):
        return self._text(self.CLINIC_STATS, self.clinic_row(name))

    def wait_for_clinic_names(self, expected):
        self.wait.until(lambda d: self.clinic_names() == expected)
        return self

    def wait_for_clinic_stats(self, name, expected):
        self.wait.until(lambda d: self.clinic_stats(name) == expected)
        return self

    def select_clinic(self, name):
        self._click(self.clinic_row(name))
        return self

    def active_clinic_names(self):
        return [
            self._text(self.CLINIC_NAME, row)
            for row in self.driver.find_elements(*self.CLINIC_ROW)
            if "active" in row.get_attribute("class").split()
        ]

    def selected_clinic_name(self):
        return self._text(self.SELECTED_CLINIC)

    def review_panel_placeholder(self):
        return self._text(self.REVIEW_PLACEHOLDER)

    def reviews(self):
        rows = []
        for card in self.driver.find_elements(*self.REVIEW_CARD):
            rows.append(
                {
                    "reviewer": card.find_element(
                        By.CSS_SELECTOR, ".item-header strong"
                    ).text.strip(),
                    "username": card.find_element(
                        By.CSS_SELECTOR, ".item-header small"
                    ).text.strip(),
                    "rating": card.find_element(
                        By.CSS_SELECTOR, ".rating"
                    ).text.strip(),
                    "comment": card.find_element(By.XPATH, "./p").text.strip(),
                    "date": card.find_element(By.XPATH, "./small").text.strip(),
                }
            )
        return rows

    def reviews_empty_text(self):
        return self._text(self.REVIEWS_EMPTY)

    def wait_for_review_count(self, expected):
        self.wait.until(lambda d: len(d.find_elements(*self.REVIEW_CARD)) == expected)
        return self

    def wait_for_reviews_empty(self):
        self.wait.until(lambda d: d.find_elements(*self.REVIEWS_EMPTY))
        return self
