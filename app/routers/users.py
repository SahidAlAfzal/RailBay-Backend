from fastapi import HTTPException,status,Depends,APIRouter,Response
from sqlalchemy.orm import Session
from .. import schemas,models,utils,oauth2
from ..database import get_db
from ..oauth2 import get_current_user


router = APIRouter(prefix="/users",tags=["Users"])


@router.post("/",status_code=status.HTTP_201_CREATED,response_model=schemas.UserResponse)
def create_user(user : schemas.UserCreate, db : Session = Depends(get_db)):
    #1. hash the password
    hashed_password = utils.hash_password(user.password)
    user.password = hashed_password
    
    #2.Create Model
    new_user = models.User(
        username = user.username,
        email = user.email,
        hashed_password = user.password
    )
    
    #3 save to db
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        raise HTTPException(status.HTTP_409_CONFLICT,detail="Username or Email already exists")
    
    return new_user



@router.get("/{id}",status_code=status.HTTP_200_OK,response_model=schemas.UserResponse)
def get_user(id: int, db : Session = Depends(get_db)):
    
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"User not found")
    
    return user





@router.put("/me",status_code=status.HTTP_200_OK,response_model=schemas.UserResponse)
def update_user(user_update: schemas.UserUpdate, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    
    if user_update.username:
        existing_user = db.query(models.User).filter(models.User.username == user_update.username).first()
        
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Usename already exists")
        
        current_user.username = user_update.username
        
    if user_update.email:
        existing_user = db.query(models.User).filter(models.User.email == user_update.email).first()
        
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Email already exists")
        
        current_user.email = user_update.email
        
    
    if user_update.password:
        hashed_password = utils.hash_password(user_update.password)
        current_user.hashed_password = hashed_password
        

    db.commit()
    db.refresh(current_user)
    
    return current_user      #validated with UserResponse




@router.delete("/me",status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(db : Session = Depends(get_db), current_user = Depends(get_current_user)):
    
    db.delete(current_user)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

