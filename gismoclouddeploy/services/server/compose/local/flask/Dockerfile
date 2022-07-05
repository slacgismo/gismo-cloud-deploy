

FROM python:3.8
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ARG CODES_FOLDER
ENV code_path  "../config/$CODES_FOLDER/requirements.txt"

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

# Requirements are installed here to ensure they will be cached.
# COPY ./server/requirements.txt /requirements.txt
# COPY ../config/$CODES_FOLDER/requirements.txt /requirements.txt
COPY $code_path /requirements.txt
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

RUN mkdir /app
WORKDIR /app



# copy project code


COPY ./server .

COPY ../config/code-templates/. ./project/

RUN chmod -R 755 ./project/

ENTRYPOINT ["/entrypoint"]
