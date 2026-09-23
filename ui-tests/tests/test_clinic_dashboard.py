from datetime import date, timedelta

import pytest

from pages.clinic_dashboard_page import (
    APPOINTMENTS_URL,
    ClinicDashboardPage,
    NOTIFICATIONS_URL,
    NO_SHOW_URL,
    UNAVAILABLE_URL,
    route,
    stub_appointment,
    stub_blocked_slot,
    stub_notification,
)
from pages.login_page import LoginPage

CLINIC_SUBTITLE = "UI Test Clinic - Skopje, Testna 1"
ACCESS_ERROR = "This dashboard is only available for clinic accounts."
EMPTY_STATE_TITLE = "Clinic login required"
NO_APPOINTMENTS_TEXT = "No appointments on this date."
NO_NOTIFICATIONS_TEXT = "No notifications yet."
BOOKED_SLOT_ERROR = "Cannot block a slot that already has an appointment"
ALREADY_BLOCKED_ERROR = "This slot is already marked unavailable"
PAST_SLOT_ERROR = "Unavailable slot must be a future 30-minute slot between 09:00 and 17:00"
UNBLOCK_ERROR = "Unavailable slot not found"
OTHER_CLINIC_ERROR = "You can only update appointments for your own clinic"
NOTIFICATIONS_ERROR_PREFIX = "Failed to fetch notifications: 500"
STUB_PET = "StubPet"
SLOT_COUNT = 16


@pytest.fixture
def clinic_page(driver, base_url):
    return ClinicDashboardPage(driver, base_url)


@pytest.fixture
def sign_in(driver, base_url, accounts):
    def run(name):
        account = accounts[name]
        page = LoginPage(driver, base_url)
        page.open().login_as(account.username, account.password)
        page.wait_for_redirect_to("/")

    return run


@pytest.fixture
def schedule_date(clinic_api):
    value = (date.today() + timedelta(days=21)).isoformat()
    clinic_api.clear(value)
    yield value
    clinic_api.clear(value)


@pytest.fixture
def future_date():
    return (date.today() + timedelta(days=30)).isoformat()


@pytest.fixture
def past_date():
    return (date.today() - timedelta(days=7)).isoformat()


def test_guest_is_redirected_to_login(clinic_page):
    clinic_page.open().wait_for_login_redirect()

    assert not clinic_page.has_dashboard()


def test_non_clinic_user_sees_access_error(clinic_page, sign_in):
    sign_in("client")
    clinic_page.open().wait_for_error(ACCESS_ERROR)

    assert clinic_page.empty_state_title() == EMPTY_STATE_TITLE
    assert not clinic_page.has_dashboard()


def test_clinic_user_sees_dashboard(clinic_page, sign_in):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()

    assert clinic_page.errors() == []
    assert clinic_page.clinic_subtitle() == CLINIC_SUBTITLE
    assert clinic_page.heading() == "Slots for %s" % clinic_page.selected_date()


def test_day_without_appointments_or_blocks_is_fully_available(
    clinic_page, sign_in, schedule_date
):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded().select_date(schedule_date)

    assert clinic_page.slot_labels()[0] == "09:00"
    assert clinic_page.slot_labels()[-1] == "16:30"
    assert clinic_page.slot_kinds() == ["available"] * SLOT_COUNT
    assert clinic_page.slot_statuses() == ["Available"] * SLOT_COUNT
    assert clinic_page.summary() == {
        "Appointments": 0,
        "Available": SLOT_COUNT,
        "Not working": 0,
    }
    assert clinic_page.appointments_empty_text() == NO_APPOINTMENTS_TEXT


def test_booked_slot_is_shown_with_pet_name(clinic_page, sign_in, future_date):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()
    clinic_page.install_routes(
        [
            route(UNAVAILABLE_URL, [], method="GET"),
            route(APPOINTMENTS_URL, [stub_appointment(future_date, "10:00")]),
        ]
    )
    clinic_page.select_date(future_date).wait_for_slot_kind("10:00", "booked")

    assert clinic_page.slot_status("10:00") == "Booked"
    assert clinic_page.slot_detail("10:00") == STUB_PET
    assert not clinic_page.has_block_button("10:00")
    assert clinic_page.slot_kind("09:00") == "available"
    assert clinic_page.summary() == {
        "Appointments": 1,
        "Available": SLOT_COUNT - 1,
        "Not working": 0,
    }
    assert clinic_page.appointments() == [
        {
            "time": "10:00",
            "pet": STUB_PET,
            "meta": "Dog with Stub Owner",
            "status": "CONFIRMED",
        }
    ]


def test_blocked_slot_is_shown_with_reason(clinic_page, sign_in, future_date):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()
    clinic_page.install_routes(
        [
            route(
                UNAVAILABLE_URL,
                [stub_blocked_slot(future_date, "11:00")],
                method="GET",
            ),
            route(APPOINTMENTS_URL, []),
        ]
    )
    clinic_page.select_date(future_date).wait_for_slot_kind("11:00", "unavailable")

    assert clinic_page.slot_status("11:00") == "Not working"
    assert clinic_page.slot_detail("11:00") == "Staff training"
    assert clinic_page.has_unblock_button("11:00")
    assert not clinic_page.has_block_button("11:00")
    assert clinic_page.summary() == {
        "Appointments": 0,
        "Available": SLOT_COUNT - 1,
        "Not working": 1,
    }


