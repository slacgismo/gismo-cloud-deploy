#!/bin/bash
#
# Install script for Amazon EC2 instance
# set -o errexit
# # fail exit if one of your pipe command fails
# set -o pipefail
# # exits if any of your variables is not set
# set -o nounset

sudo yum update -y
sudo yum install git -y
# install python 3.8
sudo yum install -y amazon-linux-extras
sudo amazon-linux-extras install python3.8 -y
echo 'install python3.8' > /home/ec2-user/installation.txt

# install aws cli
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install


# install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
echo 'install eksctl'  >> /home/ec2-user/installation.txt

echo 'install aws cli' >> /home/ec2-user/installation.txt
# install kubectl
export RELEASE=1.22.0 # check AWS to get the latest kubectl version
curl -LO https://storage.googleapis.com/kubernetes-release/release/v$RELEASE/bin/linux/amd64/kubectl
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
echo 'install kubectl' >> /home/ec2-user/installation.txt
# kubectl version --client  2>&1 | tee /home/ec2-user/installation.txt
# install docker
# amazon-linux-extras install docker -y
sudo yum install docker -y
# start docker server
sudo service docker start
sudo usermod -a -G docker ec2-user
# id ec2-user
# Reload a Linux user's group assignments to docker w/o logout
# newgrp docker
# check docker is on
sudo chkconfig docker on
# install docker-compose
sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
# check docker-compose verison
docker-compose version
echo 'install docker-compose' >> /home/ec2-user/installation.txt
# install gismo-cloud-deploy
git clone https://github.com/slacgismo/gismo-cloud-deploy.git /home/ec2-user/gismo-cloud-deploy
echo 'git clone gismo-cloud-deploy' >> /home/ec2-user/installation.txt
cd /home/ec2-user/gismo-cloud-deploy/
git fetch 
git switch feature/refactor0922

# sudo chmod +rwx /home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/services/config
# create virtual environment 
python3.8 -m venv venv
echo 'create virtual environment' >> /home/ec2-user/installation.txt
source ./venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install .
echo 'run pip install' >> /home/ec2-user/installation.txt

