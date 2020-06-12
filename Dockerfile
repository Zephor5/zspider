FROM python:3.8-slim-buster AS base

USER root
ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1
ENV DEBIAN_FRONTEND=noninteractive
RUN mkdir -p /usr/share/man/man1
RUN apt-get update
RUN apt-get install -y apt-utils
RUN apt-get install -y wget curl gnupg sudo gcc memcached firefox-esr
RUN wget -qO - https://www.mongodb.org/static/pgp/server-4.2.asc | apt-key add -
RUN echo "deb http://repo.mongodb.org/apt/debian buster/mongodb-org/4.2 main" | tee /etc/apt/sources.list.d/mongodb-org-4.2.list
RUN echo "deb https://packages.erlang-solutions.com/debian buster contrib" | tee /etc/apt/sources.list.d/erlang.list
RUN wget -qO - https://packages.erlang-solutions.com/debian/erlang_solutions.asc | apt-key add -
RUN wget -qO - https://packagecloud.io/rabbitmq/rabbitmq-server/gpgkey | apt-key add -
RUN curl -s https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-server/script.deb.sh | bash
RUN apt-get install -y mongodb-org  rabbitmq-server
RUN wget -qO /root/geckodriver-v0.26.0-linux64.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz
RUN tar zxf /root/geckodriver-v0.26.0-linux64.tar.gz  -C /usr/local/bin/

RUN useradd --create-home app
RUN usermod -a -G sudo app
RUN sed -i '/^%sudo/c\%sudo ALL=(ALL:ALL) NOPASSWD:ALL' /etc/sudoers

USER app
RUN mkdir -p /home/app/zspider
COPY requirements.txt /home/app/zspider
RUN pip install -r /home/app/zspider/requirements.txt
RUN rm -rf /home/app/zspider/requirements.txt
WORKDIR /home/app/zspider

CMD ["bash", "-c", "mongod --fork -f /etc/mongod.conf && sudo service rabbitmq-server start && sudo service memcached start && pip install -r /home/app/zspider/requirements.txt && echo Container ready for use. Feel free to ctrl-c! Container will stick around. && while true ; do sleep 3600; done"]