def test_past_day_has_no_actionable_slots(clinic_page, sign_in, past_date):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded().select_date(past_date)

    assert clinic_page.slot_kinds() == ["past"] * SLOT_COUNT
    assert clinic_page.slot_statuses() == ["Past"] * SLOT_COUNT
    assert not clinic_page.has_block_button("09:00")
    assert not clinic_page.has_unblock_button("16:30")
    assert clinic_page.summary() == {
        "Appointments": 0,
        "Available": 0,
        "Not working": 0,
    }
    assert clinic_page.appointments_empty_text() == NO_APPOINTMENTS_TEXT


def test_block_slot_marks_it_not_working(
    clinic_page, sign_in, clinic_api, schedule_date
):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded().select_date(schedule_date)

    assert clinic_page.has_block_button("09:00")

    clinic_page.block_slot("09:00").accept_dialog("Dentist visit")
    clinic_page.wait_for_slot_kind("09:00", "unavailable")

    assert clinic_page.slot_status("09:00") == "Not working"
    assert clinic_page.slot_detail("09:00") == "Dentist visit"
    assert clinic_page.has_unblock_button("09:00")
    assert clinic_page.errors() == []
    assert "09:00" in clinic_api.slots(schedule_date)


def test_block_booked_slot_shows_error(clinic_page, sign_in, future_date):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()
    clinic_page.install_routes(
        [
            route(UNAVAILABLE_URL, [], method="GET"),
            route(
                UNAVAILABLE_URL,
                {"error": BOOKED_SLOT_ERROR},
                400,
                method="POST",
            ),
            route(APPOINTMENTS_URL, []),
        ]
    )
    clinic_page.select_date(future_date)
    clinic_page.block_slot("09:00").accept_dialog("Lunch")
    clinic_page.wait_for_error(BOOKED_SLOT_ERROR)

    assert clinic_page.slot_kind("09:00") == "available"


def test_block_already_blocked_slot_shows_error(
    clinic_page, sign_in, clinic_api, schedule_date
):
    clinic_api.block(schedule_date, "10:00", "Staff training")
    sign_in("clinic")
    clinic_page.open().wait_until_loaded().select_date(schedule_date)

    assert clinic_page.slot_kind("10:00") == "unavailable"

    clinic_page.install_routes([route(UNAVAILABLE_URL, [], method="GET")])
    clinic_page.refresh_schedule().wait_for_slot_kind("10:00", "available")
    clinic_page.block_slot("10:00").accept_dialog("Lunch")
    clinic_page.wait_for_error(ALREADY_BLOCKED_ERROR)

    assert clinic_page.slot_kind("10:00") == "available"
    assert sorted(clinic_api.slots(schedule_date)) == ["10:00"]


def test_block_past_slot_shows_error(clinic_page, sign_in, future_date):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()
    clinic_page.install_routes(
        [
            route(UNAVAILABLE_URL, [], method="GET"),
            route(UNAVAILABLE_URL, {"error": PAST_SLOT_ERROR}, 400, method="POST"),
            route(APPOINTMENTS_URL, []),
        ]
    )
    clinic_page.select_date(future_date)
    clinic_page.block_slot("09:00").accept_dialog("Closed")
    clinic_page.wait_for_error(PAST_SLOT_ERROR)

    assert clinic_page.slot_kind("09:00") == "available"


def test_unblock_slot_makes_it_available(
    clinic_page, sign_in, clinic_api, schedule_date
):
    clinic_api.block(schedule_date, "12:00", "Staff training")
    sign_in("clinic")
    clinic_page.open().wait_until_loaded().select_date(schedule_date)

    assert clinic_page.slot_status("12:00") == "Not working"

    clinic_page.unblock_slot("12:00").wait_for_slot_kind("12:00", "available")

    assert clinic_page.slot_status("12:00") == "Available"
    assert clinic_page.has_block_button("12:00")
    assert clinic_page.errors() == []
    assert clinic_api.slots(schedule_date) == {}


def test_unblock_failure_shows_error(clinic_page, sign_in, future_date):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()
    clinic_page.install_routes(
        [
            route(
                UNAVAILABLE_URL,
                [stub_blocked_slot(future_date, "13:00")],
                method="GET",
            ),
            route(UNAVAILABLE_URL, {"error": UNBLOCK_ERROR}, 400, method="DELETE"),
            route(APPOINTMENTS_URL, []),
        ]
    )
    clinic_page.select_date(future_date).wait_for_slot_kind("13:00", "unavailable")
    clinic_page.unblock_slot("13:00")
    clinic_page.wait_for_error(UNBLOCK_ERROR)

    assert clinic_page.slot_status("13:00") == "Not working"
    assert clinic_page.has_unblock_button("13:00")


