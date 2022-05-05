#!/usr/bin/env python3
import boto3
from botocore.exceptions import ClientError
import json
import logging
import os
import time

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logger = logging.getLogger()
logging.basicConfig(level=LOGLEVEL)
ASGNAME = os.environ.get('ASG_NAME')

try:
    client = boto3.client(
        'autoscaling', region_name=os.environ.get('AWS_REGION', 'us-east-1')
    )
except:
    raise

try:
    codepipeline = boto3.client(
        'codepipeline'
    )
except:
    raise


def trigger_auto_scaling_instance_refresh(asg_name, event, strategy="Rolling",
                                          min_healthy_percentage=90, instance_warmup=300):
    try:
        response = client.start_instance_refresh(
            AutoScalingGroupName=asg_name,
            Strategy=strategy,
            Preferences={
                'MinHealthyPercentage': min_healthy_percentage,
                'InstanceWarmup': instance_warmup
            })
        logging.info("Triggered Instance Refresh {} for Auto Scaling "
                     "group {}".format(response['InstanceRefreshId'], asg_name))
        return response['InstanceRefreshId']

    except ClientError as e:
        logging.error("Unable to trigger Instance Refresh for "
                      "Auto Scaling group {}".format(asg_name))
        putJobFailure(event, "Unable to trigger Instance Refresh for "
                             "Auto Scaling group {}".format(asg_name))
        raise e


def check_refresh_success(asg_name, refreshID, event):
    logging.info("Checking Instance Refresh Status")
    result = is_refresh_running(asg_name, refreshID, event)
    while result not in ["Cancelled", "Successful", "Failed"]:
        time.sleep(1)
        result = is_refresh_running(asg_name, refreshID, event)
    if result == "Successful":
        return True
    else:
        putJobFailure(
            event, "Instance refresh for {} failed, {}".format(asg_name, result))


def is_refresh_running(asg_name, refreshID, event):
    try:
        response = client.describe_instance_refreshes(
            AutoScalingGroupName=asg_name,
            InstanceRefreshIds=[
                refreshID
            ]
        )
        return response['InstanceRefreshes'][0]['Status']
    except ClientError as e:
        logging.error("Unable to read Instance Refresh Status for "
                      "Auto Scaling group {} Refresh ID {}".format(
                          asg_name, refreshID)
                      )
        putJobFailure(event, "Unable to read Instance Refresh Status for "
                             "Auto Scaling group {} Refresh ID {}".format(asg_name, refreshID))
        raise e


def putJobSuccess(event):
    response = codepipeline.put_job_success_result(
        jobId=event['CodePipeline.job']['id']
    )


def putJobFailure(event, message):
    response = codepipeline.put_job_failure_result(
        jobId=event['CodePipeline.job']['id'],
        failureDetails={
            'type': 'JobFailed',
            'message': message
        }
    )


def handler(event, context):
    logger.debug('## ENVIRONMENT VARIABLES')
    logger.debug(os.environ)
    logger.debug('## EVENT')
    logger.debug(event)
    logger.info('Replacing instances')
    # Trigger Auto Scaling group Instance Refresh
    refreshID = trigger_auto_scaling_instance_refresh(ASGNAME, event)
    if check_refresh_success(ASGNAME, refreshID, event):
        logger.info(
            'Done! Instance refresh has completed'
        )
        putJobSuccess(event)
        return {
            'statusCode': 200,
            'body': json.dumps('Done! All instances have been replaced and are marked as healthy')
        }
