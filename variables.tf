data "aws_region" "current" {}
data "aws_caller_identity" "current" {}


locals {
  account_id     = data.aws_caller_identity.current.account_id
  region         = data.aws_region.current.name
  repo_full_name = "${local.repo_owner}/${local.repo_name}"
  repo_owner     = "rhythmictech"
  repo_name      = "terraform-aws-asg-rolling-restart-lambda"
}

variable "lambda_version_constraint" {
  default     = "~1.0.1-rc9"
  description = "NPM style version constraint to apply when looking for the correct version of the lambda code"
  type        = string
}

variable "loglevel" {
  type        = string
  default     = "INFO"
  description = "Logging level for the rolling restart lambda function."
}

variable "name" {
  type        = string
  default     = "rolling-restart-lambda"
  description = "Name to be used for resources"
}

variable "asg_name" {
  type        = string
  description = "Name of the ASG to execute the rolling restart against"
}

variable "tags" {
  type        = map(any)
  description = "Map of tags that should be added to stuff"
}
