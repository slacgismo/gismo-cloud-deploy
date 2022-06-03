#!/bin/bash
#
# Install script for Amazon EC2 instance 
set -o errexit
# fail exit if one of your pipe command fails
set -o pipefail
# exits if any of your variables is not set
set -o nounset


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
export RELEASE=1.22.0 # check AWS to get the latest kubectl version
curl -LO https://storage.googleapis.com/kubernetes-release/release/v$RELEASE/bin/linux/amd64/kubectl
chmod +x ./kubectl
mv ./kubectl /usr/local/bin/kubectl
# check kubcetl version
kubectl version --client
# install docker
amazon-linux-extras install docker
# start docker server
service docker start
usermod -a -G docker ec2-user
# check docker is on 
chkconfig docker on
# install docker-compose
sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
# check docker-compose verison
docker-compose version