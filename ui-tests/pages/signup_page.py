import json

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .listings_page import DELAYED_ENDPOINT_STUB

STORAGE_KEY = "petify.auth.user"

HIDE_DEV_OVERLAY = """
const id = 'ui-test-hide-dev-overlay';
if (!document.getElementById(id)) {
  const style = document.createElement('style');
  style.id = id;
  style.textContent = '#__vue-devtools-container__ { display: none !important; }';
  document.head.appendChild(style);
}
"""

NO_USER_RESPONSE_STUB = """
const original = window.fetch;
window.fetch = function (input, init) {
  const url = typeof input === 'string' ? input : String(input.url);
  if (url.indexOf('/api/auth/signup') !== -1) {
    return Promise.resolve(
      new Response(JSON.stringify({ message: 'User registered successfully' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  }
  return original.apply(this, arguments);
};
"""

RECORD_SUCCESS_ALERT = """
window.__signupSuccessAlert = null;
const capture = function () {
  const el = document.querySelector('.alert.alert-success[role="alert"]');
  if (el && !window.__signupSuccessAlert) {
    window.__signupSuccessAlert = el.textContent.trim();
  }
};
capture();
new MutationObserver(capture).observe(document.body, {
  childList: true,
  subtree: true,
  characterData: true,
});
"""

REQUEST_COUNTER = """
const original = window.fetch;
window.__signupRequests = 0;
window.fetch = function (input, init) {
  const url = typeof input === 'string' ? input : String(input.url);
  if (url.indexOf('/api/auth/signup') !== -1) {
    window.__signupRequests += 1;
  }
  return original.apply(this, arguments);
};
"""


