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

Tools for executing time-consuming tasks with developer-defined custom code blocks in parallel on the AWS EKS platform.

---

## Install & Setup

### Quick start on AWS

1. Login to `slac-gismo` AWS account.
2. Go to the `EC2` page in the `us-east-2` region and select `AMIs` in the `Images` tab in the left options menu.
3. Select the template `pvinsight-eks-bastion-template` from AMIs private image and click `Launch instance from AMIs.`
This image had been installed necessary dependenciues included:

- [kubectl](https://docs.aws.amazon.com/eks/latest/userguide/install-kubectl.html)
- [eksctl](https://docs.aws.amazon.com/eks/latest/userguide/eksctl.html)
- [awscli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [git](https://git-scm.com/)
- [docker](https://docs.docker.com/)
- [docker-compose](https://docs.docker.com/compose/install/)
- [gismo-cloud-deploy project](https://github.com/slacgismo/gismo-cloud-deploy)

#### Launch a instance

- Give this new instance a name you like (eg. `gcd-eks-test`)

- This program runs in multiple threads. Please select at least `2 vcpus` instance type.  Under `Instance types`, select `t2.large` type is recommended.

- Under `Configure Storage`, select the instance volume should be `16 GB` at least.

- Under the `Key pair(login)` option, create a new key pair or use your existing key pairs.

- Click the `Launch instance` button to launch an EC2 instance.

- After the EC2 instance is launched, under the `Tags`, create a tag called: `project:pvinsight` for budget management purposes.

#### Launch the application

- When the EC2 instance is running, use your ssh key to connect to the EC2 tunnel in your local terminal. Get the IP address from the `Public IPv4 address` in the `Detail` tabs.

Change `pem-file` permission.

```bash
cd /path-of-pem-file
chmod 400 <pem-file>
```

Connect to the EC2

```bash
ssh -i <path/pem-file> ec2-user@<Public IPv4 address>
```

#### Setup AWS credentials

- Inside the instance, set up AWS credentials to access EKS and ECR. **_NOTE:_** `(Reach out to this project's owner to get the AWS credentials).`

```bash
aws configure
```
- Setup AWS credentials

~~~
AWS Access Key ID :
AWS Secret Access Key:
Default region name:
Default output format [None]:
~~~

- Check current IAM user role

```bash
aws sts get-caller-identity
```

The output should return the IAM user details for designated_user.

~~~
{
    "UserId": "XXXXXXXXXXXXXXXXXXXXX",
    "Account": "XXXXXXXXXXXX",
    "Arn": "arn:aws:iam::XXXXXXXXXXXX:user/designated_user"
}
~~~

:warning: Confirmed with the cluster's creator that this IAM role has permission to access it.

- Find out the existing EKS clusters name on AWS EKS page of your AWS account with specify region (eg. `us-east-2`). Under EKS pages, you will see the clusters name, such as `gcd`.
Update existing EKS information to this new EC2 instance. Otherwise, this new EC2 instance cannot access the existing eks cluster by following command. For example, replace < your-cluster-name > with `gcd` and replace < your-region-code > with `us-east-2`
  
~~~
aws eks update-kubeconfig --region <your-region-code> --name <your-cluster-name>
~~~

:warning: If no eks cluster exists on AWS, please follow [EKS configuration](#eks-configuration) to create a new cluster.


### Root user

If you log in as a root user, you can find out the `gismo-cloud-deploy` folder in `/home/ec2-user/gismo-cloud-deploy` folder.

#### Pull down the latest git repository

- In `gismo-cloud-deploy` directory, use command `git checkout main` to checkout to main branchm, and use `git pull` to  pull down latest repository from [gismo-cloud-deploy.git](git@github.com:slacgismo/gismo-cloud-deploy.git) in `main` branch.

#### Update the .env file

- Set up a `.env` file for `CLI` program usage.

```bash
touch ./gismoclouddeploy/services/.env
```

Below are the sample variables in the .env file, and replace `<your-aws-key>` with the correct keys.

~~~
AWS_ACCESS_KEY_ID=<your-aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key-id>
AWS_DEFAULT_REGION=<your-aws-default-region>
SQS_URL=<your-sqs-url>
DLQ_URL=<your-dlq-url>
SNS_TOPIC=<your-sns-topic>
ECR_REPO=<your-ecr-repo>
~~~

#### Install dependencies

- The AMIs image should have installed all the python packages of `CLI` tools in the environment.
In case developers need to re-install the dependencies of `CLI`, please follow the below command:

- Activate the virtual environment.

```bash
cd gismoclouddeploy/services/
source ./venv/bin/activate
```

- Upgrade pip

```bash
pip install --upgrade pip
```

- Update dependencies.

```bash
pip install -r requirements.txt
```

- **_NOTE:_** In case the virtual environment was not created, please create the virtual environment first.

```bash
cd gismoclouddeploy/services
```

```bash
python3.8 -m venv venv
```

Upgrade pip and install all dependencies.

- Check if the EKS cluster exists.

```bash
eksctl get cluster
```

If a cluster exists, it returns the output as below.

~~~
NAME    REGION    EKSCTL CREATED
gcd   us-east-2   True
~~~

If a cluster does not exist, please follow [EKS configuration yaml files](#eks-configuration) section to create a cluster first.

#### Include the solver license

- Include the solver license file under `./gismoclouddeploy/services/config/license` folder.(eg. `./gismoclouddeploy/services/config/license/mosek.lic`) Please follow [Include MOSEK license](#include-MOSEK-licence) section to get detail.

- If you have your mosek license on S3, you can use the following command to upload file to ec2 instance:

~~~
aws s3 cp s3://<bucket_name>/<path>/<lic_file_name> /home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/
services/config/license/mosek.lic
~~~

#### Modify the code blocks

- To implement your own code in a custom code block, please modify the `entrypoint` function in `./gismoclouddeploy/services/config/code-templates/entrypoint.py`.
For example, you can modify the calculation of `data_clearness_score`.

~~~
 data_clearness_score = float("{:.1f}".format(dh.data_clearness_score * 0.5 * 100))
~~~

#### Run the command

- Under the virtual environment `(venv)`, run the `run-files` command to test it.

```bash
cd ./gismoclouddeploy/services
gcd run-files -n 1 -d -b -sc 1
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

- Check the saved data file, Gantt plot, and tasks performance in `./gismoclouddeploy/services/results` folder.

---

## Command

The gcd command supports the following subcommands:

### run-files command

~~~
Usage: gcd run-files [OPTIONS]

Run Process Files

Options:
  -n, --number TEXT       Process the first n files in the defined bucket of
                          config.yaml. If the number is None, this application
                          process defined files in config.yaml. If number is
                          0, this application processes all files in the defined
                          bucket in config.yaml. If the number is an integer, this
                          application processes the first `number` files in the
                          defined bucket in config.yaml.

  -d, --deletenodes BOOL  Enable deleting eks node after completing this
                          application. The default value is False.

  -f, --configfile TEXT   Assign custom config files, The default files name is
                          ./config/config.yaml

  -r, --rollout  BOOL     Enable deleting current k8s deployment services and
                          re-deployment services. The default value is False

  -i, --imagetag TEXT     Specify the image tag. The default value is 'latest'
                          This option command did not work with [ -b | --build ] option command.

  -do, --docker  BOOL     Default value is False. If it is True, the services
                          run in docker environment. Otherwise, the services run
                          in kubernetes◊ environment.

  -b, --build             Build a temp image and use it. If on AWS k8s
                          environment,     build and push image to ECR with
                          the temp image tag. These images will be deleted after
                          used. If you would like to preserve images, please
                          use build-image command instead

  -sc, --nodesscale TEXT  Scale up eks nodes and worker replicas as the same
                          number. This input number replaces the
                          worker_repliacs and eks_nodes_number in config files

  --help                  Show this message and exit.
~~~

- If you use the default `run-files` command with no option, this program processes the files defined in the `config.yaml` file and generates the saved results in a file specified in `config.yaml` file.

- The process file command with option command `-n` followed by an `integer number` will process the first `number` files in the defined bucket. (eg. `-n 10` will process the first ten files in the specified bucket )
If `number=0`, it processes all files in the buckets.

- The option command `[ --configfile | -f ] [filename]`  imports custom configuration yaml files under `gismoclouddeploy/services/config` folder.
If this [-f] option command is not assigned, the default configure file is `gismoclouddeploy/services/config/config.yaml`.

- The option command `[ --build | -b ]` build custom images based on `./gismoclouddeply/services/server` and `./gismoclouddeply/services/config/code-templates` folder. If your environment is on AWS, this option command builds and pushes `worker` and `server` service images to AWS ECR with a temporary image tag. This temporary tag will be deleted after this application completes processing. Please read section [Build and push images](#build-and-push-images) to get more information.

- The option command `[ --nodesscale | -sc ]` generates the same number of eks nodes and worker replicas on AWS. (eg. The `-sc 5` option command generates five nodes and five worker replicas. The five workers' replicas evenly spread among five nodes.)

#### Examples:

```bash
gcd run-files -b -n 1 -d -f test_config.yaml -sc 5
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
**NOTE** If developers want to preserve images, please use the `gcd build-images` command instead.
9. Since [-d] option command is specified, this application deletes all nodes(ec2-instances) of AWS EKS.

### Another support command

- gcd --help
- gcd nodes-scale [integer_number] [--help]
- gcd build-images [-t|--tag] <image_tag> [-p|--push] [--help]
- gcd read-dlq  [-e] [--help]

The `nodes-scale` command scales up or down the eks nodes.

The `build-images` command builds images from `docker-compose`. Please read this [Build and push images](#build-and-push-images) to get more information.

The `read-dlq` command checks current DLQ(dead letter queue) on AWS. The `-e` option command enables or disables deleting messages after invoking this command.
The default value is `False`.

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
