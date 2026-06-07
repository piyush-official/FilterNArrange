FROM alpine:3.20
RUN apk add --no-cache postgresql16-client mc curl bash gzip coreutils tzdata dcron
COPY backup.sh /usr/local/bin/backup.sh
COPY restore.sh /usr/local/bin/restore.sh
COPY mirror.sh /usr/local/bin/mirror.sh
COPY crontab /etc/crontabs/root
RUN chmod +x /usr/local/bin/*.sh
CMD ["crond", "-f", "-l", "8"]
