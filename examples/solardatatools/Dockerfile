FROM python:3.8

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ARG CODES_FOLDER

ARG TARGET_PATH_OF_UPLOAD_FILE
ARG SOURCE_PATH_OF_UPLOAD_FILE

# code template path
ENV code_path  "../$CODES_FOLDER"
ENV project_path "../$CODES_FOLDER"
# license path
ENV source_path_of_upload_file "../$CODES_FOLDER/$SOURCE_PATH_OF_UPLOAD_FILE" 



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

# copey requirements
COPY $project_path/requirements.txt /requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /requirements.txt

# copy specific file to images 

COPY ./gismoclouddeploy/server/compose/local/flask/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY /gismoclouddeploy/server/compose/local/flask/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

COPY ./gismoclouddeploy/server/compose/local/flask/celery/worker/start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker



COPY ./gismoclouddeploy/server/compose/local/flask/celery/flower/start /start-flower
RUN sed -i 's/\r$//g' /start-flower
RUN chmod +x /start-flower



# copy license
COPY $source_path_of_upload_file/  $TARGET_PATH_OF_UPLOAD_FILE


# WORKDIR /app

RUN mkdir /app
WORKDIR /app



# copy project code


COPY ./gismoclouddeploy/server .

COPY $code_path ./project/

RUN chmod -R 755 ./project/

ENTRYPOINT ["/entrypoint"]
