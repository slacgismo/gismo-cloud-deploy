

# FROM debian:11
# RUN apt-get -q update

# RUN apt-get install tzdata -y
# RUN  apt-get install curl -y
# RUN apt-get install apt-utils -y

# RUN apt-get -q install software-properties-common -y
# RUN apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev -y

# RUN apt-get -q install git -y
# RUN apt-get -q install unzip -y
# RUN apt-get -q install autoconf -y
# RUN apt-get -q install libtool -y
# RUN apt-get -q install g++ -y
# RUN apt-get -q install cmake -y
# RUN apt-get -q install flex -y
# RUN apt-get -q install bison -y
# RUN apt-get -q install libcurl4-gnutls-dev -y
# RUN apt-get -q install subversion -y
# RUN apt-get -q install util-linux -y
# RUN apt-get install liblzma-dev -y
# RUN apt-get install libbz2-dev -y
# RUN apt-get install libncursesw5-dev -y
# RUN apt-get install xz-utils -y

# # install gdal
# RUN apt-get install libgdal-dev -y

# WORKDIR /usr/local/src

# RUN git clone -b develop-fix-debian-11-setup-arm https://github.com/slacgismo/gridlabd.git
# WORKDIR /usr/local/src/gridlabd
# RUN ./install.sh -t -v
FROM python:3.8

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update \
  # dependencies for building Python packages
  && apt-get install -y build-essential \
  # psycopg2 dependencies
  && apt-get install -y libpq-dev \
  # Additional dependencies
  && apt-get install -y telnet netcat \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*
RUN apt update && apt install libblas3 liblapack3 liblapack-dev libblas-dev cmake -y
RUN apt install libhdf5-dev -y

# # Requirements are installed here to ensure they will be cached.
COPY ./server/requirements.txt /requirements.txt
# COPY ../config/code-templates/requirements.txt /requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /requirements.txt

COPY ./server/compose/local/flask/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./server/compose/local/flask/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

COPY ./server/compose/local/flask/celery/worker/start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker


# WORKDIR /app

# RUN mkdir /app
WORKDIR /app



# # copy project code


COPY ./server .

COPY ../config/code-templates/. ./project/

RUN chmod -R 755 ./project/

ENTRYPOINT ["/entrypoint"]
