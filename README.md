# Gismo-Cloud-Deployment

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

This project is to build a tool `gismo-cloud-deploy` designed to executing time-consuming computation on multiple AWS EC2 instances in parallel. The tool containerizes users custom scripts into docker images, and it utilizes `Kubernetes` (AWS EKS) horizontial scaling and vertical scaling features to distrube those images evenly among generated instances.

Since this project uses many cloud services of AWS. An extra automation tool operates AWS services on user's local machine through SSH. The automation tool `mainmenu` can genererate a new EC2 bastion. Through the generated EC2 bastion, it creates EKS cluster and run `gismo-cloud-deploy` tool. Please see the [System diagram](#system-diagram) to get more details.

---


## Install & Setup

### Quick start

#### Installations

Download the source code from the github repository.

```bash
git clone https://github.com/slacgismo/gismo-cloud-deploy.git
```

Create a python virtual environment and activate the virtual environment

```bash
cd gismo-cloud-deploy/gismoclouddeploy/services 
python3.8 -m venv venv
source ./venv/bin/activate
```

Install python dependencies.

```bash
pip install -upgrade pip 
pip install -r requirement.txt
```

#### Set up AWS permissions and credentials

Before we start to run the automation tool that control EC2 instances . We need to set up the AWS credentials.

First, include the AWS permission on your `IAM` user account. Or, if you are using share account, you can ask your account manager to add proper permissions into your `IAM` user.

The permissions includes:

- AmazonEC2FullAccess
- AmazonSQSFullAccess
- AmazonEC2ContainerRegistryFullAccess
- AmazonS3FullAccess
- AmazonEC2ContainerServiceAutoscaleRole
- EC2InstanceProfileForImageBuilderECRContainerBuilds
- AWSCloudFormationFullAccess

Custom policy

- [AmazonEKSClusterAutoscalerPolicy](./mainmenu/config/policy/AmazonEKSClusterAutoscalerPolicy.json)
- [EKSAccess](./mainmenu/config/policy/EKSAccess.json)
- [IamLimitedAccess-EKS](./mainmenu/config/policy/IamLimitedAccess-EKS.json)

Once you add those permissions onto your IAM user. Create a `.env` file with following AWS credentials: 

```bash
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secrect-access-key>
AWS_DEFAULT_REGION=<your-aws-region>
ECR_REPO=<your-ecr-repository-url>
```

#### Set up AWS ECR

If you are using your own account other than SLAC Gismo group account. Please create a private ECR repositories that will contains three temporary images (`server`, `worker`, `celeryflower`). Those images are created during the run-time, and will are deleted after the process completed.



