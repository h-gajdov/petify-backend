BEGIN;

INSERT INTO users (username, email, name, surname, password_hash, created_at)
SELECT 'ui.client', 'ui.client@petify.test', 'Uma', 'Client', 'TestPass123!', NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'ui.client');

INSERT INTO users (username, email, name, surname, password_hash, created_at)
SELECT 'ui.admin', 'ui.admin@petify.test', 'Ada', 'Admin', 'TestPass123!', NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'ui.admin');

INSERT INTO users (username, email, name, surname, password_hash, created_at)
SELECT 'ui.clinic', 'ui.clinic@petify.test', 'City', 'Clinic', 'TestPass123!', NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'ui.clinic');

INSERT INTO users (username, email, name, surname, password_hash, created_at)
SELECT 'ui.blocked', 'ui.blocked@petify.test', 'Bo', 'Blocked', 'TestPass123!', NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'ui.blocked');

INSERT INTO admins (user_id)
SELECT u.user_id FROM users u
WHERE u.username = 'ui.admin'
  AND NOT EXISTS (SELECT 1 FROM admins a WHERE a.user_id = u.user_id);

INSERT INTO clients (user_id, is_blocked)
SELECT u.user_id, FALSE FROM users u
WHERE u.username = 'ui.client'
  AND NOT EXISTS (SELECT 1 FROM clients c WHERE c.user_id = u.user_id);

INSERT INTO clients (user_id, is_blocked, blocked_at, blocked_reason, blocked_by)
SELECT u.user_id, TRUE, NOW(), 'Repeated policy violations',
       (SELECT user_id FROM users WHERE username = 'ui.admin')
FROM users u
WHERE u.username = 'ui.blocked'
  AND NOT EXISTS (SELECT 1 FROM clients c WHERE c.user_id = u.user_id);

INSERT INTO vet_clinic_applications
    (name, email, phone, city, address, submitted_at, status, reviewed_at, reviewed_by)
SELECT 'UI Test Clinic', 'ui.clinic@petify.test', '+389 70 000 000', 'Skopje', 'Testna 1',
       NOW(), 'APPROVED', NOW(), (SELECT user_id FROM users WHERE username = 'ui.admin')
WHERE NOT EXISTS (SELECT 1 FROM vet_clinic_applications WHERE name = 'UI Test Clinic');

INSERT INTO vet_clinics (name, email, phone, location, city, address, application_id, user_id)
SELECT 'UI Test Clinic', 'ui.clinic@petify.test', '+389 70 000 000', 'Centar', 'Skopje', 'Testna 1',
       (SELECT application_id FROM vet_clinic_applications WHERE name = 'UI Test Clinic'
        ORDER BY application_id DESC LIMIT 1),
       u.user_id
FROM users u
WHERE u.username = 'ui.clinic'
  AND NOT EXISTS (SELECT 1 FROM vet_clinics v WHERE v.user_id = u.user_id);

COMMIT;
