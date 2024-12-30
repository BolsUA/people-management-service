from typing import List
from pydantic import BaseModel
from pydantic import BaseModel

class UserBasic(BaseModel):
    id: str
    name: str

class User(UserBasic):
    email: str
    groups: List[str]

class InternalUsersBulkRequest(BaseModel):
    user_ids: List[str]