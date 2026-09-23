from datetime import date, timedelta

import pytest

from pages.login_page import LoginPage
from pages.profile_page import (
    CLINIC_REVIEWS_URL,
    HEALTH_RECORDS_URL,
    MY_APPOINTMENTS_URL,
    ProfilePage,
    REVIEWS_URL,
    route,
    stub_appointment,
    stub_clinic,
    stub_clinic_review,
    stub_health_record,
    stub_pet,
    stub_slot,
)

PETS = [stub_pet(94101, "Rex"), stub_pet(94102, "Milo", species="Cat")]
CLINICS = [
    stub_clinic(94501, "Stub Clinic"),
    stub_clinic(94502, "Second Clinic", city="Bitola", address="Main 2"),
]
SLOTS_URL = "/api/appointments/clinics/%s/available-slots"
CREATE_APPOINTMENT_URL = "/api/appointments"
NO_APPOINTMENTS_TEXT = "No appointments scheduled for this day."
NO_SLOTS_TEXT = "No available slots for this clinic on the selected date."
SLOT_TAKEN_ERROR = "Selected appointment slot is no longer available"
RATING_REQUIRED_ERROR = "Please select a rating"
DUPLICATE_CLINIC_REVIEW = "You have already reviewed this clinic"
HEALTH_TYPE_ERROR = "Please enter the health record type"
DUPLICATE_HEALTH_RECORD = "A health record already exists for this appointment"
TODAY = date.today()
FUTURE_DAY = TODAY + timedelta(days=10)
PAST_DAY = TODAY - timedelta(days=3)


def at(day, clock="10:00"):
    return "%sT%s:00" % (day.isoformat(), clock)


def shown_time(day, clock="10:00 AM"):
    return "%s %s, %s, %s" % (day.strftime("%b"), day.day, day.year, clock)


def slots(day, *labels):
    return [stub_slot(day.isoformat(), label) for label in labels]


def month_label(day):
    return day.strftime("%B %Y")


def shift_month(day, months):
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


FUTURE_APPOINTMENT = stub_appointment(94601, at(FUTURE_DAY))
DONE_APPOINTMENT = stub_appointment(94602, at(PAST_DAY), status="DONE")


@pytest.fixture
def profile_page(driver, base_url):
    return ProfilePage(driver, base_url)


@pytest.fixture
def sign_in(driver, base_url, accounts):
    def run(name):
        account = accounts[name]
        page = LoginPage(driver, base_url)
        page.open().login_as(account.username, account.password)
        page.wait_for_redirect_to("/")

    return run


@pytest.fixture
def appointments_tab(profile_page, sign_in, account_ids):
    def run(routes=(), appointments=()):
        sign_in("owner")
        profile_page.open_stubbed(
            account_ids("owner"),
            routes=routes,
            pets=PETS,
            clinics=CLINICS,
            appointments=appointments,
        )
        profile_page.select_tab("Appointments").wait_for_appointments_loaded()
        return profile_page

    return run


def test_calendar_moves_to_previous_month(appointments_tab):
    page = appointments_tab()

    assert page.calendar_title() == month_label(TODAY)

    page.calendar_prev().wait_for_calendar_title(month_label(shift_month(TODAY, -1)))
    page.calendar_prev().wait_for_calendar_title(month_label(shift_month(TODAY, -2)))


def test_calendar_moves_to_next_month(appointments_tab):
    page = appointments_tab()
    page.calendar_next().wait_for_calendar_title(month_label(shift_month(TODAY, 1)))

    assert page.day_title() == "Appointments for %s" % TODAY.isoformat()


def test_month_year_editor_applies_selection(appointments_tab):
    page = appointments_tab()
    page.open_month_editor().set_month_year(2, 2027).apply_month_year()
    page.wait_for_calendar_title("March 2027")

    assert not page.has_month_editor()


def test_month_year_editor_rejects_invalid_year(appointments_tab):
    page = appointments_tab()
    page.open_month_editor().set_month_year(0, 1800).apply_month_year()

    assert page.has_month_editor()

    page.cancel_month_year().wait_for_calendar_title(month_label(TODAY))

    assert not page.has_month_editor()


