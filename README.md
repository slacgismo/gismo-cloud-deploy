# gismo-cloud-deployment

<table>
<tr>
  <td>Latest Release</td>
  <td>
    <a href="https://img.shields.io/github/v/release/slacgismo/gismo-cloud-deploy?include_prereleases">
        <img src="https://img.shields.io/github/v/release/slacgismo/gismo-cloud-deploy?include_prereleases" alt="Release" />
    </a>
    <a href="https://github.com/slacgismo/gismo-cloud-deploy/tags">
        <img src="https://img.shields.io/github/v/tag/slacgismo/gismo-cloud-deploy" alt="tags" />
    </a>
  </td>
</tr>
<tr>
  <td>License</td>
</td>
</tr>
<tr>
  <td>Build Status</td>
  <td>
    <a href="https://img.shields.io/github/workflow/status/slacgismo/gismo-cloud-deploy/Build%20And%20Test">
        <img src="https://img.shields.io/github/workflow/status/slacgismo/gismo-cloud-deploy/Build%20And%20Test" alt="Build And Test status" />
    </a>
    <a href="https://img.shields.io/github/workflow/status/slacgismo/gismo-cloud-deploy/Deploy?label=deploy">
        <img src="https://img.shields.io/github/workflow/status/slacgismo/gismo-cloud-deploy/Deploy?label=deploy" alt="Deploy status" />
    </a>
  </td>
</tr>
</table>

Tools for performing multiple common tasks on solar PV data signals by running various EC2 instances in parallel on the AWS EKS platform.

---

## Install & Setup

### Quick start on AWS

