from fastapi import APIRouter, HTTPException, status, Depends
from ..database import get_db 
from sqlalchemy.orm import Session
from .. import schemas, models, oauth2, utils
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(tags=["Authentication"])

@router.post("/login",status_code=status.HTTP_200_OK,response_model=schemas.Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db:Session = Depends(get_db)):
    
    #1. find username from db
    user = db.query(models.User).filter(models.User.username == user_credentials.username).first()
    
    if not user:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
    
    #2. verify password
    if not utils.verify(user_credentials.password, user.hashed_password): # type: ignore
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
        
    #3. create a access_token
    access_token = oauth2.create_access_token({"user_id" : str(user.id)})
    return {"access_token" : access_token, "token_type" : "bearer"}
    