def test_selecting_day_with_appointments_lists_them(appointments_tab):
    page = appointments_tab(
        appointments=[dict(FUTURE_APPOINTMENT, notes="Bring vaccination card")]
    )

    assert "has-appointments" in page.day_classes(FUTURE_DAY)

    page.select_day(FUTURE_DAY)

    assert "is-selected" in page.day_classes(FUTURE_DAY)
    assert page.appointment_cards() == [
        {
            "pet": "StubPet (Dog)",
            "status": "CONFIRMED",
            "time": shown_time(FUTURE_DAY),
            "clinic": "Stub Clinic - Skopje Testna 1",
            "notes": "Bring vaccination card",
        }
    ]


def test_selecting_day_without_appointments_shows_empty_state(appointments_tab):
    empty_day = FUTURE_DAY + timedelta(days=1)
    page = appointments_tab(appointments=[FUTURE_APPOINTMENT])

    assert page.day_title() == "Appointments for %s" % TODAY.isoformat()

    page.select_day(empty_day)

    assert "has-appointments" not in page.day_classes(empty_day)
    assert page.appointment_cards() == []
    assert page.day_empty_text() == NO_APPOINTMENTS_TEXT


def test_booking_appointment_sends_request(appointments_tab):
    page = appointments_tab(
        routes=[
            route(
                SLOTS_URL % 94501,
                slots(FUTURE_DAY, "09:00", "09:30"),
                method="GET",
            ),
            route(CREATE_APPOINTMENT_URL, FUTURE_APPOINTMENT, 201, method="POST"),
        ]
    )
    page.fill_booking(pet_id=94101, clinic_id=94501, date=FUTURE_DAY.isoformat())
    page.choose_slot(at(FUTURE_DAY, "09:30")).type_booking_notes("First visit")
    page.submit_booking().wait_for_active_tab("My Pets")

    assert page.request_bodies(CREATE_APPOINTMENT_URL, "POST") == [
        {
            "clinicId": 94501,
            "animalId": 94101,
            "dateTime": at(FUTURE_DAY, "09:30"),
            "notes": "First visit",
        }
    ]
    assert page.request_count(MY_APPOINTMENTS_URL, "GET") == 2


def test_booking_requires_clinic(appointments_tab):
    page = appointments_tab()
    page.fill_booking(pet_id=94101, date=FUTURE_DAY.isoformat())

    assert not page.is_slot_enabled()
    assert page.slot_labels() == ["Choose a clinic first..."]

    page.submit_booking()

    assert page.validity(ProfilePage.APPOINTMENT_CLINIC, "valueMissing")
    assert page.request_count(CREATE_APPOINTMENT_URL, "POST") == 0


def test_booking_requires_pet(appointments_tab):
    page = appointments_tab(
        routes=[
            route(SLOTS_URL % 94501, slots(FUTURE_DAY, "09:00"), method="GET")
        ]
    )
    page.fill_booking(clinic_id=94501, date=FUTURE_DAY.isoformat())
    page.choose_slot(at(FUTURE_DAY, "09:00")).submit_booking()

    assert page.validity(ProfilePage.APPOINTMENT_PET, "valueMissing")
    assert page.request_count(CREATE_APPOINTMENT_URL, "POST") == 0


def test_booking_requires_date_and_slot(appointments_tab):
    page = appointments_tab()
    page.fill_booking(pet_id=94101, clinic_id=94501)

    assert not page.is_slot_enabled()
    assert page.slot_labels() == ["Choose a date first..."]

    page.submit_booking()

    assert page.validity(ProfilePage.APPOINTMENT_DATE, "valueMissing")
    assert page.validity(ProfilePage.APPOINTMENT_SLOT, "valueMissing")
    assert page.request_count(CREATE_APPOINTMENT_URL, "POST") == 0


def test_slots_reload_when_clinic_or_date_changes(appointments_tab):
    later_day = FUTURE_DAY + timedelta(days=1)
    page = appointments_tab(
        routes=[
            route(SLOTS_URL % 94501, slots(FUTURE_DAY, "09:00"), method="GET"),
            route(
                SLOTS_URL % 94502,
                slots(FUTURE_DAY, "11:00", "11:30"),
                method="GET",
            ),
        ]
    )
    page.fill_booking(clinic_id=94501, date=FUTURE_DAY.isoformat())
    page.wait_for_slot_labels(["Choose a time slot...", "09:00"])
    page.fill_booking(clinic_id=94502)
    page.wait_for_slot_labels(["Choose a time slot...", "11:00", "11:30"])
    page.fill_booking(date=later_day.isoformat()).wait_until_settled()

    assert [
        request.split("?")[1]
        for request in page.requests()
        if "available-slots" in request
    ] == [
        "date=%s" % FUTURE_DAY.isoformat(),
        "date=%s" % FUTURE_DAY.isoformat(),
        "date=%s" % later_day.isoformat(),
    ]
    assert page.request_count(SLOTS_URL % 94502) == 2


