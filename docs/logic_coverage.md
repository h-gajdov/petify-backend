# Logic Coverage

---

| # | Predicate                   | Method                                   | Clauses |
|:-:|:----------------------------|:-----------------------------------------|:-------:|
| 1 | required fields guard       | `AppointmentService.createAppointment`   |    3    |
| 2 | pet ownership guard         | `AppointmentService.createAppointment`   |    3    |
| 3 | `isClinicSlotAvailable`     | `AppointmentService`                     |    3    |
| 4 | `isValidWorkingSlot`        | `AppointmentService`                     |    6    |
| 5 | rating validation           | `ReviewService.createReview`             |    3    |
| 6 | filter dispatch             | `ListingService.getAdminListings`        |    3    |

---

## 1. Required fields guard — Predicate Coverage

`AppointmentService.createAppointment`

```java
if (request.getClinicId() == null || request.getAnimalId() == null || request.getDateTime() == null) {
    throw new RuntimeException("Clinic, pet, and date/time are required");
}
```

**Clauses:** `a`: `request.getClinicId() == null`, `b`: `request.getAnimalId() == null`, `c`: `request.getDateTime() == null`
**Predicate:** `p = a ∨ b ∨ c`

| # | a | b | c | p |
|:-:|:-:|:-:|:-:|:-:|
| 1 | T | T | T | T |
| 2 | T | T | F | T |
| 3 | T | F | T | T |
| 4 | T | F | F | T |
| 5 | F | T | T | T |
| 6 | F | T | F | T |
| 7 | F | F | T | T |
| 8 | F | F | F | F |

All 8 rows are feasible — the three fields are set independently.

**Test set: rows 4, 8.** Row 4 (`clinicId = null`, other two not null) exercises `p = true`; row 8
(all three present) exercises `p = false`.

---
## 2. Pet ownership guard — Clause Coverage

`AppointmentService.createAppointment`

```java
if (pet.getOwner() == null || pet.getOwner().getUserId() == null || !pet.getOwner().getUserId().equals(userId)) {
    throw new RuntimeException("You can only create appointments for your own pets");
}
```

**Clauses:** `a`: `pet.getOwner() == null`, `b`: `pet.getOwner().getUserId() == null`, `c`: `!pet.getOwner().getUserId().equals(userId)`
**Predicate:** `p = a ∨ b ∨ c`

The three clauses are not independent: if `a` is true the pet has no owner object, so `b` and `c` are
never reached (and would throw a `NullPointerException` if they were). If `b` is true there is no id
to compare, so `c` is never reached either. The full truth table makes this visible:

| # | a | b | c | p | Feasible |
|:-:|:-:|:-:|:-:|:-:|:--------:|
| 1 | T | T | T | T |    No    |
| 2 | T | T | F | T |    No    |
| 3 | T | F | T | T |    No    |
| 4 | T | F | F | T | **Yes**  |
| 5 | F | T | T | T |    No    |
| 6 | F | T | F | T | **Yes**  |
| 7 | F | F | T | T | **Yes**  |
| 8 | F | F | F | F | **Yes**  |

**Test set: rows 4, 6, 7.** CC only requires each clause to be true once and false once somewhere in
the set — it says nothing about `p`, and `p = true` at all three rows.

---
## 3. `isClinicSlotAvailable` — General Active Clause Coverage

`AppointmentService`

```java
if (!isValidWorkingSlot(appointmentTime)) {
    return false;
}
return !appointmentRepository.existsByClinicIdAndDateTimeAndStatusNotIn(clinicId, appointmentTime, NON_BLOCKING_STATUSES)
    && !unavailableSlotRepository.existsByClinicIdAndDateTime(clinicId, appointmentTime);
```

**Clauses:** `a`: `isValidWorkingSlot(time)`, `b`: no blocking appointment exists, `c`: the slot is
not marked unavailable
**Predicate:** `p = a ∧ b ∧ c`

