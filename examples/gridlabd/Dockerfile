
FROM debian:11

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ARG CODES_FOLDER

ARG TARGET_PATH_OF_UPLOAD_FILE
ARG SOURCE_PATH_OF_UPLOAD_FILE

# code template path
ENV code_path  "../$CODES_FOLDER"
ENV project_path "../$CODES_FOLDER"
# license path
ENV source_path_of_upload_file "./$CODES_FOLDER/$SOURCE_PATH_OF_UPLOAD_FILE"


RUN apt-get -q update
RUN apt-get -q install git -y
RUN apt-get -q install sudo -y
WORKDIR /usr/local/src
# download model
RUN git clone -b develop-add-aws-install https://github.com/slacgismo/gridlabd.git
WORKDIR /usr/local/src/gridlabd
RUN ./install.sh -t -v
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
# # download model

# RUN git clone -b develop-add-aws-install https://github.com/slacgismo/gridlabd.git
# WORKDIR /usr/local/src/gridlabd



# RUN ./install.sh -t -v
# RUN autoreconf -isf && ./configure
# RUN make -j6 system


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

# WORKDIR /app

# RUN mkdir /app
WORKDIR /app

# copy project code

COPY ./server .

COPY $code_path ./project/
RUN chmod -R 755 ./project/


ENTRYPOINT ["/entrypoint"]