def test_clinic_without_slots_shows_hint(appointments_tab):
    page = appointments_tab(routes=[route(SLOTS_URL % 94501, [], method="GET")])
    page.fill_booking(pet_id=94101, clinic_id=94501, date=FUTURE_DAY.isoformat())
    page.wait_for_slot_hint(NO_SLOTS_TEXT)

    assert page.slot_labels() == ["No available slots"]
    assert not page.is_slot_enabled()


def test_slot_taken_concurrently_shows_error(appointments_tab):
    page = appointments_tab(
        routes=[
            route(SLOTS_URL % 94501, slots(FUTURE_DAY, "09:00"), method="GET"),
            route(
                CREATE_APPOINTMENT_URL, {"error": SLOT_TAKEN_ERROR}, 400, method="POST"
            ),
        ]
    )
    page.fill_booking(pet_id=94101, clinic_id=94501, date=FUTURE_DAY.isoformat())
    page.choose_slot(at(FUTURE_DAY, "09:00")).submit_booking()
    page.wait_for_booking_error(SLOT_TAKEN_ERROR)

    assert page.active_tab() == "Appointments"
    assert page.booking_values()["slot"] == at(FUTURE_DAY, "09:00")


def test_past_date_cannot_be_booked(appointments_tab):
    yesterday = TODAY - timedelta(days=1)
    page = appointments_tab(routes=[route(SLOTS_URL % 94501, [], method="GET")])
    page.fill_booking(pet_id=94101, clinic_id=94501, date=yesterday.isoformat())
    page.wait_for_slot_hint(NO_SLOTS_TEXT).submit_booking()

    assert page.validity(ProfilePage.APPOINTMENT_DATE, "rangeUnderflow")
    assert page.request_count(CREATE_APPOINTMENT_URL, "POST") == 0


def test_cancel_future_appointment_after_confirm(appointments_tab):
    page = appointments_tab(
        routes=[
            route(
                "/api/appointments/my/94601/cancel",
                dict(FUTURE_APPOINTMENT, status="CANCELLED"),
                method="PATCH",
            )
        ],
        appointments=[FUTURE_APPOINTMENT],
    )
    page.select_day(FUTURE_DAY)

    assert page.appointment_buttons("StubPet") == ["Cancel appointment"]

    page.click_appointment_button("StubPet", "Cancel appointment").accept_dialog()
    page.wait_for_appointment_status("StubPet", "CANCELLED")

    assert page.appointment_buttons("StubPet") == []
    assert page.request_count("/cancel", "PATCH") == 1


def test_cancel_dismissed_keeps_appointment(appointments_tab):
    page = appointments_tab(appointments=[FUTURE_APPOINTMENT])
    page.select_day(FUTURE_DAY)
    page.click_appointment_button("StubPet", "Cancel appointment").dismiss_dialog()

    assert page.appointment_status("StubPet") == "CONFIRMED"
    assert page.appointment_buttons("StubPet") == ["Cancel appointment"]
    assert page.request_count("/cancel", "PATCH") == 0


def test_past_appointment_cannot_be_cancelled(appointments_tab):
    page = appointments_tab(appointments=[stub_appointment(94603, at(PAST_DAY))])
    page.select_day(PAST_DAY)

    assert page.appointment_status("StubPet") == "CONFIRMED"
    assert page.appointment_buttons("StubPet") == []


def test_cancelled_appointment_cannot_be_cancelled_again(appointments_tab):
    page = appointments_tab(appointments=[dict(FUTURE_APPOINTMENT, status="CANCELLED")])
    page.select_day(FUTURE_DAY)

    assert page.appointment_status("StubPet") == "CANCELLED"
    assert page.appointment_buttons("StubPet") == []


