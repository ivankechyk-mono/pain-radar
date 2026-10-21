FROM postgres:17-alpine

COPY migrations/001_raw_messages.sql /docker-entrypoint-initdb.d/001_raw_messages.sql
COPY migrations/002_classified_pains.sql /docker-entrypoint-initdb.d/002_classified_pains.sql
COPY migrations/003_add_emotional_fields.sql /docker-entrypoint-initdb.d/003_add_emotional_fields.sql
