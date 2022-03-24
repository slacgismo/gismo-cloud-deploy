variable "prefix" {
  default = "gcd"
}

variable "project" {
  default = "gismo-cloud-deploy"
}

variable "contact" {
  default = "jimmyleu@stanford.edu"
}

variable "db_username" {
  # match key om terraform.tfvars (hidden)
  description = "Username for the RDS Postgres instance"
}

variable "db_password" {
  # match key om terraform.tfvars (hidden)
  description = "Password for the RDS postgres instance"
}

variable "bastion_key_name" {
  # match key pair on ec2 set previous
  default = "solar-key-JL"
}