def test_done_and_no_show_appointments_cannot_be_cancelled(appointments_tab):
    page = appointments_tab(
        appointments=[
            stub_appointment(94604, at(FUTURE_DAY, "09:00"), status="DONE"),
            stub_appointment(
                94605,
                at(FUTURE_DAY, "11:00"),
                status="NO_SHOW",
                animalId=94102,
                petName="Milo",
                petSpecies="Cat",
            ),
        ]
    )
    page.select_day(FUTURE_DAY)

    assert "Cancel appointment" not in page.appointment_buttons("StubPet")
    assert page.appointment_status("Milo") == "NO_SHOW"
    assert page.appointment_buttons("Milo") == []


def test_clinic_review_can_be_left_after_done_appointment(appointments_tab):
    page = appointments_tab(
        routes=[
            route(
                CLINIC_REVIEWS_URL + "94501",
                stub_clinic_review(94701, rating=5, comment="Great vet"),
                201,
                method="POST",
            )
        ],
        appointments=[DONE_APPOINTMENT],
    )
    page.select_day(PAST_DAY)
    page.click_appointment_button("StubPet", "Leave clinic review")
    page.select_review_stars("StubPet", 5).type_review_comment("StubPet", "Great vet")
    page.click_appointment_button("StubPet", "Submit review")
    page.wait_for_review_summary("StubPet", {"stars": 5, "comment": "Great vet"})

    assert page.request_bodies(CLINIC_REVIEWS_URL + "94501", "POST") == [
        {"rating": 5, "comment": "Great vet"}
    ]
    assert "Edit review" in page.appointment_buttons("StubPet")


def test_clinic_review_requires_rating(appointments_tab):
    page = appointments_tab(appointments=[DONE_APPOINTMENT])
    page.select_day(PAST_DAY)
    page.click_appointment_button("StubPet", "Leave clinic review")
    page.type_review_comment("StubPet", "Forgot the stars")
    page.click_appointment_button("StubPet", "Submit review")
    page.wait_for_appointment_error("StubPet", RATING_REQUIRED_ERROR)

    assert page.request_count(CLINIC_REVIEWS_URL, "POST") == 0


def test_clinic_review_not_offered_before_done(appointments_tab):
    page = appointments_tab(appointments=[FUTURE_APPOINTMENT])
    page.select_day(FUTURE_DAY)

    assert "Leave clinic review" not in page.appointment_buttons("StubPet")
    assert "Add health record" not in page.appointment_buttons("StubPet")


def test_clinic_review_can_be_updated(appointments_tab):
    review = stub_clinic_review(94701, rating=4, comment="Kind staff.")
    page = appointments_tab(
        routes=[
            route(CLINIC_REVIEWS_URL + "94501/mine", review, method="GET"),
            route(
                REVIEWS_URL + "94701",
                dict(review, rating=2, comment="Long wait."),
                method="PUT",
            ),
        ],
        appointments=[DONE_APPOINTMENT],
    )
    page.select_day(PAST_DAY)

    assert page.review_summary("StubPet") == {"stars": 4, "comment": "Kind staff."}

    page.click_appointment_button("StubPet", "Edit review")

    assert page.review_form_rating("StubPet") == 4
    assert page.review_form_comment("StubPet") == "Kind staff."

    page.select_review_stars("StubPet", 2).type_review_comment("StubPet", "Long wait.")
    page.click_appointment_button("StubPet", "Save review")
    page.wait_for_review_summary("StubPet", {"stars": 2, "comment": "Long wait."})

    assert page.request_bodies(REVIEWS_URL + "94701", "PUT") == [
        {"rating": 2, "comment": "Long wait."}
    ]


def test_clinic_review_can_be_deleted_after_confirm(appointments_tab):
    page = appointments_tab(
        routes=[
            route(
                CLINIC_REVIEWS_URL + "94501/mine",
                stub_clinic_review(94701),
                method="GET",
            ),
            route(REVIEWS_URL + "94701", None, method="DELETE"),
        ],
        appointments=[DONE_APPOINTMENT],
    )
    page.select_day(PAST_DAY)
    page.click_appointment_button("StubPet", "Delete").accept_dialog()
    page.wait.until(
        lambda d: "Leave clinic review" in page.appointment_buttons("StubPet")
    )

    assert page.review_summary("StubPet") is None
    assert page.request_count(REVIEWS_URL + "94701", "DELETE") == 1


