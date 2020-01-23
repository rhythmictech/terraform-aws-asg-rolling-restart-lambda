module "tags" {
  source = "git::https://github.com/rhythmictech/terraform-terraform-tags.git?ref=v0.0.2"
  tags   = var.tags

  names = [
    var.name,
    "rolling-restart",
    "lambda",
  ]
}

data "archive_file" "this" {
  type        = "zip"
  source_file = "${path.module}/rolling-restart.py"
  output_path = "${path.module}/tmp/lambda.zip"
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
      "autoscaling:SetInstanceHealth",
      "autoscaling:DescribeAutoScalingGroups"
    ]

    resources = [
      "arn:aws:autoscaling:${local.region}:${local.account_id}:*:autoScalingGroupName/${var.asg_name}"
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
  filename         = data.archive_file.this.output_path
  function_name    = "${module.tags.name32}_${substr(random_uuid.lambda_uuid.result, 0, 31)}"
  role             = aws_iam_role.this.arn
  handler          = "rolling-restart.handler"
  runtime          = "python3.6"
  timeout          = 600
  source_code_hash = data.archive_file.this.output_base64sha256
  tags             = module.tags.tags
  environment {
    variables = {
      ASG_NAME   = var.asg_name
      LOGLEVEL   = var.loglevel
    }
  }
  lifecycle {
    ignore_changes = [
      filename,
      last_modified,
    ]
  }
}