class SignupPage:
    USERNAME = (By.ID, "username")
    EMAIL = (By.ID, "email")
    FIRST_NAME = (By.ID, "firstName")
    LAST_NAME = (By.ID, "lastName")
    PASSWORD = (By.ID, "password")
    CONFIRM = (By.ID, "confirm")
    SUBMIT = (By.CSS_SELECTOR, "form button[type='submit']")
    ERROR = (By.CSS_SELECTOR, ".alert.alert-danger[role='alert']")
    SUCCESS = (By.CSS_SELECTOR, ".alert.alert-success[role='alert']")
    PASSWORD_TOGGLE = (By.CSS_SELECTOR, "form .btn-eye")
    NAV_PROFILE = (By.CSS_SELECTOR, "nav a[href='/profile']")
    NAV_LOGOUT = (By.XPATH, "//nav//button[normalize-space()='Log out']")
    NAV_LOGIN = (By.CSS_SELECTOR, "nav a[href='/login']")

    def __init__(self, driver, base_url, timeout=15):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)

    def open(self, query=""):
        self.driver.get("%s/signup%s" % (self.base_url, query))
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        self.wait.until(EC.visibility_of_element_located(self.USERNAME))
        return self

    def type_into(self, locator, value):
        element = self.driver.find_element(*locator)
        element.clear()
        element.send_keys(value)
        return self

    def fill(
        self,
        username="",
        email="",
        password="",
        confirm=None,
        first_name="Ui",
        last_name="Signup",
    ):
        self.type_into(self.USERNAME, username)
        self.type_into(self.EMAIL, email)
        self.type_into(self.FIRST_NAME, first_name)
        self.type_into(self.LAST_NAME, last_name)
        self.type_into(self.PASSWORD, password)
        self.type_into(self.CONFIRM, password if confirm is None else confirm)
        return self

    def fill_from(self, account, **overrides):
        values = {
            "username": account.username,
            "email": account.email,
            "password": account.password,
        }
        values.update(overrides)
        return self.fill(**values)

    def submit(self):
        button = self.driver.find_element(*self.SUBMIT)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", button
        )
        button.click()
        return self

    def register_as(self, account, **overrides):
        return self.fill_from(account, **overrides).submit()

    def stub_success_without_user(self):
        self.driver.execute_script(NO_USER_RESPONSE_STUB)
        return self

    def record_success_alert(self):
        self.driver.execute_script(RECORD_SUCCESS_ALERT)
        return self

    def recorded_success_alert(self):
        raw = self.driver.execute_script("return window.__signupSuccessAlert;")
        return raw.replace("Done.", "").strip() if raw else None

    def count_signup_requests(self):
        self.driver.execute_script(REQUEST_COUNTER)
        return self

    def signup_requests(self):
        return self.driver.execute_script("return window.__signupRequests || 0;")

    def wait_for_redirect_to(self, path="/"):
        target = ("%s%s" % (self.base_url, path)).rstrip("/")
        self.wait.until(lambda d: d.current_url.rstrip("/") == target)
        return self

    def wait_until_settled(self, timeout=6):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: self.has_error()
                or self.has_success()
                or "/signup" not in d.current_url
            )
        except TimeoutException:
            pass
        return self

    def error_message(self):
        element = self.wait.until(EC.presence_of_element_located(self.ERROR))
        text = element.get_attribute("textContent") or ""
        return text.replace("Oops.", "").strip()

    def has_error(self):
        return len(self.driver.find_elements(*self.ERROR)) > 0

    def has_success(self):
        return len(self.driver.find_elements(*self.SUCCESS)) > 0

    def stored_user(self):
        raw = self.driver.execute_script(
            "return window.localStorage.getItem(arguments[0]);", STORAGE_KEY
        )
        return json.loads(raw) if raw else None

    def is_on_signup(self):
        return "/signup" in self.driver.current_url

    def is_value_missing(self, locator):
        element = self.driver.find_element(*locator)
        return self.driver.execute_script(
            "return arguments[0].validity.valueMissing;", element
        )

    def is_type_mismatch(self, locator):
        element = self.driver.find_element(*locator)
        return self.driver.execute_script(
            "return arguments[0].validity.typeMismatch;", element
        )

    def is_field_valid(self, locator):
        element = self.driver.find_element(*locator)
        return self.driver.execute_script(
            "return arguments[0].validity.valid;", element
        )

    def toggle_password(self, index=0):
        toggles = self.driver.find_elements(*self.PASSWORD_TOGGLE)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", toggles[index]
        )
        toggles[index].click()
        return self

    def field_type(self, locator):
        return self.driver.find_element(*locator).get_attribute("type")

    def toggle_labels(self):
        return [
            element.get_attribute("aria-label")
            for element in self.driver.find_elements(*self.PASSWORD_TOGGLE)
        ]

    def delay_signup(self, delay_ms):
        self.driver.execute_script(DELAYED_ENDPOINT_STUB, "/api/auth/signup", delay_ms)
        return self

    def delayed_requests(self):
        return self.driver.execute_script("return window.__uiTestRequestCount || 0;")

    def press_enter(self):
        self.driver.find_element(*self.CONFIRM).send_keys(Keys.ENTER)
        return self

    def submit_label(self):
        return self.driver.find_element(*self.SUBMIT).text.strip()

    def is_submit_disabled(self):
        return not self.driver.find_element(*self.SUBMIT).is_enabled()

    def wait_for_submit_label(self, expected):
        self.wait.until(lambda d: self.submit_label() == expected)
        return self

    def nav_profile_text(self):
        elements = self.driver.find_elements(*self.NAV_PROFILE)
        return elements[0].text.strip() if elements else ""

    def has_nav_logout(self):
        return len(self.driver.find_elements(*self.NAV_LOGOUT)) > 0

    def has_nav_login(self):
        return len(self.driver.find_elements(*self.NAV_LOGIN)) > 0

    def wait_for_nav_profile(self):
        self.wait.until(EC.presence_of_element_located(self.NAV_PROFILE))
        return self

    def refresh(self):
        self.driver.refresh()
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        return self
