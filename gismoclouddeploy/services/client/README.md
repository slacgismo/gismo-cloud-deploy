# Giamo cloud deployment command line interface 
## System diagram

## Quick Start

### Installation




### Deployment to EC2 and EKS
1.If (ssh tunnel) bastion instance is not created, deploying bastion instance on AWS by command as below.
~~~
cd deploy
make tf-init
make tf-plan
make tf-apply
~~~

2. SSH to bastion 
~~~
ssh -i <pem> ec2-user@<host>
~~~
3. Download git repository in Bastion instance

~~~
cd /usr/src/app
git clone https://github.com/slacgismo/gismo-cloud-deploy.git
cd gismo-cloud-deploy
~~~

4. If EKS is not created, run command as below:
~~~
eksctl create cluster --name <cluster-name> --nodes-min=1
~~~

5. Apply kubernetes configuration file
~~~
cd /usr/src/app/gismo-cloud-deploy/k8s/k8s-aws
kubectl apply -f .
~~~

### Command 

The make command supports the following subcommands:

- make run-files 
- make run-folder 
- make help
- make version