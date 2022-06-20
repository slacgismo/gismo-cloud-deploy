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

.PHONY: get-nodegroup
get-nodegroup:
	eksctl  get nodegroups --cluster=gcd-eks-cluster
