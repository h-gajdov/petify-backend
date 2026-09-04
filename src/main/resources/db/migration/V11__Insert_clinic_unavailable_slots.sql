-- Seed rows for clinic_unavailable_slots (the table is created in V9).
-- These lived in V2, which runs long before the table exists.
BEGIN;

INSERT INTO clinic_unavailable_slots (clinic_id, date_time, reason, created_at)
SELECT clinic_id, date_time, reason, created_at
FROM (VALUES
    (
        (SELECT clinic_id FROM vet_clinics WHERE name = 'Happy Paws Clinic'),
        NOW() + INTERVAL '1 day',
        'Doctor unavailable - private appointment',
        NOW()
    ),
    (
        (SELECT clinic_id FROM vet_clinics WHERE name = 'Happy Paws Clinic'),
        NOW() + INTERVAL '3 days',
        'Clinic equipment maintenance',
        NOW()
    ),
    (
        (SELECT clinic_id FROM vet_clinics WHERE name = 'Happy Paws Clinic'),
        NOW() + INTERVAL '7 days',
        'Staff training session',
        NOW()
    ),
    (
        (SELECT clinic_id FROM vet_clinics WHERE name = 'VetCare Center'),
        NOW() + INTERVAL '2 days',
        'Emergency-only working hours',
        NOW()
    ),
    (
        (SELECT clinic_id FROM vet_clinics WHERE name = 'VetCare Center'),
        NOW() + INTERVAL '5 days',
        'Veterinarian on leave',
        NOW()
    ),
    (
        (SELECT clinic_id FROM vet_clinics WHERE name = 'VetCare Center'),
        NOW() + INTERVAL '10 days',
        'Clinic closed for local holiday',
        NOW()
    )
) AS seed(clinic_id, date_time, reason, created_at)
WHERE NOT EXISTS (SELECT 1 FROM clinic_unavailable_slots);

COMMIT;
