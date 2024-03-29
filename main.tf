module "tags" {
  source  = "rhythmictech/tags/terraform"
  version = "~> 1.1"
  tags    = var.tags

  names = [
    var.name,
    "rolling-restart",
    "lambda",
  ]
}

module "lambda_version" {
  source  = "rhythmictech/find-release-by-semver/github"
  version = "~> 1.1.1"

  repo_name          = local.repo_name
  repo_owner         = local.repo_owner
  version_constraint = var.lambda_version_constraint
}

locals {
  lambda_version     = module.lambda_version.target_version
  lambda_version_tag = module.lambda_version.version_info.release_tag
}

resource "null_resource" "lambda_zip" {
  triggers = {
    on_version_change = local.lambda_version
  }

  provisioner "local-exec" {
    command = "curl -Lso lambda-${local.lambda_version}.zip https://github.com/${local.repo_full_name}/releases/download/${local.lambda_version_tag}/lambda.zip"
  }
}

data "external" "sha" {
  program = [
    "${path.module}/getsha.sh"
  ]

  query = {
    repo_full_name = local.repo_full_name
    tag            = local.lambda_version_tag
  }
}

data "aws_iam_policy_document" "lambda_assume_role_policy" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name_prefix        = module.tags.name32
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  tags               = module.tags.tags
}

data "aws_iam_policy_document" "lambda_policy_doc" {
  statement {
    actions = [
      "autoscaling:SetInstanceHealth"
    ]

    resources = [
      "arn:aws:autoscaling:${local.region}:${local.account_id}:autoScalingGroup:*:autoScalingGroupName/${var.asg_name}"
    ]
  }
  statement {
    actions = [
      "autoscaling:DescribeAutoScalingGroups"
    ]

    resources = [
      "*"
    ]
  }
  statement {
    actions = [
      "codepipeline:PutJobSuccessResult",
      "codepipeline:PutJobFailureResult"
    ]

    resources = [
      "*"
    ]
  }
}

resource "aws_iam_role_policy" "this" {
  name_prefix = module.tags.name
  role        = aws_iam_role.this.name
  policy      = data.aws_iam_policy_document.lambda_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "lambda-execution-role-attach" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "random_uuid" "lambda_uuid" {}

resource "aws_lambda_function" "this" {
  filename         = "lambda-${local.lambda_version}.zip"
  function_name    = "${module.tags.name32}_${substr(random_uuid.lambda_uuid.result, 0, 31)}"
  role             = aws_iam_role.this.arn
  handler          = "rolling-restart.handler"
  runtime          = "python3.8"
  timeout          = 600
  source_code_hash = data.external.sha.result.sha
  tags             = module.tags.tags

  environment {
    variables = {
      ASG_NAME = var.asg_name
      LOGLEVEL = var.loglevel
    }
  }

  lifecycle {
    ignore_changes = [
      last_modified
    ]
  }

  depends_on = [null_resource.lambda_zip]
}
