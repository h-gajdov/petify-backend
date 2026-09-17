import os
from dataclasses import dataclass

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions


@dataclass(frozen=True)
class Account:
    username: str
    email: str
    password: str


def _env(name, default):
    return os.environ.get(name, default)


def pytest_addoption(parser):
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Show the browser window while the tests run.",
    )


def _account(prefix, username, email):
    return Account(
        username=_env("PETIFY_%s_USERNAME" % prefix, username),
        email=_env("PETIFY_%s_EMAIL" % prefix, email),
        password=_env(
            "PETIFY_%s_PASSWORD" % prefix,
            _env("PETIFY_DEFAULT_PASSWORD", "TestPass123!"),
        ),
    )


@pytest.fixture(scope="session")
def base_url():
    return _env("PETIFY_BASE_URL", "http://localhost:5173").rstrip("/")


@pytest.fixture(scope="session")
def accounts():
    return {
        "client": _account("CLIENT", "ui.client", "ui.client@petify.test"),
        "admin": _account("ADMIN", "ui.admin", "ui.admin@petify.test"),
        "clinic": _account("CLINIC", "ui.clinic", "ui.clinic@petify.test"),
        "blocked": _account("BLOCKED", "ui.blocked", "ui.blocked@petify.test"),
    }


@pytest.fixture(scope="session")
def blocked_reason():
    return _env("PETIFY_BLOCKED_REASON", "Repeated policy violations")


@pytest.fixture
def driver(base_url, request):
    browser = _env("PETIFY_BROWSER", "chrome").lower()
    headless = _env("PETIFY_HEADLESS", "1") != "0"
    if request.config.getoption("--headed"):
        headless = False

    if browser == "firefox":
        options = FirefoxOptions()
        if headless:
            options.add_argument("-headless")
        instance = webdriver.Firefox(options=options)
    else:
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1400,1000")
        instance = webdriver.Chrome(options=options)

    instance.set_page_load_timeout(30)
    instance.get(base_url + "/")
    instance.execute_script("window.localStorage.clear();")

    yield instance

    instance.quit()