def test_duplicate_clinic_review_is_blocked(appointments_tab):
    page = appointments_tab(
        routes=[
            route(
                CLINIC_REVIEWS_URL + "94501",
                {"error": DUPLICATE_CLINIC_REVIEW},
                400,
                method="POST",
            )
        ],
        appointments=[DONE_APPOINTMENT],
    )
    page.select_day(PAST_DAY)
    page.click_appointment_button("StubPet", "Leave clinic review")
    page.select_review_stars("StubPet", 3)
    page.click_appointment_button("StubPet", "Submit review")
    page.wait_for_appointment_error("StubPet", DUPLICATE_CLINIC_REVIEW)

    assert page.review_summary("StubPet") is None


def test_health_record_can_be_added_after_done_appointment(appointments_tab):
    record = stub_health_record(94801, 94602, type="Vaccination", description="Rabies")
    page = appointments_tab(
        routes=[route(HEALTH_RECORDS_URL, record, 201, method="POST")],
        appointments=[DONE_APPOINTMENT],
    )
    page.select_day(PAST_DAY)
    page.click_appointment_button("StubPet", "Add health record")
    page.fill_health_record("StubPet", "Vaccination", "Rabies")
    page.click_appointment_button("StubPet", "Save health record")
    page.wait_for_health_summary("StubPet")

    assert page.health_summary("StubPet") == {
        "type": "Vaccination",
        "description": "Rabies",
        "date": "May 6, 2026",
    }
    assert page.request_bodies(HEALTH_RECORDS_URL, "POST") == [
        {"appointmentId": 94602, "type": "Vaccination", "description": "Rabies"}
    ]
    assert "Add health record" not in page.appointment_buttons("StubPet")


def test_health_record_type_is_required(appointments_tab):
    page = appointments_tab(appointments=[DONE_APPOINTMENT])
    page.select_day(PAST_DAY)
    page.click_appointment_button("StubPet", "Add health record")
    page.click_appointment_button("StubPet", "Save health record")

    assert page.health_type_validity("StubPet", "valueMissing")

    page.fill_health_record("StubPet", "   ")
    page.click_appointment_button("StubPet", "Save health record")
    page.wait_for_appointment_error("StubPet", HEALTH_TYPE_ERROR)

    assert page.request_count(HEALTH_RECORDS_URL, "POST") == 0


def test_health_record_type_is_trimmed(appointments_tab):
    page = appointments_tab(
        routes=[
            route(
                HEALTH_RECORDS_URL,
                stub_health_record(94801, 94602, type="Checkup"),
                201,
                method="POST",
            )
        ],
        appointments=[DONE_APPOINTMENT],
    )
    page.select_day(PAST_DAY)
    page.click_appointment_button("StubPet", "Add health record")
    page.fill_health_record("StubPet", "   Checkup   ")
    page.click_appointment_button("StubPet", "Save health record")
    page.wait_for_health_summary("StubPet")

    assert page.request_bodies(HEALTH_RECORDS_URL, "POST") == [
        {"appointmentId": 94602, "type": "Checkup"}
    ]


def test_duplicate_health_record_is_blocked(appointments_tab):
    page = appointments_tab(
        routes=[
            route(
                HEALTH_RECORDS_URL,
                {"error": DUPLICATE_HEALTH_RECORD},
                400,
                method="POST",
            )
        ],
        appointments=[DONE_APPOINTMENT],
    )
    page.select_day(PAST_DAY)
    page.click_appointment_button("StubPet", "Add health record")
    page.fill_health_record("StubPet", "Vaccination")
    page.click_appointment_button("StubPet", "Save health record")
    page.wait_for_appointment_error("StubPet", DUPLICATE_HEALTH_RECORD)

    assert page.health_summary("StubPet") is None


def test_existing_health_record_is_shown(appointments_tab):
    page = appointments_tab(
        routes=[
            route(
                "/api/pets/94101/health-records",
                [stub_health_record(94801, 94602)],
                method="GET",
            )
        ],
        appointments=[DONE_APPOINTMENT],
    )
    page.select_day(PAST_DAY)

    assert page.health_summary("StubPet") == {
        "type": "Vaccination",
        "description": "Rabies booster.",
        "date": "May 6, 2026",
    }
    assert "Add health record" not in page.appointment_buttons("StubPet")
