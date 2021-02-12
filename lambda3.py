import json
import boto3
import datetime
import os
import urllib3

slackWebhookUrl = os.environ['webHookUrlSlack']

def lambda_handler(event, context):
    ec2 = boto3.resource('ec2')
    client = boto3.client('ec2')
    instances = ec2.instances.filter(
    Filters=[{'Name': 'tag:isBastion', 'Values': ['True']}])
    counter = 0
    bastionArray = []
    for instance in instances:
        counter += 1 # to count the number of bastion hosts
        bastionArray.append(instance.id)
    counterArray = 0
    for bastionId in bastionArray:
        counterArray += 1 # to determine the last occurence
        status = client.describe_instances(InstanceIds=[bastionId])
        for i in status["Reservations"]:
            instance_details = i['Instances'][0]
            stateCurrent = instance_details["State"]["Name"].lower()
            launchTime = instance_details["LaunchTime"]
            currentTime = datetime.datetime.now(launchTime.tzinfo)
            currentDate = currentTime.date()
            if instance_details["State"]["Name"].lower() == "running":
                instanceNameArray = instance_details["Tags"]
                for tag in instanceNameArray:
                    if tag['Key'] == 'Name':
                        instanceName = tag['Value']
                        break
                differenceTime = currentTime - launchTime
                differenceTimeSeconds = differenceTime.total_seconds()
                differenceTimeMinutes = differenceTimeSeconds/60
                differenceTimeHours = differenceTimeMinutes/60
                differenceTimeDays = differenceTimeHours/24
                bastionLink = "https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#InstanceDetails:instanceId="+instance_details["InstanceId"]  # change the region if required
                if counter != 3:
                    slackPayload = payload = {
                    "username" : "Bastion Host Monitoring",
                    "text": "*:alert-light: The number of bastion hosts in <ACCOUNT NAME> account changed. Please check the list here-* https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#Instances:search=<BASTION>", # change the region if required
                    "attachments": [
                        {"fields": [{"title": "Account Name","value": "<ACCOUNT NAME>", "short": True},
                        {"title": "Total Running Time (Days)","value": round(differenceTimeDays,2), "short": True},
                        {"title": "Bastion Instance Name","value": instanceName, "short": True},
                        {"title": "Date (UTC)","value": str(currentDate), "short": True},
                        {"title": "Bastion Instance Link", "value": bastionLink,"short": False}],
                        "color": "#FF0000"}]}
                    sendSlackAlert(json.dumps(slackPayload))
                
                else:
                    slackPayload = payload = {
                    "username" : "Bastion Host Monitoring",
                    "attachments": [
                        {"fields": [{"title": "Account Name","value": "<ACCOUNT NAME>", "short": True},
                        {"title": "Total Running Time (Days)","value": round(differenceTimeDays,2), "short": True},
                        {"title": "Bastion Instance Name","value": instanceName, "short": True},
                        {"title": "Date (UTC)","value": str(currentDate), "short": True},
                        {"title": "Bastion Instance Link", "value": bastionLink,"short": False}],
                        "color": "#f59e42"}]}
                    sendSlackAlert(json.dumps(slackPayload))
            else:
                if counterArray == len(bastionArray):
                    if counter != 3:
                        slackPayload = payload = {
                            "username" : "Bastion Host Monitoring",
                            "text": "*:alert-light: The number of bastion hosts in <ACCOUNT NAME> account changed. Please check the list here-* https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#Instances:search=<BASTION>", # change the region if required
                        sendSlackAlert(json.dumps(slackPayload))
                        
                    
def sendSlackAlert(slackPayload):
    headers = {'Content-type': "application/json"}
    http = urllib3.PoolManager()
    response = http.request('POST', slackWebhookUrl, headers={'Content-Type': 'application/json'}, body=slackPayload)
    print("Slack alert sent successfully")

