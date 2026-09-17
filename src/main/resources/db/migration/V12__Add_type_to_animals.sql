ALTER TABLE animals
    ADD COLUMN type VARCHAR(60);

UPDATE animals
SET type = species
WHERE type IS NULL;

ALTER TABLE animals
    ALTER COLUMN type SET NOT NULL;
