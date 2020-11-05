#!/usr/bin/env python3
import boto3
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


def getAsg(name):
    try:
        asg = client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[ASGNAME],
            MaxRecords=100
        )
        if len(asg['AutoScalingGroups']) > 1:
            raise Exception("Found too many ASGs")
        elif len(asg['AutoScalingGroups']) == 0:
            raise Exception("Found no ASGs")
        return asg
    except:
        raise


def getAsgInstances(obj):
    try:
        return [instance['InstanceId'] for instance in obj['AutoScalingGroups'][0]['Instances']]
    except:
        raise


def isAsgHealthy(obj):
    try:
        return all(instance['HealthStatus'] == 'Healthy' for instance in obj['AutoScalingGroups'][0]['Instances'])
    except:
        raise


def replaceInstances(idList):
    targetNum = len(idList)
    for id in idList:
        try:
            client.set_instance_health(
                InstanceId=id,
                HealthStatus='Unhealthy',
                ShouldRespectGracePeriod=False
            )
        except:
            raise
        # I want to make sure the instance is marked as unhealthy before I start looking for the new one
        logger.info('Waiting for instance to be marked unhealthy')
        while isAsgHealthy(getAsg(ASGNAME)) or len(getAsgInstances(getAsg(ASGNAME))) < targetNum:
            time.sleep(1)
        logger.info('Waiting for all instances to be marked healthy')
        while not isAsgHealthy(getAsg(ASGNAME)) and len(getAsgInstances(getAsg(ASGNAME))) == targetNum:
            time.sleep(1)


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

    targetInstances = getAsgInstances(getAsg(ASGNAME))
    logger.info('Waiting for all instances to be marked healthy')
    while not isAsgHealthy(getAsg(ASGNAME)):
        time.sleep(1)
    logger.info('Replacing instances')
    replaceInstances(targetInstances)
    logger.info(
        'Done! All instances have been replaced and are marked as healthy'
    )
    putJobSuccess(event)
    return {
        'statusCode': 200,
        'body': json.dumps('Done! All instances have been replaced and are marked as healthy')
    }
