-- Create the credential_db schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS credential_db;

-- Grant all privileges on the schema to the postgres user
GRANT ALL ON SCHEMA credential_db TO postgres;

-- Set the default privileges for future objects in this schema
ALTER DEFAULT PRIVILEGES IN SCHEMA credential_db GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA credential_db GRANT ALL ON SEQUENCES TO postgres;
