#!/usr/bin/env python3
import boto3
import json
import logging
import os
import time

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logger = logging.getLogger()
logging.basicConfig(level=LOGLEVEL)

try:
    client = boto3.client(
        'autoscaling', region_name=os.environ.get('AWS_REGION', 'us-east-1')
    )
except:
    raise


def getAsg(name):
    try:
        asg = client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[args.name],
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
        while isAsgHealthy(getAsg(args.name)) or len(getAsgInstances(getAsg(args.name))) < targetNum:
            time.sleep(1)
        logger.info('Waiting for all instances to be marked healthy')
        while not isAsgHealthy(getAsg(args.name)) and len(getAsgInstances(getAsg(args.name))) == targetNum:
            time.sleep(1)


def handler(event, context):
    logger.debug('## ENVIRONMENT VARIABLES')
    logger.debug(os.environ)
    logger.debug('## EVENT')
    logger.debug(event)

    targetInstances = getAsgInstances(getAsg(os.environ.get('ASG_NAME')))
    logger.info('Waiting for all instances to be marked healthy')
    while not isAsgHealthy(getAsg(args.name)):
        time.sleep(1)
    logger.info('Replacing instances')
    replaceInstances(targetInstances)
    logger.info(
        'Done! All instances have been replaced and are marked as healthy'
    )
    return {
        'statusCode': 200,
        'body': json.dumps('Done! All instances have been replaced and are marked as healthy')
    }
