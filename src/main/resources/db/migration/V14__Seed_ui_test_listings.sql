BEGIN;

INSERT INTO users (username, email, name, surname, password_hash, created_at)
SELECT 'ui.owner', 'ui.owner@petify.test', 'Olive', 'Owner', 'TestPass123!', NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'ui.owner');

INSERT INTO users (username, email, name, surname, password_hash, created_at)
SELECT 'ui.fav', 'ui.fav@petify.test', 'Fay', 'Favorite', 'TestPass123!', NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'ui.fav');

INSERT INTO users (username, email, name, surname, password_hash, created_at)
SELECT 'ui.recs', 'ui.recs@petify.test', 'Rita', 'Recs', 'TestPass123!', NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'ui.recs');

INSERT INTO users (username, email, name, surname, password_hash, created_at)
SELECT 'ui.norecs', 'ui.norecs@petify.test', 'Noel', 'Norecs', 'TestPass123!', NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'ui.norecs');

INSERT INTO clients (user_id, is_blocked)
SELECT u.user_id, FALSE FROM users u
WHERE u.username IN ('ui.owner', 'ui.fav', 'ui.recs', 'ui.norecs')
  AND NOT EXISTS (SELECT 1 FROM clients c WHERE c.user_id = u.user_id);

INSERT INTO owners (user_id)
SELECT u.user_id FROM users u
WHERE u.username = 'ui.owner'
  AND NOT EXISTS (SELECT 1 FROM owners o WHERE o.user_id = u.user_id);

INSERT INTO animals (owner_id, name, sex, date_of_birth, photo_url, species, type, breed, located_name)
SELECT u.user_id, v.name, v.sex, v.date_of_birth, NULL, v.species, v.species, v.breed, v.located_name
FROM users u
         CROSS JOIN (VALUES
                         ('UiBeagle', 'FEMALE', DATE '2021-03-04', 'Dog', 'Beagle', 'Ohrid'),
                         ('UiCorgi', 'MALE', DATE '2020-07-19', 'Dog', 'Corgi', 'Bitola'),
                         ('UiSiamese', 'FEMALE', DATE '2022-01-25', 'Cat', 'Siamese', 'OHRID'),
                         ('UiCanary', 'MALE', DATE '2023-06-11', 'Bird', 'Canary', 'Struga')
    ) AS v(name, sex, date_of_birth, species, breed, located_name)
WHERE u.username = 'ui.owner'
  AND NOT EXISTS (SELECT 1 FROM animals a WHERE a.name = v.name);

INSERT INTO listings (owner_id, animal_id, status, price, description, created_at)
SELECT a.owner_id, a.animal_id, 'ACTIVE', v.price, v.description, NOW() - v.age
FROM animals a
         JOIN (VALUES
                   ('UiBeagle', 120.00, 'UI test beagle from Ohrid.', INTERVAL '4 days'),
                   ('UiCorgi', 130.00, 'UI test corgi from Bitola.', INTERVAL '3 days'),
                   ('UiSiamese', 140.00, 'UI test siamese from Ohrid.', INTERVAL '2 days'),
                   ('UiCanary', 150.00, 'UI test canary from Struga.', INTERVAL '1 day')
    ) AS v(name, price, description, age) ON v.name = a.name
WHERE NOT EXISTS (SELECT 1 FROM listings l WHERE l.animal_id = a.animal_id);

INSERT INTO favorite_listings (client_id, listing_id)
SELECT u.user_id, l.listing_id
FROM users u
         JOIN animals a ON a.name = 'UiBeagle'
         JOIN listings l ON l.animal_id = a.animal_id
WHERE u.username = 'ui.recs'
  AND NOT EXISTS (
    SELECT 1 FROM favorite_listings f
    WHERE f.client_id = u.user_id AND f.listing_id = l.listing_id
);

DELETE FROM favorite_listings f
    USING users u
WHERE f.client_id = u.user_id
  AND u.username IN ('ui.fav', 'ui.norecs');

COMMIT;
