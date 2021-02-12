import boto3
import json
from datetime import datetime
import os
import urllib3

slackWebhookUrl = os.environ['webHookUrlSlack']

def lambda_handler(event, context):
    instanceBId = event['detail']['instance-id']
    lambdaClient = boto3.client('lambda')
    eventsClient = boto3.client('events')
    ec2Client = boto3.client('ec2')
    ec2Status = ec2Client.describe_instances(InstanceIds=[instanceBId])
    for i in ec2Status["Reservations"]:
        stateCurrent = i['Instances'][0]["State"]["Name"].lower()
        instanceDetails = i['Instances'][0]
        if stateCurrent == "running":
            fnName = "<FUNCTION NAME>"
            fnArn = "<FUNCTION ARN>"
            currentTime = datetime.now()
            year = currentTime.year
            month = currentTime.month
            day = currentTime.day
            hour = currentTime.hour
            minute = currentTime.minute

            # alarm event -> T+2 days
            if month == 1 or month == 3 or month == 5 or month == 7 or month == 8 or month == 10 or month == 12:
                if day == 31:
                    if month == 12:
                        frequency = "cron("+str(minute)+" "+str(hour)+" "+str(2)+" "+str(1)+" "+"?"+" "+str(year+1)+")" #UTC time zone
                    else:
                        frequency = "cron("+str(minute)+" "+str(hour)+" "+str(2)+" "+str(month+1)+" "+"?"+" "+str(year)+")" #UTC time zone
                elif day == 30:
                    if month == 12:
                        frequency = "cron("+str(minute)+" "+str(hour)+" "+str(1)+" "+str(1)+" "+"?"+" "+str(year+1)+")" #UTC time zone
                    else:
                        frequency = "cron("+str(minute)+" "+str(hour)+" "+str(1)+" "+str(month+1)+" "+"?"+" "+str(year)+")" #UTC time zone
                else:
                    frequency = "cron("+str(minute)+" "+str(hour)+" "+str(day+2)+" "+str(month)+" "+"?"+" "+str(year)+")" #UTC time zone                    
            elif month == 4 or month == 6 or month == 9 or month == 11:
                if day == 30:
                    frequency = "cron("+str(minute)+" "+str(hour)+" "+str(2)+" "+str(month+1)+" "+"?"+" "+str(year)+")" #UTC time zone
                elif day == 29:
                    frequency = "cron("+str(minute)+" "+str(hour)+" "+str(1)+" "+str(month+1)+" "+"?"+" "+str(year)+")" #UTC time zone
                else:
                    frequency = "cron("+str(minute)+" "+str(hour)+" "+str(day+2)+" "+str(month)+" "+"?"+" "+str(year)+")" #UTC time zone                    
            elif year%4 == 0 and year%100 != 0 or year%400 == 0:
                if day == 29:
                    frequency = "cron("+str(minute)+" "+str(hour)+" "+str(2)+" "+str(month+1)+" "+"?"+" "+str(year)+")" #UTC time zone
                elif day == 28:
                    frequency = "cron("+str(minute)+" "+str(hour)+" "+str(1)+" "+str(month+1)+" "+"?"+" "+str(year)+")" #UTC time zone
                else:
                    frequency = "cron("+str(minute)+" "+str(hour)+" "+str(day+2)+" "+str(month)+" "+"?"+" "+str(year)+")" #UTC time zone            
            else:
                if day == 28:
                    frequency = "cron("+str(minute)+" "+str(hour)+" "+str(2)+" "+str(month+1)+" "+"?"+" "+str(year)+")" #UTC time zone
                elif day == 27:
                    frequency = "cron("+str(minute)+" "+str(hour)+" "+str(1)+" "+str(month+1)+" "+"?"+" "+str(year)+")" #UTC time zone
                else:
                    frequency = "cron("+str(minute)+" "+str(hour)+" "+str(day+2)+" "+str(month)+" "+"?"+" "+str(year)+")" #UTC time zone
            
            name = "{0}-<RULE NAME>".format(instanceBId) # unique for each instance
            
            # adding the CloudWatch rule
            ruleResponse = eventsClient.put_rule(
                Name = name,
                ScheduleExpression = frequency,
                State = "ENABLED",
                )
                
            """
            # giving permission to the CloudWatch rule to trigger the target Lambda
            lambdaClient.add_permission(
                FunctionName = fnName,
                StatementId = "<ID>",
                Action = "lambda:InvokeFunction",
                Principal = "events.amazonaws.com",
                SourceArn = ruleResponse['RuleArn'],
                )
            """
            
            # adding Lambda function as a target
            eventsClient.put_targets(
                Rule = name,
                Targets = [
                    {
                        'Id': "1",
                        'Arn': fnArn,
                        'Input': '{"instanceIdLambda2":"' +str(instanceDetails["InstanceId"])+ '"}'
                    },
                    ]
                    )

            # change the region if required
            cwLink = "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#rules:name=" + name 
            bastionLink = "https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#InstanceDetails:instanceId="+instanceDetails["InstanceId"]
            slackPayload = payload = {
                "username": "Bastion Host Monitoring",
                "text": "*The bastion instance has been started*",
                "attachments": [
                    {"fields": [
                        {"title": "Account Name","value": "<ACCOUNT NAME>", "short": True},
                        {"title": "Bastion Instance ID","value": instanceDetails["InstanceId"], "short": True},
                        {"title": "Updated CloudWatch Rule","value": cwLink, "short": False},
                        {"title": "Bastion Instance Link", "value": bastionLink,"short": False}],
                        "color": "#FFFF00"}
                    ]
                    }
            sendSlackAlert(json.dumps(slackPayload))

        # change the region if required
        elif stateCurrent == "stopped":
            print("Bastion instance in stopped state")
            bastionLink = "https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#InstanceDetails:instanceId="+instanceDetails["InstanceId"]
            slackPayload = payload = {
                "username": "Bastion Host Monitoring",
                "text": "*The bastion instance has been stopped*",
                "attachments": [
                    {"fields": [
                        {"title": "Account Name","value": "<ACCOUNT NAME>", "short": True},
                        {"title": "Bastion Instance ID","value": instanceDetails["InstanceId"], "short": True},
                        {"title": "Bastion Instance Link", "value": bastionLink,"short": False}],
                        "color": "#008000"}
                        ]
                
            }
            sendSlackAlert(json.dumps(slackPayload))            
        else:
            print("Neither running nor stopped state")

def sendSlackAlert(slackPayload):
    headers = {'Content-type': "application/json"}
    http = urllib3.PoolManager()
    response = http.request('POST', slackWebhookUrl, headers={'Content-Type': 'application/json'}, body=slackPayload)
    print("Slack alert sent successfully")
    print(response.data) 
