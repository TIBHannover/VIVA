FROM alpine:20201218

RUN apk add --no-cache postgresql-client

COPY backup.sh /etc/periodic/daily/db_backup
RUN chmod +x /etc/periodic/daily/db_backup

COPY cleanup.sh /etc/periodic/daily/dump_cleanup
RUN chmod +x /etc/periodic/daily/dump_cleanup

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["crond"]