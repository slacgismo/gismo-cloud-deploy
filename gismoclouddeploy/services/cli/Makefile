.PHONY: ecr-validation
ecr-validation:
	@echo "validaton aws ecr credentidals"
	aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 041414866712.dkr.ecr.us-east-2.amazonaws.com

.PHONY: create-cluster
create-cluster:
	@echo "Create Cluster from cluster.yaml"
	eksctl create cluster -f ./config/eks/cluster.yaml

.PHONY: delete-cluster
delete-cluster:
	@echo "Create Cluster from cluster.yaml"
	eksctl delete cluster -f ./config/eks/cluster.yaml

.PHONY: get-cluster
get-cluster:
	eksctl get cluster


.PHONY: rollout
rollout:
	@echo "Rollout kubernetes images"
	kubectl rollout restart deployment/worker
	kubectl rollout restart deployment/webapp
