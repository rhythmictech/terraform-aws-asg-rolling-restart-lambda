#!/usr/bin/env python3
import argparse
import boto3
import time
import json

parser = argparse.ArgumentParser(
    description='This is a simple script to redeploy all instances in an autoscaling group'
)

parser.add_argument(
    '-n',
    '--name',
    help='The name of the AutoScaling Group you want to restart',
    required=True
)

parser.add_argument(
    '-r',
    '--region',
    help='The region you are targetting',
    required=True
)

args = parser.parse_args()
client = boto3.client('autoscaling', region_name=args.region)


def getAsg(name):
    try:
        asg = client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[args.name],
            MaxRecords=100
        )
        if len(asg['AutoScalingGroups']) > 1:
            raise LookupError("Found too many ASGs")
        elif len(asg['AutoScalingGroups']) == 0:
            raise LookupError("Found no ASGs")
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
        print('Waiting for instance to be marked unhealthy')
        while isAsgHealthy(getAsg(args.name)):
            time.sleep(1)
        print('Waiting for all instances to be marked healthy')
        while ! isAsgHealthy(getAsg(args.name)):
            time.sleep(1)


targetInstances = getAsgInstances(getAsg(args.name))

print('Waiting for all instances to be marked healthy')
while ! isAsgHealthy(getAsg(args.name)):
    time.sleep(1)
replaceInstances(targetInstances)
