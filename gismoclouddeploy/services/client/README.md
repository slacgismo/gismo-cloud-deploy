# Giamo cloud deployment command line interface 
## System diagram



## Local development

### Installation
1). Download git repository
~~~
git clone https://github.com/slacgismo/gismo-cloud-deploy.git
~~~
2). Install the dependencies
~~~
cd gismo-cloud-deploy/services/client
python3 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
~~~
3). Developers are allowed to use `docker-compose` or `kubernetes` to manage the system

Using `docker-compose`
Staring docker images by command
~~~
cd gismo-cloud-deploy/services
docker-compose up --build
~~~
Check if images is exist


using `kubernetes`



## AWS development
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
ssh -i <pem-file> ec2-user@<host-ip>
~~~
3. Download git repository in Bastion instance

~~~
cd /usr/src/app
git clone https://github.com/slacgismo/gismo-cloud-deploy.git
cd gismo-cloud-deploy
~~~

4. CLI installation
~~~
make install-ec2
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

- make run-files [-n]
- make list-files 
- make run-folder 
- make help
- make version


### Configuration files

Under `config` folder, developers can change parametes of the project. 
1). The `general.yaml` contains all the environement variables setting.
2). The `run-files.yaml` contains all the config setting of run multiple files. Option command `[-n]` will run all files in the bucket listed in  `run-files.yaml` file. 
3). The `run-foler.yaml` constins all the config setting of run multiple folders.
4). The `sdt-params.yaml` contains the parameters setting of solardatatools `ataHandler.run_pipeline`. 