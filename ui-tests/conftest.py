import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from stack import managed_ui_stack
from video import ScreencastRecorder, combine, ffmpeg_available


@dataclass(frozen=True)
class Account:
    username: str
    email: str
    password: str


@dataclass(frozen=True)
class ClinicApi:
    clinic_id: int
    block: object
    unblock: object
    slots: object
    clear: object


@dataclass(frozen=True)
class FavoriteApi:
    add: object
    clear: object
    ids: object
    wait_for: object


@dataclass(frozen=True)
class ReviewApi:
    create: object
    reviews: object
    track: object


WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 1200


def _env(name, default):
    return os.environ.get(name, default)


def pytest_addoption(parser):
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Show the browser window while the tests run.",
    )
    parser.addoption(
        "--external-stack",
        action="store_true",
        default=False,
        help="Use PETIFY_BASE_URL and PETIFY_API_URL instead of starting a Testcontainers stack.",
    )
    parser.addoption(
        "--record-video",
        action="store_true",
        default=False,
        help="Record an mp4 of every test (Chrome only), plus all-tests.mp4 joining them in run order.",
    )
    parser.addoption(
        "--video-size",
        default="1920x1000",
        metavar="WIDTHxHEIGHT",
        help="Page size while recording, and the video resolution (default: 1920x1000).",
    )
    parser.addoption(
        "--video-dir",
        default="videos",
        help="Directory for --record-video output (default: videos).",
    )


def pytest_configure(config):
    config.recorded_videos = []
    if config.getoption("--record-video") and not ffmpeg_available():
        raise pytest.UsageError("--record-video needs ffmpeg on PATH")
    if not re.fullmatch(r"\d+x\d+", config.getoption("--video-size")):
        raise pytest.UsageError("--video-size must look like 1920x1080")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    setattr(item, "report_" + report.when, report)
    return report


def pytest_sessionfinish(session):
    if session.config.recorded_videos:
        combine(session.config.recorded_videos, _video_dir(session.config) / "all-tests.mp4")


def _video_dir(config):
    return config.rootpath / config.getoption("--video-dir")


def _outcome(item):
    report = getattr(item, "report_call", None) or getattr(item, "report_setup", None)
    return report.outcome if report else "unknown"


def _video_path(item):
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.nodeid.replace("tests/", "", 1).replace("::", "__"))
    return _video_dir(item.config) / ("%s.%s.mp4" % (name, _outcome(item)))


def _caption(item):
    return item.nodeid.replace("tests/", "", 1).replace("::", "  \u203a  ")


