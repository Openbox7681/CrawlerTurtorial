FROM debian:jessie-slim
MAINTAINER YuPingAOA <gisellewang@cyber00rn.org>

# ensure local python is preferred over distribution python
ENV PATH /usr/local/bin:$PATH

# http://bugs.python.org/issue19846
# "LANG=C" 
# At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
# "PYTHONIOENCODING"
# https://github.com/docker-library/python/issues/147
ENV LANG=C.UTF-8 \
  ES_IP=192.168.163.51 \
  ES_PORT=59200 \
  SCHED_PERIOD=30 \
  DEBIAN_FRONTEND=noninteractive

# runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
		ca-certificates \
		netbase \
		apt-utils \
	&& rm -rf /var/lib/apt/lists/*

RUN set -ex \
	\
	&& savedAptMark="$(apt-mark showmanual)" \
	&& apt-get update && apt-get install -y --no-install-recommends \
		build-essential \
		wget \
		python3 \
		python3-dev \
		python3-pip \
	&& rm -rf /var/lib/apt/lists/ \
	&& python3 -m pip install --upgrade pip setuptools wheel \
	&& mkdir /usr/local/cvedetails/

WORKDIR /usr/local/cvedetails/
# Install the python packages
COPY requirement.txt /usr/local/cvedetails/
RUN pip install -r requirement.txt

COPY . /usr/local/cvedetails/
RUN chmod +x /usr/local/cvedetails/run.sh

CMD ["sh", "-c", "/usr/local/cvedetails/run.sh"]







