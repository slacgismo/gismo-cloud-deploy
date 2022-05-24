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

3. Set up aws credential key for kubernetes usage. 

```bash
$ kubectl create secret generic aws-access-key-id --from-literal aws-access-key-id=<your AWS access key>
```
```bash
$ kubectl create secret generic aws-secret-key --from-literal aws-secret-access-key =<your AWS secret key>
```

4. Create and activate python virtual environment.
   
```bash
$ cd ./gismoclouddeploy/services/cli
$ python3 -m venv venv
$ source ./venv/bin/activate
```
5. Install python dependencise packages.

```bash
$ pip install -r requirements.txt
```

6. Under virutal environemnt, run process files command.

```bash
(venv)$ ./gismoclouddeploy/services/cli
(venv)$ python3 main.py run-files -n 1
```
### Command

The make command supports the following subcommands:

Process files command.

```bash
(venv)$ python3 main.py run-files -n <number | n >
```
If processfile command with no option command `-n` . The program will process the defined files in `config.yaml` files.

The process file command with option command`-n` followed with `number` will process the first `number` files in defined bucket.

The process file command with option command `-n` followed with `n` will process the all files in defined bucket.

### Configuration files

Under `gismoclouddeploy/services/cli` folder, developers can modify parametes of the cli command tool.
1). The `general` configuration contains all the environement variables setting.
2). The `file-config` configuration contains all the config setting of run multiple files.
3). The `solardata` configuration contains all the parametes of solar-data-tools algorithm.
4). The `aws_config` configuration contains basic eks setting.Developer can defined number of nodes in EKS.
5). The `k8s_config` configuration contains basic kubernetes setting. Developers can define the replicas of worker in this files instead of modifying the `worker.deployment.yaml`.

### Kubernetes yaml files
All kubernetes deployment and service files are listed under `gismoclouddeploy/services/cli/k8s/k8s-aws` and `gismoclouddeploy/services/cli/k8s/k8s-local` folder. Developers can modify as their need.



### Setup, build and push image in the local machine

The AWS EKS hosts services based on the ECR images. In order to build new images to be used by Kubernetes, developers have to build and test images by docker-compose command. If the images are verified, developers can push images to ECR.
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
