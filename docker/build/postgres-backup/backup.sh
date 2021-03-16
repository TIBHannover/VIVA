#! /bin/sh

TIMESTAMP=$(date +"%F")
BACKUP_DIR="/dumps"
CURRENT_BACKUP="${BACKUP_DIR}/${TIMESTAMP}"
PG_DUMP=/usr/bin/pg_dump

echo "Starting PostgreSQL backup"
# create single database dump into a compressed sql file
PGPASSWORD=${POSTGRES_PASSWORD} ${PG_DUMP} \
    --host=${SERVICE_DATABASE_POSTGRES} \
    --username=${POSTGRES_USER} \
    --clean \
    ${POSTGRES_DB} \
 | gzip -9 - >${CURRENT_BACKUP}.sql.gz
echo "Finished PostgreSQL backup"
