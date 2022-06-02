#!/bin/bash
#
# Install script for Amazon EC2 instance 

# install git 
yum update -y 
yum install git
# install python 3.8
yum install -y amazon-linux-extras
amazon-linux-extras install python3.8

# install eksctl 
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
mv /tmp/eksctl /usr/local/bin

# install aws cli
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
# install kubectl 
export RELEASE=1.22.0
curl -LO https://storage.googleapis.com/kubernetes-release/release/v$RELEASE/bin/linux/amd64/kubectl
chmod +x ./kubectl
mv ./kubectl /usr/local/bin/kubectl
# install docker


# start docker server
# install docker-compose