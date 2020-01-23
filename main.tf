module "tags" {
  source = "git::https://github.com/rhythmictech/terraform-terraform-tags.git?ref=v0.0.2"
  tags = var.tags

  names = [
    var.name,
    "rolling-restart",
    "lambda",
  ]
}

data "archive_file" "this" {
  type        = "zip"
  source_file = "rolling-restart.py"
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
  name_prefix        = module.tags.tags["Name"]
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  tags = module.tags.tags
}

data "aws_iam_policy_document" "lambda_policy_doc" {
  statement {
    actions = [
      "autoscaling:SetInstanceHealth",
      "autoscaling:DescribeAutoScalingInstances"
    ]

    resources = [
      "arn:aws:autoscaling:${local.region}:${local.account_id}:*:autoScalingGroupName/${var.asg_name}"
    ]
  }
}

resource "aws_iam_role_policy" "this" {
  name_prefix = module.tags.tags["Name"]
  role = aws_iam_role.this
  policy = data.aws_iam_policy_document.lambda_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "lambda-execution-role-attach" {
  role       = aws_iam_role.pipeline_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "random_uuid" "lambda_uuid" {}


resource "aws_lambda_function" "this" {
  filename         = data.archive_file.pipeline_lambda.output_path
  function_name    = "${module.tags.tags["Name"]}_${random_uuid.lambda_uuid}"
  role             = aws_iam_role.pipeline_lambda.arn
  handler          = "rolling-restart.handler"
  runtime          = "python3.6"
  timeout          = 600
  source_code_hash = data.archive_file.pipeline_lambda.output_base64sha256
  tags             = module.tags.tags

  lifecycle {
    ignore_changes = [
      filename,
      last_modified,
    ]
  }
}
