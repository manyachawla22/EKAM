-- Adds the new 'results' value to the EventStage enum for EXISTING databases.
--
-- Background: tables are created via SQLAlchemy `Base.metadata.create_all`, which
-- will NOT alter an enum type that already exists. Fresh databases pick up
-- 'results' automatically; existing ones need this one-time statement.
--
-- The SQLAlchemy enum type for app.models.event.EventStage is named "eventstage".
-- Run once against your Postgres database, e.g.:
--   psql "$DATABASE_URL" -f backend/scripts/add_results_stage.sql
--
-- Note: ADD VALUE cannot run inside a transaction block on older Postgres,
-- so run this statement on its own (psql -f does this fine).

ALTER TYPE eventstage ADD VALUE IF NOT EXISTS 'results' BEFORE 'completed';
