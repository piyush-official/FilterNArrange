FROM redpandadata/redpanda:latest

USER root
COPY create-topics.sh /usr/local/bin/create-topics.sh
RUN chmod +x /usr/local/bin/create-topics.sh

ENTRYPOINT ["/usr/local/bin/create-topics.sh"]
