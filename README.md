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

## Install & Setup
### Quick start on AWS

1. SSH to EC2 tunnel.

```bash
$ ssh -i <pem-file> ec2-user@<host-ip>
```

2. Set up .env files for `cli` program usage.

```bash
$  touch ./gismoclouddeploy/services/cli/.env
```

The below is the sample variables in .env file.
~~~
AWS_ACCESS_KEY_ID=<your-aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key-id>
AWS_DEFAULT_REGION=<your-aws-default-region>
SQS_URL=<your-sqs-url>
SQS_ARN=<your-sqs-arn>
SNS_TOPIC=<your-sns-topic>
~~~

4. Create and activate python virtual environment.
   
```bash
$ cd ./gismoclouddeploy/services/cli
$ python3 -m venv venv
$ source ./venv/bin/activate
```
5. Install python dependencise packages.

```bash
(venv)$ pip install -r requirements.txt
```

6. Under virutal environemnt, run process files command.

```bash
(venv)$ ./gismoclouddeploy/services/cli
(venv)$ python3 main.py run-files -n 1
```
### Command

The make command supports the following subcommands:

#### Process files command

```bash
(venv)$ python3 main.py run-files [ --number | -n ] [0 ~ number] [ --deletenodes | -d ] [ True | False ] [ --configfile | -f ] [filename]
```
If processfile command with no option command `-n` . The program will process the defined files in `config.yaml` files.

The process file command with option command`-n` followed with `integer number` will process the first `number` files in defined bucket.
If `number=0`, it processes all files in the buckets.

The option command `[ --deletenodes | -d ] [ True | False ]` will enable or disable deleting the eks nodes action after processing the files.
If `[ --deletenodes | -d ]` is not assigned, the default value is `True`. The program will delete all eks nodes after processing.

The option command `[ --configfile | -f ] [filename]` allows users to import configuration yaml files under `gismoclouddeploy/services/cli/config` folder.
If this option command is not assigned, the default configure file is `gismoclouddeploy/services/cli/config/config.yaml`.

Examples:

```bash
(venv)$ python3 main.py run-files -n 1 -d False -f test_config.yaml
```

#### Other support command

- python3 main.py --help
- python3 main.py nodes-scale [integer_number]
- python3 main.py check-nodes
- python3 main.py read-dlq  [-e] [ True | False ]
- python3 main.py processlogs


- The `nodes-scale` command allows developers to scale up or down the eks nodes.
- The `check-nodes` command allows developers to check current nodes number.
- The `read-dlq` command allows developers to check current nodes number. The `-e [ True | False ]` option commmand enables or disables deleting messages after invoking this command.
- The `processlogs` command processes `logs.csv` files on AWS and draws the gantt plot in local folder.


The above command invokes function to process the first `1` file in the bucket defined in `gismoclouddeploy/services/cli/config/test_config.yaml` file.
The optional command `-d False` will disable deleting the eks nodes action after processing the files.

### Configuration files

Under `gismoclouddeploy/services/cli` folder, developers can modify parametes of the cli command tool.
1). The `general` configuration contains all the environement variables setting.
2). The `file-config` configuration contains all the config setting of run multiple files.
3). The `solardata` configuration contains all the parametes of solar-data-tools algorithm.
4). The `aws_config` configuration contains basic eks setting.Developer can defined number of nodes in EKS.
5). The `k8s_config` configuration contains basic kubernetes setting. Developers can define the replicas of worker in this files instead of modifying the `worker.deployment.yaml`.

### Kubernetes yaml files
All kubernetes deployment and service files are listed under `gismoclouddeploy/services/cli/k8s/k8s-aws` and `gismoclouddeploy/services/cli/k8s/k8s-local` folder. Developers can modify as their need.

### EKS configration yaml files
The create cluster command will create a eks cluster based on the configuration file in `gismoclouddeploy/services/cli/k8s/eks/cluster.yaml`.
```bash
$ make create-cluster
```

If user create cluster throug the `create-cluster` command based on the `cluster.yaml`. 
It's recommended to delete cluster through `delete-cluster`command based on the `cluster.yaml` file to avoid issue on AWS.  
```bash
$ make delete-cluster
```
### Build and push images on AWS.
The AWS EKS hosts services based on the ECR images. In order to build new images to be used by Kubernetes, developers have to build and test images by docker-compose command. If the images are verified, developers can push images to ECR.
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

4. Apply new images to kubernetes.
Check k8s status by command:

```bash
kubectl get all
```

If no k8s config files had been apply, please apply k8s yaml files by command:

```bash
$ cd gismoclouddeploy/services/cli/k8s/k8s-aws
$ kubectl apply -f .
```

If 'worker' and 'webapp' images had been applied. Developer can rollout and restart image by command:

```bash
$ make rollout
```


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
#### Using `Kubernetes`
Once the docker images were build. Apply `kubernetes` setting in `./gismoclouddeploy/services/cli/k8s/k8s-local` folder by command.
```bash
$ kubectl apply -f .
```
#### Push to AWS ECR


Setup AWS credentials
```bash
$ export AWS_ACCESS_KEY_ID=<xxxxxxx>
$ export AWS_SECRET_ACCESS_KEY=<xxxxxxx>
$ export AWS_DEFAULT_REGION=<xxxxxxxxx>
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


### EKS Setting
method 1
eksctl create iamidentitymapping --cluster  <clusterName> --region=<region> --arn arn:aws:iam::123456:role/testing --group system:masters --username admin
method 2
kubectl edit configmap aws-auth -n kube-system
mapUsers: |
  - userarn: arn:aws:iam::[account_id]:root
    groups:
    - system:masters
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


