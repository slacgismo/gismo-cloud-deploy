# Gismo-Cloud-Deploy
## Describtion
## System diagram
![System diagram](./Solar-data-tools-AWS.png)

## Start the project

### local development

1. Copy `Mosek` licence into server
If you want to use `Mosek` solver and have the licence, plase copy `mosek.lic` to `/gismoclouddeploy/services/server/licence/`

2. Setup environment variables of DB and AWS credentials. Create `./env/.dev-sample`, and change the variables marked inside `<>`

~~~
FLASK_ENV=development
FLASK_CONFIG=development
DATABASE_URL=postgresql://<db user name>:<db password>@db/<db name>
SECRET_KEY=<any secretky>
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

AWS_ACCESS_KEY_ID=<your access key>
AWS_SECRET_ACCESS_KEY=<your secret key>
AWS_DEFAULT_REGION=<your region>
~~~

3. Init server by docker-compose command

~~~
cd gismoclouddeploy/services/
docker-compose up --build
~~~

Check server is running by: http://localhost:5010/solardata/ping/ on browser
You should see:

~~~
{
  "container_id": "e7097b1122ad", 
  "message": "pong!", 
  "status": "success"
}
~~~

2. Init database. Open another terminal window.

~~~
cd gismoclouddeploy/services/
docker-compose exec web python app.py recreate_db
docker-compose exec web python app.py seed_db
~~~

Check db had seed data by running: http://localhost:5010/solardata/all_results/ on browser
You shoud see:

~~~
{
  "container_id": "e7097b1122ad", 
  "solardata": [
    {
      "bucket_name": "pv.insight.nrel", 
      "capacity_changes": false, 
      "capacity_estimate": 5.28, 
      "column_name": "Power(W)", 
      "data_clearness_score": 31.8, 
      "data_quality_score": 98.4, 
      "data_sampling": 5, 
      "error_message": "this is test error message", 
      "file_name": "10059.csv", 
      "file_path": "PVO/PVOutput", 
      "id": 1, 
      "inverter_clipping": false, 
      "length": 4.41, 
      "normal_quality_scores": true, 
      "num_clip_points": 0, 
      "power_units": "W", 
      "process_time": 23.23, 
      "task_id": "task_id", 
      "time_shifts": false, 
      "tz_correction": -1
    }
  ], 
  "status": "success"
}
~~~


## Local Kubernetes

1. Enable kubernetes on Docker Desktop.
2. Install kubectl.
3. Enable kuebernetes config .ymal.

~~~
cd gismoclouddeploy/k8s
kubectl apply -f .
~~~

4. create db 
~~~
$ kubectl get pods

NAME                        READY   STATUS    RESTARTS   AGE
postgres-95566f9-xs2cf   1/1     Running   0          93s

$ kubectl exec postgres-95566f9-xs2cf --stdin --tty -- createdb -U sample flask_celery
~~~
verify 
~~~
kubectl exec postgres-95566f9-xs2cf --stdin --tty -- psql -U sample
psql (13.6)
Type "help" for help.

sample=# \l
                               List of databases
     Name     | Owner  | Encoding |  Collate   |   Ctype    | Access privileges 
--------------+--------+----------+------------+------------+-------------------
 flask_celery | sample | UTF8     | en_US.utf8 | en_US.utf8 | 
 postgres     | sample | UTF8     | en_US.utf8 | en_US.utf8 | 
 sample       | sample | UTF8     | en_US.utf8 | en_US.utf8 | 
 template0    | sample | UTF8     | en_US.utf8 | en_US.utf8 | =c/sample        +
              |        |          |            |            | sample=CTc/sample
 template1    | sample | UTF8     | en_US.utf8 | en_US.utf8 | =c/sample        +
              |        |          |            |            | sample=CTc/sample
(5 rows)

sample=# 
~~~
5. Check server is running on URL: in your local machine.

6. Use kubectl create secrets. 

~~~
kubectl create secret generic aws-access-key-id --from-literal  aws-access-key-id=<your AWS access key>
kubectl create secret generic aws-secret-access-key --from-literal aws-secret-access-key =<your AWS secret key>

~~~
## Setup AWS EKS 
`(will be simplied by terraform)`
1. Crreate an ec2 bastion tunnel. 
2. SSH to bastion tunnel
3. Install eksctl
~~~
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
~~~
4. Update AWS CLI to Version 2
~~~
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
~~~
5. log out of your shell and back in again.

6. Set up a user group
7. Set up a group with the Permissions of
- AmazonEC2FullAccess
- IAMFullAccess
- AWSCloudFormationFullAccess
- create a custom security permission:
~~~
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "eks:*",
      "Resource": "*"
    },
    {
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "*",
      "Effect": "Allow"
    }
  ]
}
~~~
8.  Add a user to the group
Use the console to add a user to your new group, and then use "aws configure" to input the credentials
9. Install kubectl.
~~~
export RELEASE=<enter default eks version number here. Eg 1.21.0>
curl -LO https://storage.googleapis.com/kubernetes-release/release/v$RELEASE/bin/linux/amd64/kubectl
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
~~~
10.  Check the version 
~~~
kubectl version --client"
~~~
11.  Start your cluster!
~~~
eksctl create cluster --name fleetman --nodes-min=3
~~~

### excute command
`(will be simplied by cli tools)`
~~~
kubectl get pods


~~~