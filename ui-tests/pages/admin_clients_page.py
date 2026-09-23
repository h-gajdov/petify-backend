import json

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .admin_clinics_page import ROUTES_STUB
from .listings_page import HIDE_DEV_OVERLAY, IN_VIEWPORT

USERS_URL = "/api/users/admin/all"
REVIEWS_BY_URL = "/api/reviews/by/"
REVIEWS_URL = "/api/reviews/"
BLOCK_URL = "/block"


def route(match, body=None, status=200, method=None):
    return {"match": match, "status": status, "body": body, "method": method}


def stub_user(user_id, first_name, last_name, **overrides):
    user = {
        "userId": user_id,
        "username": "%s.%s" % (first_name.lower(), last_name.lower()),
        "email": "%s.%s@petify.test" % (first_name.lower(), last_name.lower()),
        "firstName": first_name,
        "lastName": last_name,
        "createdAt": "2026-01-10T10:00:00",
        "userType": "CLIENT",
        "isBlocked": False,
        "blockedReason": None,
        "verified": False,
    }
    user.update(overrides)
    return user


def stub_review(review_id, **overrides):
    review = {
        "reviewId": review_id,
        "reviewerId": 91901,
        "reviewerName": "Stub Reviewer",
        "reviewerUsername": "stub.reviewer",
        "rating": 5,
        "comment": "Friendly and honest.",
        "createdAt": "2026-02-20T09:15:00",
    }
    review.update(overrides)
    return review


