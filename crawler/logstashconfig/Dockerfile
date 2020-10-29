FROM logstash:6.7.1

WORKDIR /usr/share/logstash/config/
# Install the python packages
COPY k8ssync.config /usr/share/logstash/config/

CMD ["logstash", "-f" , "k8ssync.config"]