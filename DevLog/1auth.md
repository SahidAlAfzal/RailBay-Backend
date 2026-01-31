# Authentication
These APIs involved in authentiacation following - 
* routers/auth.py    ----> contains "login"  
* routers/users.py   ----> contains CRUD operations on user

---

## auth.py
```python
@router.post("/login",status_code=status.HTTP_200_OK,response_model=schemas.Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db:Session = Depends(get_db)):
```

> OAuth2PasswordRequestForm has two fields
* username (username taken not email)
* password (plain password)

On successful username fetch if *hash(plain_password)* matches with database's hashed_password(done through **utils.verify()**)  
JWT token is generated using **oauth2.create_access_token()** 

Each **protected Route** verifies JWT token of user by Depends **oauth2.get_current_user**  which uses **oauth2.verify_access_token()**.
