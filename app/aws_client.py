import os
import boto3

cognito_client = boto3.client('cognito-idp',
    region_name=os.getenv('AWS_REGION')
)