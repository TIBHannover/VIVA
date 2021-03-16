#! /bin/sh

BACKUP_DIR="/dumps"

# delete daily backups of last 30-90 days except if day of month = 1
for i in $(seq 30 90); do
	if [[ $(date +"%d" -d@$(($(date +%s)-86400*$i))) != "01" ]]; then
		delete_timestamp=$(date +"%F" -d@$(($(date +%s)-86400*$i)))
		rm -f "${BACKUP_DIR}/${delete_timestamp}.sql.gz" 2>/dev/null
	fi
done
# delete backups with day of month = 1 and age of 1-2 years
for i in $(seq 365 730); do
	if [[ $(date +"%d" -d@$(($(date +%s)-86400*$i))) = "01" ]]; then
		delete_timestamp=$(date +"%F" -d@$(($(date +%s)-86400*$i)))
		rm -f "${BACKUP_DIR}/${delete_timestamp}.sql.gz" 2>/dev/null
	fi
done
