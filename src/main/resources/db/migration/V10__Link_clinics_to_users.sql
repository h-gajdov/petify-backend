ALTER TABLE vet_clinics
    ADD COLUMN IF NOT EXISTS user_id BIGINT;

ALTER TABLE vet_clinics
    DROP CONSTRAINT IF EXISTS vet_clinics_user_FK;

ALTER TABLE vet_clinics
    ADD CONSTRAINT vet_clinics_user_FK FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT;

ALTER TABLE vet_clinics
    DROP CONSTRAINT IF EXISTS vet_clinics_user_UQ;

ALTER TABLE vet_clinics
    ADD CONSTRAINT vet_clinics_user_UQ UNIQUE (user_id);