1. Login to `slac-gismo` AWS account.
2. Go to `EC2` page in `us-east-2` region and select `AMIs` in `Images` tab in left option menu.
3. Select the template called `pvinsight-eks-bastion-template` from AMIs private image and click `Lunach instance from AMIs`.
This image had been installed necessary dependenciues included:
- [kubectl](https://docs.aws.amazon.com/eks/latest/userguide/install-kubectl.html)
- [eksctl](https://docs.aws.amazon.com/eks/latest/userguide/eksctl.html)
- [awscli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [git](https://git-scm.com/)
- [docker](https://docs.docker.com/)
- [docker-compose](https://docs.docker.com/compose/install/)
- [gismo-cloud-deploy project](https://github.com/slacgismo/gismo-cloud-deploy)

#### Launch instance notes

- This program runs in multiple threads. Therefore, please select at least `2 vcpus` instance type.  Under `Instance types`, select `t2.large` type is recommended.

- Under `Configure Storage`, select the volume of the instance should be `12 GB` at least.

- Under `Key pair(login)` option, create a new key pair or use your existing key pair.

- Click `Lunach instance` button to lanch a EC2 instance.

- After the EC2 instance is launched, under the `Tags`, create a tag called: `project:pvinsight` for budget management purpose.

1. Once the EC2 instance is running, use your ssh key to connect to the EC2 tunnel in your local terminal. Get the ip address from the `Public IPv4 address` in `Detail` tabs.
 - Change `pem-file` permission.

```bash
cd /path-of-pem-file
chmod 400 <pem-file>
```
 - Connect to the EC2
```bash
ssh -i <path/pem-file> ec2-user@<Public IPv4 address>
```

2. Once inside the instance, set up AWS credential to access EKS and ECR. **_NOTE:_** `(Reach out this project's owner to get the AWS credentials).`

```bash
$ aws configure
```

~~~
AWS Access Key ID :
AWS Secret Access Key:
Default region name:
Default output format [None]:
~~~

3. Check if aws credentials are vaild by listing aws s3 bucket command.

``` bash
aws s3 ls
```

4. Change directory to `gismo-cloud-deploy`. Pull down latest `main` repository from [gismo-cloud-deploy.git](git@github.com:slacgismo/gismo-cloud-deploy.git), and run `git pull` command.

5. Set up .env files for `cli` program usage.

```bash
touch ./gismoclouddeploy/services/cli/.env
```

Below are the sample variables in the .env file, and replace `<your-aws-key>` with the correct keys.
~~~
AWS_ACCESS_KEY_ID=<your-aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key-id>
AWS_DEFAULT_REGION=<your-aws-default-region>
SQS_URL=<your-sqs-url>
DLQ_URL=<your-dlq-url>
SNS_TOPIC=<your-sns-topic>
~~~

6. The AMIs image should have pre-install all the python3 dependencies of `cli` in the environment.
In case users need to re-install the dependencies of `cli`. Please follow the below command:

- The python virtual environemnt was created Create virutal environment.

- Activate the virtual environment.

```bash
source ./venv/bin/activate
```

- Upgrade pip

```bash
pip install --upgrage pip
```

- Update dependencies.

```bash
pip install -r requirements.txt
```

- **_NOTE:_** If virtual environment was not created, please create the virtual environemnt first.

```bash
cd ./gismoclouddeploy/services/cli
```

```bash
python3.8 -m venv venv
```

Upgrade pip

```bash
pip install --upgrage pip
```

Install dependencies

```bash
pip install -r requirements.txt
```

- Install python dependencies

```bash
(venv)$ pip install -r requirements.txt
```

- install pysetup

```bash
pip install e .
```

7.  Check the EKS cluster is existing.

```bash
eksctl get cluster
```

If cluster is existing, it returns the output below.

~~~
NAME		REGION		EKSCTL CREATED
gcd-eks-cluster	us-east-2	True
~~~

If cluster is not existing, please follow `EKS configuration yaml files` section to create a cluster first.

9.  Under the virutal environemnt, run `run-files` command to test it.

```bash
(venv)$ gcd run-files -n 1 -d
```

Read below for more informations.

---

## Command

The gcd command supports the following subcommands:

### run-files command

~~~
Usage: gcd run-files [OPTIONS]

Run Process Files

Options:
  -n, --number TEXT       Process the first n files in the defined bucket of
                          config.yaml.  If number is None, this application
                          process defined files in config.yaml. If number is
                          0,this application processs all files in the defined
                          bucket in config.yaml. If number is an integer, this
                          applicaion process the first `number` files in the
                          defined bucket in config.yaml.

  -d, --deletenodes BOOL  Enable deleting eks node after complete this
                          application. Default value is False.

  -f, --configfile TEXT   Assign custom config files, Default files name is
                          ./config/config.yaml

  -r, --rollout  BOOL     Enable deleting current k8s deployment services and
                          re-deployment services. Default value is False

  -i, --imagetag TEXT     Specifiy the image tag. Default value is 'latest'
                          This option command did not work with [ -b | --build ] option command.

  -do, --docker  BOOL     Default value is False. If it is True, the services
                          run in docker environment. Otherwise, the services run
                          in kubernetes◊ environment.

  -l, --local    BOOL     Default value is False. If it is True, define running
                          environemnt in local. Otherwiser, define running
                          environemt on AWS

  -b, --build             Build a temp image and use it. If on AWS k8s
                          environment,     build and push image to ECR with
                          temp image tag. These images will be deleted after
                          used.    If you would like to preserve images, please
                          use build-image command instead

  --help                  Show this message and exit.
~~~

* If you use default `run-files` command with no option, the program processes the files defined in the `config.yaml` file with `solar-data-tools` algorithm, and generated the results that saved in a file defined in `config.yaml` file.

* The process file command with option command`-n` followed with an `integer number` will process the first `number` files in the defined bucket. (eg. `-n 10` will process the first 10 files in defined bucket )
If `number=0`, it processes all files in the buckets.

* The option command `[ --configfile | -f ] [filename]`  imports custom configuration yaml files under `gismoclouddeploy/services/cli/config` folder.
If this [-f] option command is not assigned, the default configure file is `gismoclouddeploy/services/cli/config/config.yaml`.

* The option command `[ --build | -b ] ` build custom images based on `./gismoclouddeply/services/cli/server` and `./gismoclouddeply/services/cli/config/code-templates` folder.
  If your environment is on AWS, this option command builds and pushs `worker` and `server` service images to AWS ECR with temporary image tag.
  This temporary tag will be deleted after this applicaiton completes processing. Please read section [Build and push images](#build-and-push-images) to get more information.



Examples:

```bash
(venv)$ gcd run-files -b -n 1 -d -f test_config.yaml
```

Command details:

On the AWS environment ,the above command starts the following processes:

1. Since [-f] option commnad is specified, this application imports `./gismoclouddeply/services/cli/config/test_config.yaml` to replace default `./gismoclouddeply/services/cli/config/config.yaml` file.
2. The AWS EKS fires up mutiple ec2-instandes(nodes) according to the custom config file.
3. This application builds `server` and `worker` images from `./gismoclouddeply/services/cli/server` and `./gismoclouddeply/services/cli/config/code-templates` folder with a temporary image tag according to its hostname.
4. After buidling images is completed, this application pushes those two images to AWS ECR with temporary images tage, such as `worker:my-hostname` and `server:my-hostname`.
5. This AWS EKS pull down those temporary images and mounted into generated nodes.
6. The `woker` service is the major service to process time consuming tasks, such as analyizing data with defined algorithm. In order to processing the time consuming tasks in parallel on AWS, developer can increase the `replicas` of the `worker`. This application spreads multiple `worker` services evenly among generated `nodes`(ec2-instances) of AWS EKS.
7. Since [-n] <1> option command is specified, this application starts to proccess the `first 1` file of the defined buket in `test_config.yaml`.
8. After the process is done, this application deletes temporary images on ECR.
**NOTE** If developers would like to preserve builds images, please use `gcd build-images` command instead.
9.  Since [-d] option command is specified, this application deletes all nodes(ec2-instances) of AWS EKS.

### Other support command

- gcd --help
- gcd nodes-scale [integer_number] [--help]
- gcd build-images [-t|--tag] <image_tag> [-p|--push] [--help]
- gcd check-nodes [--help]
- gcd combine-files [--help]
- gcd read-dlq  [-e] [--help]
- gcd processlogs [--help]

The `nodes-scale` command scales up or down the eks nodes.

The `build-images` command builds image from `docker-compose`. Please read this [Build and push images](#build-and-push-images) to get more information.

The `check-nodes` command checks current nodes number.

The `read-dlq` command checks current DLQ(dead letter queue) on AWS. The `-e` option commmand enables or disables deleting messages after invoking this command.
The default value is `False`.

The `processlogs` command processes `logs.csv` files on AWS and draws the gantt plot in local folder.

The `combine-fies` command generates saved data file from the data of prvious run-time. During initializtion, this application erases any cached data of previous processing.
If the previous process stoped for any reasons before it outputs saved data, this command helps to output those cached data from previous processing.

---
### Configuration files


Under `gismoclouddeploy/services/cli` folder, developers can modify parametes of the cli command tool.

1. The `general` section contains all the environement variables settings.
2. The `file_config` section contains all the config settings to run multiple files.
3. The `algorithms` section contains all algorithms setting. The algorithm's parametes are defined under its name.
   The `algorithm` name should match the `selected_algorithm` in `file_config`.
4. The `aws_config` section contains basic eks settings. Developers can define the number of nodes in EKS.
5. The `k8s_config` section contains basic kubernetes setting. Developers can define the replicas of workers in this file instead of modifying the `worker.deployment.yaml`.
6. The `output` section contains the setting of all output file names, paths and target bucket.

### Kubernetes yaml files

All kubernetes deployment and service files are listed under `gismoclouddeploy/services/cli/config/k8s` folder. Developers can modify it if necessary.

### EKS configuration yaml files

The create cluster command will create an EKS cluster based on the configuration file in `gismoclouddeploy/services/cli/config/eks/cluster.yaml`.

```bash
make create-cluster
```

If users create a cluster based on the `cluster.yaml` file, and if they need to delete the cluster later, it's recommended to delete the cluster through `delete-cluster`command based on the `cluster.yaml` file to avoid issue on AWS.

```bash
make delete-cluster
```

---

#### Include MOSEK licence to build docker image

 MOSEK is a commercial software package. The included YAML file will install MOSEK for you, but you will still need to obtain a license. More information is available here:

* [mosek](https://www.mosek.com/resources/getting-started/)
* [Free 30-day trial](https://www.mosek.com/products/trial/)
* [Personal academic license](https://www.mosek.com/products/academic-licenses/)

Include `MOSEK` licence file `mosek.lic` under folder `./gismoclouddeploy/services/server/licence`. The licence file is required to prove you have the licence.


## Build and push images

The AWS EKS hosts services based on the ECR images. If developers modify any code inside the server folder, developers have to build and push new images to ECR to see the changes.

In order to build images, developers have to use `build-images` command. This command is a python wrapper function to invoke `docker-compose build` command in shell.

~~~
Usage: main.py build-images [OPTIONS]

  Build image from docker-compose and push to ECR

Options:
  -t, --tag TEXT    Rollout and restart of webapp and worker pod of kubernetes

  -p, --push BOOL   Is pushing image to AWS ECR : Default is False
  --help            Show this message and exit.
~~~

Example:

```bash
gcd build-image  -t test -p
```

The above example command execute `build-image` command, and tag built images with tag `test`.
In this example, two images with build and tag as `worker:test` and `server:test`.Since `-p` optin command is enabled, the built images with tag are pushed to AWS ECR.

> **_NOTE:_** The image with `latest` and `develop` tags are pushed from `Github Action` CI/CD pipeline to AWS ECR.
> Developers cannot push images with `latest` and `develop` tags from local to AWS ECR.

---


## Testing

### Test cli

Run pytest coverage in cli

```bash
cd ./gismoclouddeploy/services/cli
pytest
```

#### Test docker image

Run pytest in docker image

```bash
$ docker-compose exec web pytest
```

Get test coverage in docker image

```bash
$ docker-compose exec web pytest
```

## Debug

### Kubernetes.


---

### EKS auth setting

Once the EKS cluster is created, only the user who makes this EKS cluster has permission to access it. In order to add other users permission into this cluster, two methods are listed below to setup permissions.
Users can get their `User ARN` in their `IAM` user page.

method 1:

```bash
eksctl create iamidentitymapping --cluster  <clusterName> --region=<region> --arn <arn:aws:iam::123456:role/testing> --group system:masters --username admin
```

method 2:

```bash
kubectl edit configmap aws-auth -n kube-system
```

change the config file as:
~~~
mapUsers: |
  - userarn: arn:aws:iam::[account_id]:root
    groups:
    - system:masters
~~~
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
