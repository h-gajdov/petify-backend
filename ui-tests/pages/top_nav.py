import json

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .listings_page import HIDE_DEV_OVERLAY, IN_VIEWPORT
from .login_page import STORAGE_KEY

MOBILE_WIDTH = 400
MOBILE_HEIGHT = 900


class TopNav:
    NAV = (By.CSS_SELECTOR, "nav.navbar")
    BRAND = (By.CSS_SELECTOR, "nav .navbar-brand")
    TOGGLER = (By.CSS_SELECTOR, "nav .navbar-toggler")
    COLLAPSE = (By.ID, "petifyNavbar")
    LINK = (By.CSS_SELECTOR, "#petifyNavbar a")
    LOGOUT = (By.XPATH, "//nav//button[normalize-space()='Log out']")

    def __init__(self, driver, base_url, timeout=15):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(
            driver, timeout, ignored_exceptions=(StaleElementReferenceException,)
        )

    def open(self, path="/"):
        self.driver.get(self.base_url + path)
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        self.wait.until(EC.presence_of_element_located(self.NAV))
        return self

    def refresh(self):
        self.driver.refresh()
        self.driver.execute_script(HIDE_DEV_OVERLAY)
        self.wait.until(EC.presence_of_element_located(self.NAV))
        return self

    def use_mobile_window(self):
        if hasattr(self.driver, "execute_cdp_cmd"):
            self.driver.execute_cdp_cmd(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": MOBILE_WIDTH,
                    "height": MOBILE_HEIGHT,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                },
            )
        else:
            self.driver.set_window_size(MOBILE_WIDTH, MOBILE_HEIGHT)
        return self

    def _click(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )
        self.wait.until(lambda d: d.execute_script(IN_VIEWPORT, element))
        element.click()
        return self

    def links(self):
        return [
            {
                "text": " ".join(element.text.split()),
                "href": element.get_attribute("href").replace(self.base_url, ""),
            }
            for element in self.driver.find_elements(*self.LINK)
        ]

    def link_texts(self):
        return [link["text"] for link in self.links()]

    def link_targets(self):
        return [link["href"] for link in self.links()]

    def wait_for_link_texts(self, expected):
        self.wait.until(lambda d: self.link_texts() == expected)
        return self

    def has_logout(self):
        return len(self.driver.find_elements(*self.LOGOUT)) > 0

    def logout(self):
        self._click(self.driver.find_element(*self.LOGOUT))
        return self

    def brand_text(self):
        return self.driver.find_element(*self.BRAND).text.strip()

    def click_brand(self):
        self._click(self.driver.find_element(*self.BRAND))
        return self

    def click_link(self, text):
        locator = (
            By.XPATH,
            "//div[@id='petifyNavbar']//a[normalize-space()='%s']" % text,
        )
        self._click(self.driver.find_element(*locator))
        return self

    def wait_for_path(self, path):
        target = (self.base_url + path).rstrip("/")
        self.wait.until(lambda d: d.current_url.rstrip("/") == target)
        return self

    def stored_user(self):
        raw = self.driver.execute_script(
            "return window.localStorage.getItem(arguments[0]);", STORAGE_KEY
        )
        return json.loads(raw) if raw else None

    def is_toggler_visible(self):
        return self.driver.find_element(*self.TOGGLER).is_displayed()

    def toggle_menu(self):
        self._click(self.driver.find_element(*self.TOGGLER))
        return self

    def is_menu_expanded(self):
        return (
            self.driver.find_element(*self.TOGGLER).get_attribute("aria-expanded")
            == "true"
        )

    def is_menu_visible(self):
        return self.driver.find_element(*self.COLLAPSE).is_displayed()

    def wait_for_menu_visible(self, expected):
        self.wait.until(lambda d: self.is_menu_visible() == expected)
        return self