class AdminClientsPage:
    MAIN = (By.CSS_SELECTOR, "main.admin-clients")
    PAGE_TITLE = (By.CSS_SELECTOR, ".page-title")
    PANEL_TITLE = (By.CSS_SELECTOR, ".panel-header h2")
    ALERT = (By.CSS_SELECTOR, ".moderation-body .alert-danger")
    LOADING = (By.CSS_SELECTOR, ".moderation-body .alert-info")
    NAV_LINK = (By.CSS_SELECTOR, "a[href='/admin/clients']")
    SEARCH = (By.CSS_SELECTOR, "input.search-input")
    CLIENT_LIST = (By.CSS_SELECTOR, ".client-list")
    CLIENT_ROW = (By.CSS_SELECTOR, ".client-row")
    LIST_EMPTY = (By.CSS_SELECTOR, ".client-list .empty-state")
    PLACEHOLDER = (By.CSS_SELECTOR, ".review-panel > .empty-state")
    SELECTED_NAME = (By.CSS_SELECTOR, ".review-panel > .item-header h3")
    SELECTED_DETAILS = (By.CSS_SELECTOR, ".review-panel > .item-header p")
    BLOCK_BUTTON = (By.CSS_SELECTOR, ".review-panel > .item-header .btn-outline-danger")
    UNBLOCK_BUTTON = (By.CSS_SELECTOR, ".review-panel > .item-header .btn-success")
    REVIEW_COLUMN = (By.CSS_SELECTOR, ".review-columns > section")

    def __init__(self, driver, base_url, timeout=20):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(
            driver, timeout, ignored_exceptions=(StaleElementReferenceException,)
        )

    def open(self):
        self.driver.get(self.base_url + "/admin/clients")
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
            lambda d: d.find_elements(*self.CLIENT_LIST)
            and not d.find_elements(*self.LOADING)
            and (d.find_elements(*self.CLIENT_ROW) or d.find_elements(*self.LIST_EMPTY))
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

    def errors(self):
        return [
            element.text.strip() for element in self.driver.find_elements(*self.ALERT)
        ]

    def wait_for_error(self, expected):
        self.wait.until(lambda d: expected in self.errors())
        return self

    def search(self, text):
        field = self.driver.find_element(*self.SEARCH)
        field.clear()
        if text:
            field.send_keys(text)
        return self

    def clear_search(self):
        field = self.driver.find_element(*self.SEARCH)
        self.driver.execute_script(
            "arguments[0].value = '';"
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
            field,
        )
        return self

    def search_value(self):
        return self.driver.find_element(*self.SEARCH).get_attribute("value")

    def client_rows(self):
        rows = []
        for row in self.driver.find_elements(*self.CLIENT_ROW):
            smalls = row.find_elements(By.CSS_SELECTOR, "small")
            blocked = row.find_elements(By.CSS_SELECTOR, "small.blocked")
            rows.append(
                {
                    "name": row.find_element(By.CSS_SELECTOR, "span").text.strip(),
                    "handle": smalls[0].text.strip() if smalls else "",
                    "stats": self._text((By.CSS_SELECTOR, "small.review-stats"), row),
                    "blocked": blocked[0].text.strip() if blocked else "",
                }
            )
        return rows

    def client_names(self):
        return [row["name"] for row in self.client_rows()]

    def client_row_data(self, name):
        return next(row for row in self.client_rows() if row["name"] == name)

    def wait_for_client_names(self, expected):
        self.wait.until(lambda d: self.client_names() == expected)
        return self

    def wait_for_client_stats(self, name, expected):
        self.wait.until(lambda d: self.client_row_data(name)["stats"] == expected)
        return self

    def wait_for_client_blocked(self, name, expected):
        self.wait.until(lambda d: self.client_row_data(name)["blocked"] == expected)
        return self

    def list_empty_text(self):
        return self._text(self.LIST_EMPTY)

    def client_row(self, name):
        locator = (
            By.XPATH,
            "//button[contains(@class,'client-row')][span[normalize-space()='%s']]"
            % name,
        )
        return self.wait.until(EC.presence_of_element_located(locator))

    def select_client(self, name):
        self._click(self.client_row(name))
        self.wait.until(lambda d: self.selected_name() == name)
        return self

    def active_client_names(self):
        return [
            row.find_element(By.CSS_SELECTOR, "span").text.strip()
            for row in self.driver.find_elements(*self.CLIENT_ROW)
            if "active" in row.get_attribute("class").split()
        ]

    def placeholder_text(self):
        return self._text(self.PLACEHOLDER)

    def selected_name(self):
        return self._text(self.SELECTED_NAME)

    def selected_details(self):
        return self._text(self.SELECTED_DETAILS)

    def has_block_button(self):
        return len(self.driver.find_elements(*self.BLOCK_BUTTON)) > 0

    def has_unblock_button(self):
        return len(self.driver.find_elements(*self.UNBLOCK_BUTTON)) > 0

    def block(self):
        self._click(self.driver.find_element(*self.BLOCK_BUTTON))
        return self

    def unblock(self):
        self._click(self.driver.find_element(*self.UNBLOCK_BUTTON))
        return self

    def wait_for_unblock_button(self):
        self.wait.until(EC.presence_of_element_located(self.UNBLOCK_BUTTON))
        return self

    def wait_for_block_button(self):
        self.wait.until(EC.presence_of_element_located(self.BLOCK_BUTTON))
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

    def _column(self, index):
        return self.driver.find_elements(*self.REVIEW_COLUMN)[index]

    def _column_reviews(self, index):
        rows = []
        for card in self._column(index).find_elements(By.CSS_SELECTOR, ".review-card"):
            rows.append(
                {
                    "rating": card.find_element(By.CSS_SELECTOR, ".rating").text.strip(),
                    "comment": card.find_element(By.CSS_SELECTOR, "p").text.strip(),
                    "meta": card.find_element(By.CSS_SELECTOR, "small").text.strip(),
                }
            )
        return rows

    def _column_empty_text(self, index):
        return self._text((By.CSS_SELECTOR, ".empty-state"), self._column(index))

    def column_titles(self):
        return [
            column.find_element(By.CSS_SELECTOR, "h4").text.strip()
            for column in self.driver.find_elements(*self.REVIEW_COLUMN)
        ]

    def reviews_for(self):
        return self._column_reviews(0)

    def reviews_by(self):
        return self._column_reviews(1)

    def reviews_for_empty_text(self):
        return self._column_empty_text(0)

    def reviews_by_empty_text(self):
        return self._column_empty_text(1)

    def wait_for_review_counts(self, received, left):
        self.wait.until(
            lambda d: len(d.find_elements(*self.REVIEW_COLUMN)) == 2
            and len(self.reviews_for()) == received
            and len(self.reviews_by()) == left
        )
        return self
