

CLUSTER_FILE ?= $(shell bash -c 'read -p "Cluster_file: " cluster_file; echo $$cluster_file')



# .PHONY: create-cluster
create-cluster:
	@clear
	@read -p "Enter cluster file:" cluster_file; \  
	@echo "Create Cluster from ${cluster_file}.yaml"
	eksctl create cluster -f ./config/eks/${cluster_file}.yaml


.PHONY: delete-cluster
delete-cluster:
	@echo "Create Cluster from ${cluster_file}.yaml"
	eksctl delete cluster -f ./config/eks/${cluster_file}.yaml

.PHONY: get-cluster
get-cluster:
	eksctl get cluster


.PHONY: get-nodegroup
get-nodegroup:
	eksctl  get nodegroups --cluster=gcd


build:  
    @read -p "Enter Module Name:" module; \  
    module_dir=./modules/$$module; \
    mkdir -p $$module_dir/build