def test_past_appointment_can_be_marked_no_show(clinic_page, sign_in, past_date):
    appointment = stub_appointment(past_date, "09:00")
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()
    clinic_page.install_routes(
        [
            route(UNAVAILABLE_URL, [], method="GET"),
            route(APPOINTMENTS_URL, [appointment]),
            route(
                NO_SHOW_URL,
                dict(appointment, status="NO_SHOW"),
                method="PATCH",
            ),
        ]
    )
    clinic_page.select_date(past_date)

    assert clinic_page.has_no_show_button(STUB_PET)

    clinic_page.mark_no_show(STUB_PET).accept_dialog()
    clinic_page.wait_for_appointment_status(STUB_PET, "NO_SHOW")

    assert not clinic_page.has_no_show_button(STUB_PET)
    assert clinic_page.errors() == []


def test_future_appointment_cannot_be_marked_no_show(
    clinic_page, sign_in, future_date
):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()
    clinic_page.install_routes(
        [
            route(UNAVAILABLE_URL, [], method="GET"),
            route(APPOINTMENTS_URL, [stub_appointment(future_date, "14:00")]),
        ]
    )
    clinic_page.select_date(future_date).wait_for_slot_kind("14:00", "booked")

    assert clinic_page.appointment_status(STUB_PET) == "CONFIRMED"
    assert not clinic_page.has_no_show_button(STUB_PET)


def test_cancelled_appointment_cannot_be_marked_no_show(
    clinic_page, sign_in, past_date
):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()
    clinic_page.install_routes(
        [
            route(UNAVAILABLE_URL, [], method="GET"),
            route(
                APPOINTMENTS_URL,
                [stub_appointment(past_date, "09:30", status="CANCELLED")],
            ),
        ]
    )
    clinic_page.select_date(past_date)

    assert clinic_page.appointment_status(STUB_PET) == "CANCELLED"
    assert not clinic_page.has_no_show_button(STUB_PET)
    assert clinic_page.slot_kind("09:30") == "past"


def test_dismissed_confirm_keeps_appointment_status(clinic_page, sign_in, past_date):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()
    clinic_page.install_routes(
        [
            route(UNAVAILABLE_URL, [], method="GET"),
            route(APPOINTMENTS_URL, [stub_appointment(past_date, "10:00")]),
        ]
    )
    clinic_page.select_date(past_date)
    clinic_page.mark_no_show(STUB_PET).dismiss_dialog()

    assert clinic_page.appointment_status(STUB_PET) == "CONFIRMED"
    assert clinic_page.has_no_show_button(STUB_PET)
    assert not [
        request for request in clinic_page.requests() if NO_SHOW_URL in request
    ]


def test_other_clinic_appointment_no_show_is_rejected(
    clinic_page, sign_in, past_date
):
    sign_in("clinic")
    clinic_page.open().wait_until_loaded()
    clinic_page.install_routes(
        [
            route(UNAVAILABLE_URL, [], method="GET"),
            route(
                APPOINTMENTS_URL,
                [stub_appointment(past_date, "11:00", clinicId=90999)],
            ),
            route(NO_SHOW_URL, {"error": OTHER_CLINIC_ERROR}, 400, method="PATCH"),
        ]
    )
    clinic_page.select_date(past_date)
    clinic_page.mark_no_show(STUB_PET).accept_dialog()
    clinic_page.wait_for_error(OTHER_CLINIC_ERROR)

    assert clinic_page.appointment_status(STUB_PET) == "CONFIRMED"
    assert clinic_page.has_no_show_button(STUB_PET)


def test_notifications_are_listed(clinic_page, sign_in):
    messages = ["UI test notification %s" % index for index in range(1, 6)]
    sign_in("clinic")
    clinic_page.install_routes(
        [
            route(
                NOTIFICATIONS_URL,
                [
                    stub_notification(index, "UI test notification %s" % index)
                    for index in range(1, 7)
                ],
            )
        ]
    )
    clinic_page.open_from_nav().wait_until_loaded()
    clinic_page.wait_for_notification_messages(messages)

    assert clinic_page.notifications()[0]["date"].startswith("Mar 4")
    assert clinic_page.errors() == []


def test_empty_notifications_show_placeholder(clinic_page, sign_in):
    sign_in("clinic")
    clinic_page.install_routes([route(NOTIFICATIONS_URL, [])])
    clinic_page.open_from_nav().wait_until_loaded()

    assert clinic_page.notifications() == []
    assert clinic_page.notifications_empty_text() == NO_NOTIFICATIONS_TEXT
    assert clinic_page.errors() == []


def test_notifications_load_error_is_shown(clinic_page, sign_in):
    sign_in("clinic")
    clinic_page.install_routes(
        [route(NOTIFICATIONS_URL, {"error": "Simulated failure"}, 500)]
    )
    clinic_page.open_from_nav().wait_until_loaded()
    clinic_page.wait_for_error_starting_with(NOTIFICATIONS_ERROR_PREFIX)

    assert clinic_page.notifications() == []
    assert clinic_page.notifications_empty_text() == NO_NOTIFICATIONS_TEXT
