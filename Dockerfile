FROM debian:11

RUN apt-get -q update

RUN apt-get install tzdata -y
RUN  apt-get install curl -y
RUN apt-get install apt-utils -y

RUN apt-get -q install software-properties-common -y
RUN apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev -y

RUN apt-get -q install git -y
RUN apt-get -q install unzip -y
RUN apt-get -q install autoconf -y
RUN apt-get -q install libtool -y
RUN apt-get -q install g++ -y
RUN apt-get -q install cmake -y
RUN apt-get -q install flex -y
RUN apt-get -q install bison -y
RUN apt-get -q install libcurl4-gnutls-dev -y
RUN apt-get -q install subversion -y
RUN apt-get -q install util-linux -y
RUN apt-get install liblzma-dev -y
RUN apt-get install libbz2-dev -y
RUN apt-get install libncursesw5-dev -y
RUN apt-get install xz-utils -y

# install gdal
RUN apt-get install libgdal-dev -y

WORKDIR /usr/local/src
# download model

# RUN git clone -b develop-add-aws-install https://github.com/slacgismo/gridlabd.git
# WORKDIR /usr/local/src/gridlabd



# RUN ./install.sh -t -v
# RUN autoreconf -isf && ./configure
# RUN make -j6 system


