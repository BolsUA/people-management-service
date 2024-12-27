import json
import os
import jwt
import requests
from jwt.algorithms import RSAAlgorithm
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from app.schemas import schemas
from app.aws_client import cognito_client

router = APIRouter()

cognito_region = os.getenv('AWS_REGION')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')
keys_url = f'https://cognito-idp.{cognito_region}.amazonaws.com/{cognito_pool_id}/.well-known/jwks.json'
keys_response = requests.get(keys_url)
public_keys = keys_response.json()['keys']

def decode_token(token: str):
    if not token.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    token = token.split(' ')[1]

    headers = jwt.get_unverified_header(token)
    key_id = headers['kid']
    public_key = next((key for key in public_keys if key['kid'] == key_id), None)

    if not public_key:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    public_key_pem = RSAAlgorithm.from_jwk(json.dumps(public_key))
    decoded_token = jwt.decode(
        token,
        key=public_key_pem,
        algorithms=['RS256']
    )

    return decoded_token    

async def get_user_groups(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")
    
    try:
        decoded_token = decode_token(authorization)
       
        # Get user's groups
        groups_response = cognito_client.admin_list_groups_for_user(
            UserPoolId=os.getenv('COGNITO_USER_POOL_ID'),
            Username=decoded_token['username']
        )
        
        return [group['GroupName'] for group in groups_response['Groups']]
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token or user not found")
    

@router.get("/jury-members", response_model=List[schemas.UserBasic])
async def get_jury_members(groups: List[str] = Depends(get_user_groups)):
    """Get all jury members - only accessible by users in the 'proposals' group"""
    
    if 'proposers' not in groups:
        raise HTTPException(
            status_code=403,
            detail="Only users in the proposers group can access this endpoint"
        )
    
    try:
        # List users with the 'jury' group filter
        response = cognito_client.list_users_in_group(
            UserPoolId=os.getenv('COGNITO_USER_POOL_ID'),
            GroupName='jury'
        )

        jury_members = []
        for user in response['Users']:
            attributes = {
                attr['Name']: attr['Value']
                for attr in user['Attributes']
            }
            
            jury_members.append(schemas.UserBasic(
                id=user['Username'],
                name=attributes.get('name', user['Username'])
            ))
            
        return jury_members
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching jury members")

@router.get("/internal/users/{user_id}", response_model=schemas.User)
async def get_user(user_id: str):
    try:
        response = cognito_client.admin_get_user(
            UserPoolId=os.getenv('COGNITO_USER_POOL_ID'),
            Username=user_id
        )
        
        attributes = {
            attr['Name']: attr['Value']
            for attr in response['UserAttributes']
        }

        groups_response = cognito_client.admin_list_groups_for_user(
            UserPoolId=os.getenv('COGNITO_USER_POOL_ID'),
            Username=user_id
        )
        
        return schemas.User(
            id=response['Username'],
            name=attributes.get('name', response['Username']),
            email=attributes.get('email', ''),
            groups=[group['GroupName'] for group in groups_response['Groups']]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="User not found")