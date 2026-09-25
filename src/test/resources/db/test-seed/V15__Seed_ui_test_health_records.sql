BEGIN;

INSERT INTO appointments (clinic_id, animal_id, responsible_owner_id, status, date_time, notes)
SELECT vc.clinic_id, a.animal_id, a.owner_id, 'DONE', TIMESTAMP '2025-02-03 09:00:00', 'UI test checkup'
FROM animals a
         CROSS JOIN vet_clinics vc
WHERE a.name = 'UiBeagle'
  AND vc.name = 'UI Test Clinic'
  AND NOT EXISTS (
    SELECT 1 FROM appointments ap
    WHERE ap.animal_id = a.animal_id
      AND ap.date_time = TIMESTAMP '2025-02-03 09:00:00'
);

INSERT INTO health_records (animal_id, appointment_id, type, description, date)
SELECT ap.animal_id, ap.appointment_id, 'Vaccination', 'UI test rabies shot.', ap.date_time::date
FROM appointments ap
         JOIN animals a ON a.animal_id = ap.animal_id
WHERE a.name = 'UiBeagle'
  AND ap.date_time = TIMESTAMP '2025-02-03 09:00:00'
  AND NOT EXISTS (
    SELECT 1 FROM health_records hr WHERE hr.appointment_id = ap.appointment_id
);

COMMIT;