def _api(url, method="GET", payload=None, user_id=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("Content-Type", "application/json")
    if user_id is not None:
        request.add_header("X-User-Id", str(user_id))
    with urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else None


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
def app_urls(request):
    if request.config.getoption("--external-stack"):
        yield (
            _env("PETIFY_BASE_URL", "http://localhost:5173").rstrip("/"),
            _env("PETIFY_API_URL", "http://localhost:8081").rstrip("/"),
        )
    else:
        with managed_ui_stack() as urls:
            yield urls


@pytest.fixture(scope="session")
def base_url(app_urls):
    return app_urls[0]


@pytest.fixture(scope="session")
def api_url(app_urls):
    return app_urls[1]


@pytest.fixture(scope="session")
def accounts():
    return {
        "client": _account("CLIENT", "ui.client", "ui.client@petify.test"),
        "admin": _account("ADMIN", "ui.admin", "ui.admin@petify.test"),
        "clinic": _account("CLINIC", "ui.clinic", "ui.clinic@petify.test"),
        "blocked": _account("BLOCKED", "ui.blocked", "ui.blocked@petify.test"),
        "owner": _account("OWNER", "ui.owner", "ui.owner@petify.test"),
        "favorites": _account("FAVORITES", "ui.fav", "ui.fav@petify.test"),
        "recommended": _account("RECOMMENDED", "ui.recs", "ui.recs@petify.test"),
        "unrecommended": _account("UNRECOMMENDED", "ui.norecs", "ui.norecs@petify.test"),
    }


@pytest.fixture(scope="session")
def account_ids(api_url, accounts):
    resolved = {}

    def lookup(name):
        if name not in resolved:
            account = accounts[name]
            user = _api(
                api_url + "/api/auth/login",
                method="POST",
                payload={"username": account.username, "password": account.password},
            )
            resolved[name] = int(user["userId"])
        return resolved[name]

    return lookup


@pytest.fixture(scope="session")
def listing_ids(api_url):
    rows = _api(api_url + "/api/public/listings") or []
    return {
        row["animalName"]: int(row["listingId"])
        for row in rows
        if row.get("animalName")
    }


@pytest.fixture
def favorite_api(api_url, account_ids):
    user_id = account_ids("favorites")

    def ids():
        rows = _api(api_url + "/api/favorites", user_id=user_id) or []
        return {int(row["listingId"]) for row in rows}

    def add(listing_id):
        _api(
            "%s/api/favorites/%s" % (api_url, listing_id),
            method="POST",
            user_id=user_id,
        )

    def clear():
        for listing_id in ids():
            _api(
                "%s/api/favorites/%s" % (api_url, listing_id),
                method="DELETE",
                user_id=user_id,
            )

    def wait_for(expected, timeout=15):
        deadline = time.monotonic() + timeout
        current = ids()
        while current != expected and time.monotonic() < deadline:
            time.sleep(0.25)
            current = ids()
        return current

    clear()
    yield FavoriteApi(add=add, clear=clear, ids=ids, wait_for=wait_for)
    clear()


@pytest.fixture
def clinic_api(api_url, account_ids):
    user_id = account_ids("clinic")
    clinic = _api(api_url + "/api/clinics/my", user_id=user_id)

    def slots(date):
        rows = _api(
            "%s/api/appointments/my-clinic/unavailable-slots?date=%s" % (api_url, date),
            user_id=user_id,
        ) or []
        return {row["label"]: int(row["slotId"]) for row in rows}

    def block(date, label, reason="Seeded block"):
        return _api(
            api_url + "/api/appointments/my-clinic/unavailable-slots",
            method="POST",
            payload={"dateTime": "%sT%s" % (date, label), "reason": reason},
            user_id=user_id,
        )

    def unblock(slot_id):
        _api(
            "%s/api/appointments/my-clinic/unavailable-slots/%s" % (api_url, slot_id),
            method="DELETE",
            user_id=user_id,
        )

    def clear(date):
        for slot_id in slots(date).values():
            unblock(slot_id)

    return ClinicApi(
        clinic_id=int(clinic["clinicId"]),
        block=block,
        unblock=unblock,
        slots=slots,
        clear=clear,
    )


@pytest.fixture
def new_account():
    def make():
        unique = uuid.uuid4().hex[:12]
        return Account(
            username="ui.signup.%s" % unique,
            email="ui.signup.%s@petify.test" % unique,
            password=_env("PETIFY_DEFAULT_PASSWORD", "TestPass123!"),
        )

    return make


@pytest.fixture
def registered_account(api_url, new_account):
    def make():
        account = new_account()
        user = _api(
            api_url + "/api/auth/signup",
            method="POST",
            payload={
                "username": account.username,
                "email": account.email,
                "password": account.password,
                "firstName": "Ui",
                "lastName": "Registered",
            },
        )
        return account, int(user["userId"])

    return make


@pytest.fixture
def block_api(api_url, account_ids):
    admin_id = account_ids("admin")

    def run(user_id, blocked, reason=""):
        _api(
            "%s/api/users/admin/%s/block" % (api_url, user_id),
            method="PATCH",
            payload={"isBlocked": blocked, "blockedReason": reason},
            user_id=admin_id,
        )

    return run


@pytest.fixture
def review_api(api_url):
    tracked = set()

    def reviews(target_id):
        return _api("%s/api/reviews/%s" % (api_url, target_id)) or []

    def track(target_id, reviewer_id):
        tracked.add((target_id, reviewer_id))

    def create(target_id, reviewer_id, rating, comment=""):
        track(target_id, reviewer_id)
        return _api(
            "%s/api/reviews/%s" % (api_url, target_id),
            method="POST",
            payload={"rating": rating, "comment": comment},
            user_id=reviewer_id,
        )

    yield ReviewApi(create=create, reviews=reviews, track=track)

    for target_id, reviewer_id in tracked:
        for review in reviews(target_id):
            if int(review["reviewerId"]) == reviewer_id:
                _api(
                    "%s/api/reviews/%s" % (api_url, review["reviewId"]),
                    method="DELETE",
                    user_id=reviewer_id,
                )


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
        options.add_argument("--width=%s" % WINDOW_WIDTH)
        options.add_argument("--height=%s" % WINDOW_HEIGHT)
        instance = webdriver.Firefox(options=options)
    else:
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=%s,%s" % (WINDOW_WIDTH, WINDOW_HEIGHT))
        instance = webdriver.Chrome(options=options)

    instance.set_page_load_timeout(30)

    recorder = None
    if request.config.getoption("--record-video"):
        if browser == "firefox":
            pytest.fail("--record-video supports Chrome only; unset PETIFY_BROWSER=firefox")
        width, height = (int(value) for value in request.config.getoption("--video-size").split("x"))
        # The window includes browser UI, so grow it until the page itself matches the video.
        chrome_height = instance.execute_script("return window.outerHeight - window.innerHeight;")
        instance.set_window_size(width, height + chrome_height)
        recorder = ScreencastRecorder(instance, width, height)

    yield instance

    try:
        if recorder is not None:
            ended_at = recorder.stop(instance)
            output = _video_path(request.node)
            if recorder.save(output, ended_at, _caption(request.node), _outcome(request.node)):
                request.config.recorded_videos.append(output)
    finally:
        instance.quit()
