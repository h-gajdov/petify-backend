-- Match the Pet entity and sql/ddl.sql on databases created through Flyway.
-- Older deployments may already have this column from the standalone schema.
ALTER TABLE animals ADD COLUMN IF NOT EXISTS type VARCHAR(40);
