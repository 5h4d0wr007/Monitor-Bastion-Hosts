# make sure all the triggers to this function are active

import json
import boto3
import datetime
import os
import urllib3

slackWebhookUrl = os.environ['webHookUrlSlack']

def lambda_handler(event, context):
    currentBH = event['instanceIdLambda2']
    client = boto3.client("ec2")
    status = client.describe_instances(InstanceIds=[currentBH])
    for i in status["Reservations"]:
        instanceDetails = i['Instances'][0]
        stateCurrent = instanceDetails["State"]["Name"].lower()
        launchTime = instanceDetails["LaunchTime"]
        currentTime = datetime.datetime.now(launchTime.tzinfo)
        currentDate = currentTime.date()
        if instanceDetails["State"]["Name"].lower() == "running":
            differenceTime = currentTime - launchTime
            differenceTimeSeconds = differenceTime.total_seconds()
            differenceTimeMinutes = differenceTimeSeconds/60
            differenceTimeHours = differenceTimeMinutes/60
            differenceTimeDays = differenceTimeHours/24
            bhLink = "https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#InstanceDetails:instanceId="+instanceDetails["InstanceId"]  # change the region if required
            
            # to trigger the alert when the total running time > 2 days
            if differenceTimeDays > 1.9:
                print("The bastion instance has been left running for more than 2 days")
                slackPayload = payload = {
                    "username" : "Bastion Host Monitoring",
                    "text": "*:alert-light: The bastion host has been left running for more than 2 days*",
                    "attachments": [
                        {"fields": [{"title": "Account Name","value": "<ACCOUNT NAME>", "short": True},
                        {"title": "Total Running Time (Hours)","value": round(differenceTimeHours,2), "short": True},
                        {"title": "Bastion Instance ID","value": instanceDetails["InstanceId"], "short": True},
                        {"title": "Date (UTC)","value": str(currentDate), "short": True},
                        {"title": "Bastion Instance Link", "value": bhLink,"short": False}],
                        "color": "#FF0000"}]}
                sendSlackAlert(json.dumps(slackPayload))
        else:
            print("Bastion host is not running")

def sendSlackAlert(slackPayload):
        headers = {'Content-type': "application/json"}
        http = urllib3.PoolManager()
        response = http.request('POST', slackWebhookUrl, headers={'Content-Type': 'application/json'}, body=slackPayload)
        print("Slack alert sent successfully")
