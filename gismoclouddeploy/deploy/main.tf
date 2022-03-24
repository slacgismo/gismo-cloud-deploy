terraform {
  backend "s3" {
    bucket         = "gismo-cloud-deploy-dev-tfstate"
    key            = "gismo-cloud-deploy.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "gismo-cloud-deploy-tf-state-lock"
  }
}

#ECR

# 041414866712.dkr.ecr.us-east-1.amazonaws.com/gismo-cloud-deploy


provider "aws" {
  region = "us-east-1"
}



locals {
  prefix = "${var.prefix}-${terraform.workspace}"
  common_tags = {
    Environment = terraform.workspace
    Project     = var.project
    Owner       = var.contact
    ManagedBy   = "Terraform"
  }

}

data "aws_region" "current" {}