| # | a | b | c | p | Active a | Active b | Active c |
|:-:|:-:|:-:|:-:|:-:|:--------:|:--------:|:--------:|
| 1 | T | T | T | T |    X     |    X     |    X     |
| 2 | T | T | F | F |          |          |    X     |
| 3 | T | F | T | F |          |    X     |          |
| 4 | T | F | F | F |          |          |          |
| 5 | F | T | T | F |    X     |          |          |
| 6 | F | T | F | F |          |          |          |
| 7 | F | F | T | F |          |          |          |
| 8 | F | F | F | F |          |          |          |



| Major clause | Evaluates to True (a b c) | Evaluates to False (a b c) |
|:------------:|:-------------------------:|:--------------------------:|
|      a       |           T T T           |           F T T            |
|      b       |           T T T           |           T F T            |
|      c       |           T T T           |           T T F            |

**Test set: rows 1, 2, 3, 5** Test setup: row 1 = valid future slot,
both repositories return `false`; row 5 = slot at `10:15`, off the 30-minute grid (`a` false); row 3
= appointment repository returns `true` (`b` false); row 2 = unavailable-slot repository returns
`true` (`c` false).

---
## 4. `isValidWorkingSlot` — Correlated Active Clause Coverage

`AppointmentService`

```java
return !appointmentTime.isBefore(LocalDateTime.now())
    && !time.isBefore(CLINIC_DAY_START)
    && time.isBefore(CLINIC_DAY_END)
    && appointmentTime.getMinute() % SLOT_MINUTES == 0
    && appointmentTime.getSecond() == 0
    && appointmentTime.getNano() == 0;
```

**Clauses:**
* `a`: `!appointmentTime.isBefore(now)` — not in the past
* `b`: `!time.isBefore(09:00)` — not before opening
* `c`: `time.isBefore(17:00)` — before closing
* `d`: `minute % 30 == 0` — on the half-hour grid
* `e`: `second == 0`
* `f`: `nano == 0`

**Predicate:** `p = a ∧ b ∧ c ∧ d ∧ e ∧ f`

**Infeasibility:** `b` and `c` cannot both be false — a time cannot be before 09:00 and at or after
17:00 simultaneously. That rules out 16 of the 64 rows below.

Full truth table (64 rows, `p = a ∧ b ∧ c ∧ d ∧ e ∧ f`)

