import json

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

STORAGE_KEY = "petify.auth.user"


class LoginPage:
    USERNAME = (By.ID, "username")
    PASSWORD = (By.ID, "password")
    SUBMIT = (By.CSS_SELECTOR, "form button[type='submit']")
    ERROR = (By.CSS_SELECTOR, ".alert.alert-danger[role='alert']")

    def __init__(self, driver, base_url, timeout=15):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)

    def open(self, query=""):
        self.driver.get("%s/login%s" % (self.base_url, query))
        self.wait.until(EC.visibility_of_element_located(self.USERNAME))
        return self

    def fill(self, identifier, password):
        username = self.driver.find_element(*self.USERNAME)
        username.clear()
        username.send_keys(identifier)

        secret = self.driver.find_element(*self.PASSWORD)
        secret.clear()
        secret.send_keys(password)
        return self

    def submit(self):
        self.driver.find_element(*self.SUBMIT).click()
        return self

    def login_as(self, identifier, password):
        return self.fill(identifier, password).submit()

    def wait_for_redirect_to(self, path="/"):
        target = ("%s%s" % (self.base_url, path)).rstrip("/")
        self.wait.until(lambda d: d.current_url.rstrip("/") == target)
        return self

    def wait_until_settled(self, timeout=6):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: self.has_error() or "/login" not in d.current_url
            )
        except TimeoutException:
            pass
        return self

    def error_message(self):
        element = self.wait.until(EC.visibility_of_element_located(self.ERROR))
        return element.text.replace("Oops.", "").strip()

    def has_error(self):
        return len(self.driver.find_elements(*self.ERROR)) > 0

    def stored_user(self):
        raw = self.driver.execute_script(
            "return window.localStorage.getItem(arguments[0]);", STORAGE_KEY
        )
        return json.loads(raw) if raw else None

    def is_on_login(self):
        return "/login" in self.driver.current_url

    def is_value_missing(self, locator):
        element = self.driver.find_element(*locator)
        return self.driver.execute_script(
            "return arguments[0].validity.valueMissing;", element
        )

    def has_link(self, href):
        selector = "a[href='%s']" % href
        return len(self.driver.find_elements(By.CSS_SELECTOR, selector)) > 0
