# gismo-cloud-deployment

<table>
<tr>
  <td>Latest Release</td>
</tr>
<tr>
  <td>License</td>
</td>
</tr>
<tr>
  <td>Build Status</td>
</tr>
<tr>
    <td>Code Quality</td>
</tr>
<tr>
    <td>Test-Coverage</td>
</tr>
</table>

Tools for performing multiple common tasks on solar PV data signals by running multiple EC2 instances in parallel on AWS EKS platform.

---

## Install & Setup

### Quick start on AWS

1. Create a EC2 instance from a private [AMIs](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html) Image named as `pvinsight-eks-bastion-template`.
This image had been installed necessary dependenciues included:
- [kubectl](https://docs.aws.amazon.com/eks/latest/userguide/install-kubectl.html)
- [eksctl](https://docs.aws.amazon.com/eks/latest/userguide/eksctl.html)
- [awscli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [git](https://git-scm.com/) 
- [docker](https://docs.docker.com/)
- [docker-compose](https://docs.docker.com/compose/install/)
- [gismo-cloud-deploy project](https://github.com/slacgismo/gismo-cloud-deploy) 
   
1. Onec EC2 instance is running. Use ssh key to connect to the EC2 tunnel.

```bash
$ ssh -i <pem-file> ec2-user@<host-ip>
```

2. Set up AWS crednetial to access EKS and ECR.` (Reach out this project owner to get the correct AWS credentials).`
```bash
$ aws configure
```

~~~
AWS Access Key ID : 
AWS Secret Access Key: 
Default region name: 
Default output format [None]: 
~~~

1. Check if aws credentials vaild by listing aws s3 bucket command.
``` bash
$ aws s3 ls
```
4. Set up .env files for `cli` program usage.

```bash
$  touch ./gismoclouddeploy/services/cli/.env
```

The below is the sample variables in .env file, and replace `<your-aws-key> `with correct keys.
~~~
AWS_ACCESS_KEY_ID=<your-aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key-id>
AWS_DEFAULT_REGION=<your-aws-default-region>
SQS_URL=<your-sqs-url>
SQS_ARN=<your-sqs-arn>
SNS_TOPIC=<your-sns-topic>
~~~

4. The AMIs image should had pre-insatll all the python3 dependencies of `cli` in the environment.
In case users need to re-install the dependencies of `cli`. Please follow the below command:

- Create virutal environment.

```bash
$ cd ./gismoclouddeploy/services/cli
$ python3 -m venv venv
```

- Switch to virtual environment.
  
```bash
$ source ./venv/bin/activate
```

- Install python dependencies

```bash
(venv)$ pip install -r requirements.txt
```

- install pysetup

```bash
pip install e .
```

5. Under virutal environemnt, run process files command.

```bash
(venv)$ gcd run-files -n 1
```

### Command

The make command supports the following subcommands:

---

#### Process files command

```bash
(venv)$ gcd run-files [ --number | -n ] <0 ~ number> [ --deletenodes | -d ] [ --configfile | -f ] <filename> [--help]
```

* If processfile command with no option command `-n` . The program will process the defined files in `config.yaml` files.

* The process file command with option command`-n` followed with `integer number` will process the first `number` files in defined bucket.
If `number=0`, it processes all files in the buckets.

* The option command `[ --deletenodes | -d ]` will enable or disable deleting the eks nodes action after processing the files.
If `[ --deletenodes | -d ]` is assigned. The program will delete all eks nodes after processing.

* The option command `[ --configfile | -f ] [filename]` allows users to import configuration yaml files under `gismoclouddeploy/services/cli/config` folder.
If this option command is not assigned, the default configure file is `gismoclouddeploy/services/cli/config/config.yaml`.

Examples:

```bash
(venv)$ gcd run-files -n 1 -d -f test_config.yaml
```
The above command process the `first one` file of bucket defined in the `test_config.yaml`.  
Because `-d` optional command is assigned, the EKS nodes will be deleted after processing 

#### Other support command

- gcd --help
- gcd nodes-scale [integer_number] [--help]
- gcd check-nodes [--help]
- gcd read-dlq  [-e] [--help]
- gcd processlogs [--help]

The `nodes-scale` command allows developers to scale up or down the eks nodes.

The `check-nodes` command allows developers to check current nodes number.

The `read-dlq` command allows developers to check current nodes number. The `-e` option commmand enables or disables deleting messages after invoking this command.
The default value is `False`.

The `processlogs` command processes `logs.csv` files on AWS and draws the gantt plot in local folder.


The above command invokes function to process the first `1` file in the bucket defined in `gismoclouddeploy/services/cli/config/test_config.yaml` file.
The optional command `-d False` will disable deleting the eks nodes action after processing the files.

---

### Configuration files

Under `gismoclouddeploy/services/cli` folder, developers can modify parametes of the cli command tool.

1. The `general` configuration contains all the environement variables setting.
2. The `file-config` configuration contains all the config setting of run multiple files.
3. The `solardata` configuration contains all the parametes of solar-data-tools algorithm.
4. The `aws_config` configuration contains basic eks setting.Developer can defined number of nodes in EKS.
5. The `k8s_config` configuration contains basic kubernetes setting. Developers can define the replicas of worker in this files instead of modifying the `worker.deployment.yaml`.

### Kubernetes yaml files

All kubernetes deployment and service files are listed under `gismoclouddeploy/services/cli/k8s/k8s-aws` and `gismoclouddeploy/services/cli/k8s/k8s-local` folder. Developers can modify as their need.

### EKS configration yaml files

The create cluster command will create a eks cluster based on the configuration file in

```bash
$ make create-cluster
```

If user create cluster throug the `create-cluster` command based on the `cluster.yaml`. 
It's recommended to delete cluster through `delete-cluster`command based on the `cluster.yaml` file to avoid issue on AWS.  

```bash
$ make delete-cluster
```

---

### Build and push images on AWS.

The AWS EKS hosts services based on the ECR images. If developers modify any code inside server folder, developers have to build and push new imges to ECR to see the chnages.

In order to build new images to be used by Kubernetes, developers have to build and test images by docker-compose command. If the images are verified, developers can push images to ECR.
The EC2 basion instance has pre-installed `docker` and `docker-compose` command.

1. Build `worker` and `webapp` images through `docker-compose` command.

```bash
$ cd gismoclouddeploy/services
$ docker-compose build
```

2. Login to ECR and get validation

```bash
$ make ecr-validation
```

3. push `worker` and `webapp` to ECR
```bash
$ make push-worker
$ make push-server
```

4. Check k8s status by command:

```bash
kubectl get all
```
If kubernetes is running. Developers should see following output in the terminal.

~~~
NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/rabbitmq   0/1     1            0           20h
deployment.apps/redis      0/1     1            0           20h
deployment.apps/webapp     0/1     1            0           20h
deployment.apps/worker     0/1     1            0           20h
~~~

If no k8s config files had been apply, please apply k8s yaml files by command:

```bash
$ cd gismoclouddeploy/services/cli/k8s/k8s-aws
$ kubectl apply -f .
```

If `worker` and `webapp` images had been applied. Developers can rollout and restart image by command:

```bash
$ make rollout
```

---

### Setup, build and push image in the local machine

#### local Installation

1. Download git repository

```bash
$ git clone https://github.com/slacgismo/gismo-cloud-deploy.git
```

2. Install the dependencies

```bash
$ cd gismo-cloud-deploy/services/cli
$ python3 -m venv venv
$ source ./venv/bin/activate
$ pip install -r requirements.txt
```

3). Developers are allowed to use `docker-compose` or `kubernetes` to manage the system

#### Using `docker-compose`
Before using docker to host local services, please install docker by following the instructions [Docker Link](https://docs.docker.com/get-docker/).

Setup AWS credentials for Kubernetes
```
touch ./gismoclouddeploy/services/server/.env/.dev-sample
```
Replace the environemnt variables inside `<xxx-xxx-xxx>`.

~~~
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key-id>
AWS_DEFAULT_REGION=<region>
~~~

#### Include MOSEK licence

 MOSEK is a commercial software package. The included YAML file will install MOSEK for you, but you will still need to obtain a license. More information is available here:

* [mosek](https://www.mosek.com/resources/getting-started/)
* [Free 30-day trial](https://www.mosek.com/products/trial/)
* [Personal academic license](https://www.mosek.com/products/academic-licenses/)

Include `MOSEK` licence file `mosek.lic` under folder `./gismoclouddeploy/services/server/licence`. The licence file is required to build docker images. 

Staring docker images by command

```bash
$ cd gismo-cloud-deploy/gismoclouddeploy/services
$ docker-compose up --build
```

---

#### Using `Kubernetes`

Once the docker images were build. Apply `kubernetes` setting in `./gismoclouddeploy/services/cli/k8s/k8s-local` folder by command.

```bash
$ kubectl apply -f .
```

#### Push to AWS ECR

Setup AWS credentials

```bash
$ aws configure
```

Login AWS ECR

```bash
$ cd ./gismoclouddeploy/services
$ make ecr-validation
```

Push images to ECR
```bash
$ make push-server
$ make push-worker
```
---

### Testing

### Test cli 

Run pytest coverage in cli

```bash
$ cd ./gismoclouddeploy/services/cli
$ pytest --cov=.
```

#### Test docker image

Run pytest in docker image

```bash
$ docker-compose exec web pytest 
```

Get test coverage in docker image

```bash
$ docker-compose exec web pytest --cov=.
```

---

### EKS Setting
method 1
eksctl create iamidentitymapping --cluster  <clusterName> --region=<region> --arn arn:aws:iam::123456:role/testing --group system:masters --username admin
method 2
kubectl edit configmap aws-auth -n kube-system
mapUsers: |
  - userarn: arn:aws:iam::[account_id]:root
    groups:
    - system:masters

---

### System diagram
![System diagram](./Solar-data-tools-AWS.png)

## Usage

## Contributors



## Test Coverage

## Versioning

We use [Semantic Versioning](http://semver.org/) for versioning. For the versions available, see the [tags on this repository].

## Authors

## License

This project is licensed under the BSD 2-Clause License - see the [LICENSE](LICENSE) file for details