| #  | a | b | c | d | e | f | p | Active a | Active b | Active c | Active d | Active e | Active f | Feasible |
|:--:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-----------|
| 1 | T | T | T | T | T | T | T | X | X | X | X | X | X |  |
| 2 | T | T | T | T | T | F | F |  |  |  |  |  | X |  |
| 3 | T | T | T | T | F | T | F |  |  |  |  | X |  |  |
| 4 | T | T | T | T | F | F | F |  |  |  |  |  |  |  |
| 5 | T | T | T | F | T | T | F |  |  |  | X |  |  |  |
| 6 | T | T | T | F | T | F | F |  |  |  |  |  |  |  |
| 7 | T | T | T | F | F | T | F |  |  |  |  |  |  |  |
| 8 | T | T | T | F | F | F | F |  |  |  |  |  |  |  |
| 9 | T | T | F | T | T | T | F |  |  | X |  |  |  |  |
| 10 | T | T | F | T | T | F | F |  |  |  |  |  |  |  |
| 11 | T | T | F | T | F | T | F |  |  |  |  |  |  |  |
| 12 | T | T | F | T | F | F | F |  |  |  |  |  |  |  |
| 13 | T | T | F | F | T | T | F |  |  |  |  |  |  |  |
| 14 | T | T | F | F | T | F | F |  |  |  |  |  |  |  |
| 15 | T | T | F | F | F | T | F |  |  |  |  |  |  |  |
| 16 | T | T | F | F | F | F | F |  |  |  |  |  |  |  |
| 17 | T | F | T | T | T | T | F |  | X |  |  |  |  |  |
| 18 | T | F | T | T | T | F | F |  |  |  |  |  |  |  |
| 19 | T | F | T | T | F | T | F |  |  |  |  |  |  |  |
| 20 | T | F | T | T | F | F | F |  |  |  |  |  |  |  |
| 21 | T | F | T | F | T | T | F |  |  |  |  |  |  |  |
| 22 | T | F | T | F | T | F | F |  |  |  |  |  |  |  |
| 23 | T | F | T | F | F | T | F |  |  |  |  |  |  |  |
| 24 | T | F | T | F | F | F | F |  |  |  |  |  |  |  |
| 25 | T | F | F | T | T | T | F |  |  |  |  |  |  | infeasible |
| 26 | T | F | F | T | T | F | F |  |  |  |  |  |  | infeasible |
| 27 | T | F | F | T | F | T | F |  |  |  |  |  |  | infeasible |
| 28 | T | F | F | T | F | F | F |  |  |  |  |  |  | infeasible |
| 29 | T | F | F | F | T | T | F |  |  |  |  |  |  | infeasible |
| 30 | T | F | F | F | T | F | F |  |  |  |  |  |  | infeasible |
| 31 | T | F | F | F | F | T | F |  |  |  |  |  |  | infeasible |
| 32 | T | F | F | F | F | F | F |  |  |  |  |  |  | infeasible |
| 33 | F | T | T | T | T | T | F | X |  |  |  |  |  |  |
| 34 | F | T | T | T | T | F | F |  |  |  |  |  |  |  |
| 35 | F | T | T | T | F | T | F |  |  |  |  |  |  |  |
| 36 | F | T | T | T | F | F | F |  |  |  |  |  |  |  |
| 37 | F | T | T | F | T | T | F |  |  |  |  |  |  |  |
| 38 | F | T | T | F | T | F | F |  |  |  |  |  |  |  |
| 39 | F | T | T | F | F | T | F |  |  |  |  |  |  |  |
| 40 | F | T | T | F | F | F | F |  |  |  |  |  |  |  |
| 41 | F | T | F | T | T | T | F |  |  |  |  |  |  |  |
| 42 | F | T | F | T | T | F | F |  |  |  |  |  |  |  |
| 43 | F | T | F | T | F | T | F |  |  |  |  |  |  |  |
| 44 | F | T | F | T | F | F | F |  |  |  |  |  |  |  |
| 45 | F | T | F | F | T | T | F |  |  |  |  |  |  |  |
| 46 | F | T | F | F | T | F | F |  |  |  |  |  |  |  |
| 47 | F | T | F | F | F | T | F |  |  |  |  |  |  |  |
| 48 | F | T | F | F | F | F | F |  |  |  |  |  |  |  |
| 49 | F | F | T | T | T | T | F |  |  |  |  |  |  |  |
| 50 | F | F | T | T | T | F | F |  |  |  |  |  |  |  |
| 51 | F | F | T | T | F | T | F |  |  |  |  |  |  |  |
| 52 | F | F | T | T | F | F | F |  |  |  |  |  |  |  |
| 53 | F | F | T | F | T | T | F |  |  |  |  |  |  |  |
| 54 | F | F | T | F | T | F | F |  |  |  |  |  |  |  |
| 55 | F | F | T | F | F | T | F |  |  |  |  |  |  |  |
| 56 | F | F | T | F | F | F | F |  |  |  |  |  |  |  |
| 57 | F | F | F | T | T | T | F |  |  |  |  |  |  | infeasible |
| 58 | F | F | F | T | T | F | F |  |  |  |  |  |  | infeasible |
| 59 | F | F | F | T | F | T | F |  |  |  |  |  |  | infeasible |
| 60 | F | F | F | T | F | F | F |  |  |  |  |  |  | infeasible |
| 61 | F | F | F | F | T | T | F |  |  |  |  |  |  | infeasible |
| 62 | F | F | F | F | T | F | F |  |  |  |  |  |  | infeasible |
| 63 | F | F | F | F | F | T | F |  |  |  |  |  |  | infeasible |
| 64 | F | F | F | F | F | F | F |  |  |  |  |  |  | infeasible |

48 of the 64 rows are feasible. Six clauses means CoC would need all 64 rows (48 feasible); CACC
needs only `n + 1 = 7`, which is the headline cost comparison this document is built around.

**Determination**, using `p_x = p(x=true) ⊕ p(x=false)` — the condition on the other five clauses
under which `x` determines `p`:

