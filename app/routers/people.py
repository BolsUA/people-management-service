import os
import jwt
from jwt import PyJWKClient
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from app.schemas import schemas
from app.aws_client import cognito_client

router = APIRouter()

cognito_region = os.getenv('AWS_REGION')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')
keys_url = f'https://cognito-idp.{cognito_region}.amazonaws.com/{cognito_pool_id}/.well-known/jwks.json'

def verify_token(token: str):
    if not token.startswith('Bearer '):
        return False, "Invalid token format"
    
    token = token.split(' ')[1]

    try:
        # Fetch public keys from AWS Cognito
        jwks_client = PyJWKClient(keys_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate the token
        payload = jwt.decode(token, signing_key.key, algorithms=["RS256"])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, "Token expired"
    except Exception:
        return False, "Invalid token"

async def get_user_groups(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")
    
    valid, token = verify_token(authorization)

    if not valid:
        raise HTTPException(status_code=401, detail=token)
    
    try:
        # Get user's groups
        groups_response = cognito_client.admin_list_groups_for_user(
            UserPoolId=os.getenv('COGNITO_USER_POOL_ID'),
            Username=token['username']
        )
        
        return [group['GroupName'] for group in groups_response['Groups']]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token or user not found")
    
async def get_user_info(user_id: str):
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
        return None
    

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
        return get_user_info(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="User not found")
    
@router.post("/internal/users/bulk", response_model=List[schemas.User])
async def get_users(user_ids: List[str]):
    users = []
    for user_id in user_ids:
        try:
            users.append(get_user_info(user_id))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"User {user_id} not found")
    
    return users