from jose import JWTError,jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException,status,Depends
from . import schemas,models
from .database import get_db
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/login') #login is the path where user will send username and password to get the token




SECRET_KEY = os.getenv("SECRET_KEY", "some_random_secret_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES =  int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))


def create_access_token(data : dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp":expire})
    
    encoded_jwt = jwt.encode(to_encode,key=SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token : str,credentials_exception):
    try:
        payload = jwt.decode(token,key=SECRET_KEY,algorithms=[ALGORITHM])
        id : int = payload.get("user_id") # type: ignore
        
        if id is None:
            raise credentials_exception
        
        token_data = schemas.TokenData(id=id)    #token data contains user_id for now
    
    except JWTError:
        raise credentials_exception
    
    return token_data

def get_current_user(token:str = Depends(oauth2_scheme), db : Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_access_token(token,credentials_exception)
    
    user = db.query(models.User).filter(models.User.id == token_data.id).first()
    
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND,detail="User not found") #change it to credentials_exception later
    
    return user