```
p_a = b ∧ c ∧ d ∧ e ∧ f      p_b = a ∧ c ∧ d ∧ e ∧ f      p_c = a ∧ b ∧ d ∧ e ∧ f
p_d = a ∧ b ∧ c ∧ e ∧ f      p_e = a ∧ b ∧ c ∧ d ∧ f      p_f = a ∧ b ∧ c ∧ d ∧ e
```

| Major clause | Evaluates to True (a b c d e f) | Evaluates to False (a b c d e f) |
|:------------:|:-------------------------------:|:--------------------------------:|
|     a        |           T T T T T T           |           F T T T T T            |
|      b       |           T T T T T T           |           T F T T T T            |
|      c       |           T T T T T T           |           T T F T T T            |
|      d       |           T T T T T T           |           T T T F T T            |
|      e       |           T T T T T T           |           T T T T F T            |
|      f       |           T T T T T T           |           T T T T T F            |

**Test set: rows 1, 2, 3, 5, 9, 17, 33.**

---
## 5. Rating validation — Restricted Active Clause Coverage

`ReviewService.createReview`

```java
if (request.getRating() == null || request.getRating() < 1 || request.getRating() > 5) {
    throw new RuntimeException("Rating must be between 1 and 5");
}
```

**Clauses:** `a`: `request.getRating() == null`, `b`: `request.getRating() < 1`, `c`: `request.getRating() > 5`
**Predicate:** `p = a ∨ b ∨ c`

**Infeasibility:** `b ∧ c` is contradictory (a rating cannot be simultaneously below 1 and above 5),
which rules out rows 1 and 5. Java also short-circuits `||`, so whenever `a` is true, `b` and `c` are
never evaluated — unboxing `request.getRating()` would otherwise throw a `NullPointerException`. That
rules out rows 2 and 3
(`a = true` with `b` or `c` also true): the only row that represents `a = true` at runtime is row 4,
where `b` and `c` are both false.

| # | a | b | c | p | Active a | Active b | Active c | Feasible |
|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | T | T | T | T |   |   |   | No |
| 2 | T | T | F | T |   |   |   | No |
| 3 | T | F | T | T |   |   |   | No |
| 4 | T | F | F | T | X |   |   | **Yes** |
| 5 | F | T | T | T |   |   |   | No |
| 6 | F | T | F | T |   | X |   | **Yes** |
| 7 | F | F | T | T |   |   | X | **Yes** |
| 8 | F | F | F | F | X | X | X | **Yes** |


| Major clause | Evaluates to True (a b c) | Evaluates to False (a b c) |
|:-:|:-:|:-:|
| a | T F F | F F F |
| b | F T F | F F F |
| c | F F T | F F F |

**Test set: rows 4, 6, 7, 8.**

---
## 6. Filter dispatch — Combinatorial Coverage

`ListingService.getAdminListings`

```java
if (normalizedStatus == null && !hasMinPrice && !hasMaxPrice) {
    return listingRepository.findAll(pageable).map(this::mapToDTO);
}
```

**Clauses:** `a`: `normalizedStatus == null`, `b`: `minPrice == null`, `c`: `maxPrice == null`
**Predicate:** `p = a ∧ b ∧ c`

| # | a | b | c |   p    | status     | minPrice | maxPrice | Repository called        |
|:-:|:-:|:-:|:-:|:------:|:-----------|:---------|:---------|:-------------------------|
| 1 | T | T | T | **T**  | `null`     | `null`   | `null`   | `findAll`                |
| 2 | T | T | F |   F    | `null`     | `null`   | `100`    | `findAdminListings`      |
| 3 | T | F | T |   F    | `null`     | `10`     | `null`   | `findAdminListings`      |
| 4 | T | F | F |   F    | `null`     | `10`     | `100`    | `findAdminListings`      |
| 5 | F | T | T |   F    | `"ACTIVE"` | `null`   | `null`   | `findByStatusIgnoreCase` |
| 6 | F | T | F |   F    | `"ACTIVE"` | `null`   | `100`    | `findAdminListings`      |
| 7 | F | F | T |   F    | `"ACTIVE"` | `10`     | `null`   | `findAdminListings`      |
| 8 | F | F | F |   F    | `"ACTIVE"` | `10`     | `100`    | `findAdminListings`      |

**Test set: all 8 rows.**

