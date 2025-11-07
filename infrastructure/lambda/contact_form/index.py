"""
JoyofPM Contact Form Lambda Handler
Processes contact form submissions, saves to DynamoDB, and sends email notifications
"""

import json
import os
import uuid
import time
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

# Environment variables
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
RECIPIENT_EMAIL = os.environ['RECIPIENT_EMAIL']
CALENDLY_LINK = os.environ['CALENDLY_LINK']

def handler(event, context):
    """
    Lambda handler for contact form submissions
    """

    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': 'https://joyofpm.com',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST,OPTIONS',
        'Content-Type': 'application/json'
    }

    try:
        # Parse request body
        body = json.loads(event['body'])

        # Validate required fields
        required_fields = ['firstName', 'lastName', 'email', 'interest']
        for field in required_fields:
            if not body.get(field):
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'error': f'Missing required field: {field}'
                    })
                }

        # Generate submission ID and timestamp
        submission_id = str(uuid.uuid4())
        timestamp = int(time.time())

        # Prepare DynamoDB item
        table = dynamodb.Table(DYNAMODB_TABLE)
        item = {
            'submission_id': submission_id,
            'timestamp': timestamp,
            'firstName': body['firstName'],
            'lastName': body['lastName'],
            'email': body['email'],
            'company': body.get('company', ''),
            'interest': body['interest'],
            'message': body.get('message', ''),
            'submitted_at': datetime.fromtimestamp(timestamp).isoformat(),
            'ttl': timestamp + (365 * 24 * 60 * 60)  # 1 year retention
        }

        # Save to DynamoDB
        table.put_item(Item=item)

        # Send email notification
        send_email_notification(body, submission_id)

        # Return success response with Calendly link
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'Thank you for your interest! We will be in touch soon.',
                'calendly_link': CALENDLY_LINK,
                'submission_id': submission_id
            })
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': 'Invalid JSON in request body'
            })
        }

    except ClientError as e:
        print(f"AWS Error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Failed to process submission. Please try again.'
            })
        }

    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'An unexpected error occurred. Please try again.'
            })
        }


def send_email_notification(form_data, submission_id):
    """
    Send email notification to recipient
    """

    # Build email subject
    subject = f"New Contact Form Submission - {form_data['firstName']} {form_data['lastName']}"

    # Build email body
    html_body = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                line-height: 1.6;
                color: #1A2332;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #4ECDC4;
                color: white;
                padding: 20px;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                background-color: #F7F9FC;
                padding: 30px;
                border-radius: 0 0 8px 8px;
            }}
            .field {{
                margin-bottom: 15px;
            }}
            .label {{
                font-weight: 600;
                color: #1A2332;
                margin-bottom: 5px;
            }}
            .value {{
                color: #64748B;
                padding: 8px;
                background-color: white;
                border-radius: 4px;
            }}
            .footer {{
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                font-size: 12px;
                color: #64748B;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin: 0;">🎯 New Contact Form Submission</h2>
            </div>
            <div class="content">
                <div class="field">
                    <div class="label">Name:</div>
                    <div class="value">{form_data['firstName']} {form_data['lastName']}</div>
                </div>

                <div class="field">
                    <div class="label">Email:</div>
                    <div class="value"><a href="mailto:{form_data['email']}">{form_data['email']}</a></div>
                </div>

                <div class="field">
                    <div class="label">Company:</div>
                    <div class="value">{form_data.get('company', 'Not provided')}</div>
                </div>

                <div class="field">
                    <div class="label">Interest:</div>
                    <div class="value">{form_data['interest']}</div>
                </div>

                <div class="field">
                    <div class="label">Message:</div>
                    <div class="value">{form_data.get('message', 'No message provided')}</div>
                </div>

                <div class="footer">
                    <strong>Submission ID:</strong> {submission_id}<br>
                    <strong>Submitted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_body = f"""
    New Contact Form Submission

    Name: {form_data['firstName']} {form_data['lastName']}
    Email: {form_data['email']}
    Company: {form_data.get('company', 'Not provided')}
    Interest: {form_data['interest']}

    Message:
    {form_data.get('message', 'No message provided')}

    ---
    Submission ID: {submission_id}
    Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
    """

    try:
        response = ses.send_email(
            Source=RECIPIENT_EMAIL,
            Destination={
                'ToAddresses': [RECIPIENT_EMAIL]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        print(f"Email sent! Message ID: {response['MessageId']}")
        return True

    except ClientError as e:
        print(f"Error sending email: {e}")
        # Don't fail the submission if email fails
        return False