<!-- If you want to include a private `solver license`, such as `MOSEK` inside this project. Please include your `solver license` in the `gismo-cloud-deploy/gismoclouddeploy/services/config/license` folder of your local machine. Please follow the [Include MOSEK licenses](#include-mosek-license) section to get more detail. -->

#### Run menu

Run `menu` command to select main menu.

```bash
python3 main.py menu

```

A selection menu pop up , please select `create_cloud_resources_and_start` command. It starts a process of creating all necessary cloud resources automatically with instructions and permissions.

```bash
 > create_cloud_resources_and_start
   resume_from_existing
   cleanup_cloud_resources
   run_in_local_machine
```

The following question is to type your project path.

```bash
('Enter project folder (Hit `Enter` button to use default path',): /Users/<username>/Development/gismo/gismo-cloud-deploy/examples/sleep path): 
```

There are four example projects in this gihub repositoy.

- examples/gridlabd
  - This exmaples runs the [gridlabd](https://github.com/slacgismo/gridlabd) project
- examples/sleep
  - This exmaples runs a for loop without doing anything.
- examples/solardatatools
  - This exmaples runs the [solar-data-tools](https://github.com/slacgismo/solar-data-tools) project. It might require a `MOSEK` solver license file to run properly. Please check [Include MOSEK licenses](#include-mosek-license) to get more details.
- examples/stasticclearsky
  - This exmaples runs the [StatisticClearSky](https://github.com/slacgismo/StatisticalClearSky) project It might require a `MOSEK` solver license file to run properly. Please check [Include MOSEK licenses](#include-mosek-license) to get more details.

You can start from examples/sleep. It run a for loop without doing anything. You can edit the 


### Project files structures

A project folder 


```bash
Use default VPC ?(default:yes) (must be yes/no): yes # type yes to use default VPC 
Create a new security group allow SSH connection only ?(default:yes) (must be yes/no): # type yes to create a new security group that only alow SSH connection. 
Create a new keypair ?(default:yes) (must be yes/no): yes # If you already had a pem file, type `no`, otherwise type `yes` to create a new one.
Enter existing keypair name: JS-ss # type your existing key pair pem file. (If you enter no in previous quesiton. This question is skipped.)
Enter the pem path (hit enter to use default path: /Users/jimmyleu/Development/gismo/gismo-cloud-deploy/gismoclouddeploy/services/config/keypair):  #(type your pem file location. hit enter button to use default setting) 
Creat a EC2 name  : my-first-ec2 # give your ec2 a name
Creat a project name in tag: my-project # give your ec2 a project name in tags. 
Select instance type (suggest 't2.large')?: t2.large # select ec2 type
 > t2.large
   t2.medium
   t2.xlarge
Enter the ec2 volume (enter for default: 20): # define ec2 storage (hit enter to use default value:20)
Enter the export file name (enter for default:config-ec2.yaml): # define the export file name of ec2.
```

***NOTE*** When you generate `pem file`. It important to keep this pem file privacy and never show to others for security purpose.

A table will shows all the settings you just key in and ask for the confirmation. Type `yes` to create your ec2 bastion.

```bash
Confim to process creation (must be yes/no):
```

Then it will start to create an EC2 instance and install all the dependencies.
It includes:
- [kubectl](https://docs.aws.amazon.com/eks/latest/userguide/install-kubectl.html)
- [eksctl](https://docs.aws.amazon.com/eks/latest/userguide/eksctl.html)
- [awscli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [git](https://git-scm.com/)
- [docker](https://docs.docker.com/)
- [docker-compose](https://docs.docker.com/compose/install/)
- [gismo-cloud-deploy project](https://github.com/slacgismo/gismo-cloud-deploy)

#### Create EKS Cluster

Run handle ec2 command to create a ec2 bastion that control AWS EKS.( Under path: `gismo-cloud-deploy/gismoclouddeploy/services`).

```bash
python3 main.py handle-ec2
```

Before creating a eks cluster to hold all the services, plase define your cluster name in the file `gismo-cloud-deploy/gismoclouddeploy/services/config/eks/cluster.yaml`

A selection menu pop up , please select `ssh_create_eks` command. This command will eks cluster from the defined yaml file through SSH.

```bash
   create
   running
   stop
   terminate
   ssh
 > ssh_create_eks
   ssh_delete_eks
```

Creating eks cluster takes about 10 ~ 20 minutes depend on the system. After the creating is completed, it pop up a following questions to ask how to handle ec2 action again.
Please select `ssh` to run commands to control eks you just created.

```bash
 > ssh
   running
   stop
   terminate
```

A question pop up to ask update config file :

```bash
Is update config folder?: yes 
 > yes
   no
```

Select `yes` to upload the all `config` folder to ec2 bastion. It will overwirte the `config` folder in the AWS ec2 to keep your local config folder the same as your AWS ec2 folder.

#### Start the application

Follow the previous command. If you see the terminal ask another question:
Congrtulations!!. You have set up the environments correct. We can start to run real process.
Please type `python3 main.py run-files -n 1` in the terminal after the question as follow:

```bash
Please type your command: python3 main.py run-files -n 1
```

The program starts to process the first file in the S3 bucket that defined in `gismo-cloud-deploy/gismoclouddeploy/services/config/config.yaml`
After couple minutes waiting, the program will show the results in the terminals. 
Congrautaltions!! You have completed your fist process file analysis.
The program will ask you to run ssh again or not. Select no to try another ssh command or select `yes` to close the ssh connection.

```bash
 breaking ssh ?: yes
  > yes
    no
```

Then select `running` to keep the instance running. We need to delete EKS cluster to avoid running cost from AWS.

#### Delete EKS Cluster

A running eks cluster is charged in hour rate by AWS. If you complete your process, please remember to delete eks cluster to avoid extra cost.

Run the `handle-c2` command and select `ssh_delete_eks` command.

```bash
python3 main.py handle-ec2
   create
   running
   stop
   terminate
   ssh
   ssh_create_eks
 > ssh_delete_eks
```

This commnad will scale down the nodes to 0 and delete eks cluster defined from the `cluster.yaml` file.

***Note*** Please delete eks cluster before your terminate youre ec2 basion. Otherwiser you may face some permission issue. Then you have to delete the eks cluster in your online console.

#### Stop or terminate the EC2

A running ec2 basion will be charge in hour rate. If you complete your porcess, please remember to stop or terminated your ec2.
Run the `handle-c2` command and select `terminate` command.

```bash
python3 main.py handle-ec2
   create
   running
 > stop
   terminate
   ssh
   ssh_create_eks
   ssh_delete_eks
```

### Quick start on AWS

Running command from local machine and control AWS EC2 through SSH is slow, and debug could be challenge. Therefore, running command on the AWS ec2 bastion is highly recommended. Follow the steps to configure your AWS EC2.

If you have follow up the [Create EC2 bastion](#create-ec2-bastion) steps. All the necessary environmental dependencies and privacy files such as `solver license` and `.env` file that contains AWS crendetials had been upload to the EC2 during process time. 

However, we still need configure `AWS CLI` to give the ec2 permission to control kubernetes and EKS.

#### Fetch public ip of EC2

Run run `handle-ec2` command, select `running` in the pop up menu.

```bash
[?] Select action type ?: running
   create
 > running
   stop
   terminate
   ssh
   ssh_create_eks
   ssh_delete_eks
```

It requests you to enter the config file of ec2. The file is the export file that created when you run `create` command.

```bash
Enter the ec2 config file name (enter for default:config-ec2.yaml): 
```

Enter the pem file location to provid ssh key:

 ```bash
 Enter the ec2 config file name (enter for default:config-ec2.yaml): 
 ```

 If everything is correct, you will see the public ip of the ec2.

 ```bash
 i-0a08f95xxxx is ready to connect SSH
 ------------------
 public_ip :3.1x.84.xx
 ------------------
 ```

 ***Note*** The public ip changed when you re-start the EC2 instance.

#### Login to your EC2

Under you key pair folder (for example:`/gismoclouddeploy/services/config/keypair`)
RUN ssh command. Replace `<your-key-pair-file>` with your keypair file. `<ec2_public_ip>` is the public ip that you get from the running ec2 in previous step.

```bash
ssh -i <your-key-pair-file> ec2-user@<ec2_public_ip>
```

Then you will login to your ec2 and control the ec2 in your terminal. 

***Note*** If you use `VScode` as editor. You can use its `SSH` features to control the EC2 from your local editor. Here is [link](https://code.visualstudio.com/docs/remote/ssh) describes how to do the configuration.

Once you have login to your EC2. Run the following command to set up the AWS CLI:

```bash
aws configure
AWS Access Key ID : # key in your aws access key
AWS Secret Access Key:  # key in your aws secrect access key
Default region name:  # key in your aws region 
Default output format [None]: # we don't need this one. 
```

Congratulation!! You have completed the environment setup.

#### Run command on AWS

Activate your pyton3 virtual environment.

```bash
cd gismo-cloud-deploy/gismoclouddeploy/services
source ./venv/bin/activate
```

Under the virtual environment `(venv)`, run the `run-files` command to test it.

```bash
cd ./gismoclouddeploy/services
python3 main.py run-files -n 1 
```

Please follwo [Command](#command) section to explore the command detail.
:warning: If you see some error messages related to **unauthorized** actions, it means this cluster didn't authorize the permission to this role. Please reach out the project or cluster creator to grant permission. Or follow the [EKS configuration](#eks-configuration) section to create a new cluster

After it completed, the terminal prints out the performance analysis as below:

~~~
+-------------------------------------+-----------------------+---------------------------------+
| Performance                         | Results               | Info                            |
+-------------------------------------+-----------------------+---------------------------------+
| Total tasks                         | 2                     |                                 |
| Average task duration               | 2.046194 sec          |                                 |
| Min task duration                   | 1.915406 sec          | PVO/PVOutput/10059.csv/Power(W) |
| Max task duration                   | 2.176982 sec          | PVO/PVOutput/10010.csv/Power(W) |
| Number of error tasks               | 0                     |                                 |
| Number of unfinished tasks          | 0                     |                                 |
| Process tasks duration(in parallel) | 3.479771137237549 sec | Real data                       |
| Process tasks duration(in serial)   | 4.092388 sec          | Estimation                      |
| Effeciency improvement              | 17 %                  |                                 |
| Initialize services duration        | 60.2083740234375 sec  |                                 |
| Total process durations             | 76.75437307357788 sec |                                 |
| Number of nodes                     | 1                     |                                 |
| Number of workers                   | 1                     |                                 |
+-------------------------------------+-----------------------+---------------------------------+
~~~

Check the saved data file, Gantt plot, and tasks performance in `./gismoclouddeploy/services/results` folder.

---

### Root user

If you log in as a root user, you can find out the `gismo-cloud-deploy` folder in `/home/ec2-user/gismo-cloud-deploy` folder.


#### Modify the code blocks

- To implement your own code in a custom code block, please modify the `entrypoint` function in `./gismoclouddeploy/services/config/code-templates/entrypoint.py`.
For example, you can modify the calculation of `data_clearness_score`.

~~~
 data_clearness_score = float("{:.1f}".format(dh.data_clearness_score * 0.5 * 100))
~~~

#### Include the solver license

- Include the solver license file under `./gismoclouddeploy/services/config/license` folder.(eg. `./gismoclouddeploy/services/config/license/mosek.lic`) Please follow [Include MOSEK license](#include-MOSEK-licence) section to get detail.




## Command

The gcd command supports the following subcommands:

### run-files command

~~~
Usage: python3 main.py run-files [OPTIONS]

Run Process Files

Options:
  -n, --number TEXT       Process the first n files in the defined bucket of
                          config.yaml. If the number is None, this application
                          process defined files in config.yaml. If number is
                          0, this application processes all files in the defined
                          bucket in config.yaml. If the number is an integer, this
                          application processes the first `number` files in the
                          defined bucket in config.yaml.
  -f, --configfile TEXT   Assign custom config files, The default files name is
                          ./config/config.yaml

  --help                  Show this message and exit.
~~~

- If you use the default `run-files` command with no option, this program processes the files defined in the `config.yaml` file and generates the saved results in a file specified in `config.yaml` file.

- The process file command with option command `-n` followed by an `integer number` will process the first `number` files in the defined bucket. (eg. `-n 10` will process the first ten files in the specified bucket )
- If `number=0`, it processes all files in the buckets.

- The option command `[ --configfile | -f ] [filename]`  imports custom configuration yaml files under `gismoclouddeploy/services/config` folder.
If this [-f] option command is not assigned, the default configure file is `gismoclouddeploy/services/config/config.yaml`.

#### Example

```bash
python3 main.py run-files -n 0 -f test_config.yaml
```

Command details:
On the AWS environment ,the above command starts the following processes:

1. Since [-f] option commnad is specified, this application imports `./gismoclouddeply/services/config/test_config.yaml` to replace default `./gismoclouddeply/services/config/config.yaml` file.
2. The AWS EKS fires up 5 ec2-instandes(nodes), and 5 worker replicas according to the option command [-sc] <5>.
3. This application builds `server` and `worker` images from `./gismoclouddeply/services/server` and `./gismoclouddeply/services/config/code-templates` folder with a temporary image tag according to its hostname.
4. After building images are completed, this application pushes those two images to AWS ECR with temporary image tags, such as `worker:my-hostname` and `server:my-hostname`.
5. This AWS EKS pulls those temporary images and mounts them into generated nodes.
6. The `woker` service is the major service to process time-consuming tasks, such as analyzing data with a defined algorithm. To process the time-consuming tasks in parallel on AWS, a developer can increase the `replicas` of the `worker`. This application spreads multiple `worker` services evenly among generated `nodes`(ec2-instances) of AWS EKS.
7. Since [-n] <1> option command is specified, this application starts to process the `first 1` file of the defined bucket in `test_config.yaml`.
8. After the process is done, this application deletes temporary images on ECR.


### Another support command

- python3 main.py --help
- handle-ec2

---

## Configuration files

Under `gismoclouddeploy/services/config/config.yaml` folder, developers can modify the parameters of the cli command tool.

1. The `aws_config` section contains all the AWS environment variables settings.
2. The `worker_config` section contains all the parameters for `worker` services.
3. The `services_config_list` section contains all `kubernetes` settings.

**NOTE** The details information of each variable is defined in the `config.yaml` file.

### Kubernetes yaml files

All Kubernetes deployment and service files are listed under `gismoclouddeploy/services/config/k8s` folder. Developers can modify it if necessary.

### EKS configuration

The create cluster command will create an EKS cluster based on the configuration file in `./gismoclouddeploy/services/config/eks/cluster.yaml`.

***NOTE*** The `max_size` variable under `nodeGroups` limits the maximum nodes number that scales in this application. The default number is `20`.

To update the cluster setting, developers have to delete the old cluster and create a new cluster. Under `./gismoclouddeploy/services/` folder, a developer can use command as follows:

- Delete a cluster

```bash
make delete-cluster
```

- Create a cluster

```bash
make create-cluster
```


**NOTE** If a user creates a cluster, please remember to add permission in this cluster after creation. Only the ec2 instance that create this cluster has permission to access it. Please follow [EKS auth setting](#eks-auth-setting) setion to add other user's permission into this cluster.


---

#### Include MOSEK license

 MOSEK is a commercial software package. The included YAML file will install MOSEK for you, but you will still need to obtain a license. More information is available here:

- [mosek](https://www.mosek.com/resources/getting-started/)
- [Free 30-day trial](https://www.mosek.com/products/trial/)
- [Personal academic license](https://www.mosek.com/products/academic-licenses/)

**NOTE** If developers defined `MOSEK` in `config.yaml` file. Please include `MOSEK` licence file `mosek.lic` under folder `./gismoclouddeploy/services/config/licence`
This license file will be uploaded to a temporary S3 folder and downloaded into the AWS EKS worker during run-time. The program deletes the license file after the process is done.

---

## Code blocks

- Custom code:
Developers can build and run their code blocks in this application.
To pass the developer's code block to this application, the code block has to be inside a self defined folder (eg. `code-templates`) with the path, `./gismoclouddeploy/services/config/`. The full path is `./gismoclouddeploy/services/config/code-templates`. Then you have to specify the folder variable `code_template_folder` in `config.yaml` file. This `code_template_folder` variable has to match to your code block folder.

- Code block folder:
When you define your code block folder, this folder has to include a  `entrypoint.py` file with a `entrypoint` function in it. The `entrypoint` function is the start function of this application. When this application builds images, it copies all the files inside code block folder (eg.`code-templates`) and pastes them to docker images.
Developers can include any files or self defined python modules in their folder (eg `code-templates`). Those files, sub-folder and modules will be copied to the Docker images.
You can check the example `entrypoint.py` files in `code-tempates` folder to get more information on input parameters.

- Python packages:
Please include a `requirements.txt` file under your code block folder. (eg. `./gismoclouddeploy/services/config/code-templates/requirements.txt`). You have to include all the necessary dependencies pacakges in this file. The Docker copys those files into their images, and the application will install python packages based on it.
Some packages are necessary to run flask server and celery worker. Please do not remove it. Please check the example `requirements.txt` to get more details.

- Specify the code block folder
In `./gismoclouddeploy/services/config/config.yaml` file, a user can specify a code block folder by modifying the variable `code_template_folder`.The default code block folder is `code-templates`.

---

## Build and push images

The AWS EKS hosts services based on the ECR images. If developers modify any code inside the `code-templates` folder, developers have to build and push new images to ECR to see the changes.

Developers can use `run-files` command with [-b|--build] option to build temporary images for a quick start. However, these temporary images will be deleted after processing.
If developers want to preserver images, the `build-images` command can build and push images to ECR for next usage.
The `build-images` command is a python wrapper function to invoke `docker-compose build` command in the shell.

~~~
Usage: gcd build-images [OPTIONS]

  Build an image from docker-compose and push to ECR

Options:
  -t, --tag TEXT    Rollout and restart of webapp and worker pod of Kubernetes

  -p, --push BOOL   Is pushing the images to AWS ECR : Default is False

  --help            Show this message and exit.
~~~

Example:

```bash
gcd build-image  -t test -p
```

The above example command executes `build-image` command, and tags built images with tag `test`.
In this example, two images with build and tag as `worker:test` and `server:test`.Since `-p` optin command is enabled, the built images with tag are pushed to AWS ECR.

**_NOTE:_** The image with `latest` and `develop` tags are pushed from `Github Action` CI/CD pipeline to AWS ECR. Developers cannot push images with `latest` and `develop` tags from local to AWS ECR.

---

## Debug

### Read error/logs files

This program saves all the output in a logs files. It separates error output into a error file. Developers can check the error of previous run-time in this error file.

### Read DLQ

The `gcd read-dlq` command prints out the error ouput of dlq.

### Debug in real time

Getting the logs information of workers in real time needs a serial step as follows:

- Make sure the nodes are generated, and wokers are running. Open a new terminal, list all running worker services' name as command below:


```bash
kubectl get pod
```

It prints out:

~~~
NAME                       READY   STATUS    RESTARTS   AGE
rabbitmq-84669dd8f-rc2fx   1/1     Running   0          10h
rabbitmq-84669dd8f-xm597   1/1     Running   0          10h
redis-697477d557-8jdz2     1/1     Running   0          10h
redis-697477d557-mxtpx     1/1     Running   0          10h
server-65bf8bc584-h885f    1/1     Running   0          10h
server-65bf8bc584-kc6zs    1/1     Running   0          10h
worker-6d47d89f94-r7drj    1/1     Running   0          10h
worker-6d47d89f94-zh8pq    1/1     Running   0          10h
worker-6d47d89f94-zv8pt    1/1     Running   0          10h
~~~

***NOTE*** The worker's (`worker-<random id>`) name changes when this application restarts the services.

- In this case, this program has two server and three worker. We don't need to care about the server output. We just need to logs out all three worker's logs. And we start to logs out the `worker-6d47d89f94-r7drj` information in the terminal.

  ```bash
  kubectl logs -f worker-6d47d89f94-r7drj
  ```

  It prints out the logs detail of `worker-6d47d89f94-r7drj`.Repeat this step to print out the rest two workers in a different terminal.

- Please check [kubectl](https://kubernetes.io/docs/tasks/tools/) to get more information.

### Monitoring the CPU and memory

---

This is extra information. In case you need to monitoring the cup and memory. Here is the steps.

- Install and apply the metrics server if the system didn't install before.

```bash
git clone https://github.com/kodekloudhub/kubernetes-metrics-server.git
kubectl apply -f kubernetes-metrics-server
```

- Check specific pod's memory and CPU usage. For example, if you would like to check pod, `worker-6d47d89f94-zv8pt`, memory and CPU. Use the following command:

```bash
kubectl top pod worker-6d47d89f94-zv8pt
```

---

## Testing

### Test cli

Run pytest coverage in cli

```bash
cd ./gismoclouddeploy/services/cli
pytest
```

<!-- #### Test docker image

Run pytest in the docker image

```bash
docker-compose exec web pytest
```

Get test coverage in docker image

```bash
docker-compose exec web pytest
``` -->

---

### EKS auth setting

Once the EKS cluster is created, only the ec2 instance that create this EKS cluster has permission to access it. To add other users' permission into this cluster, two methods are listed below to setup permissions.

First of all, users get their `User ARN` on AWS `IAM` user page.

- method 1:

```bash
eksctl create iamidentitymapping --cluster  <clusterName> --region=<region> --arn <arn:aws:iam::123456:role/testing> --group system:masters --username admin
```

- method 2:

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

![System diagram](./systemdiagram.png)

## Usage

## Contributors

## Test Coverage

## Versioning

We use [Semantic Versioning](http://semver.org/) for versioning. For the versions available, see the [tags on this repository].

## Authors

## License

This project is licensed under the BSD 2-Clause License - see the [LICENSE](LICENSE) file for details
