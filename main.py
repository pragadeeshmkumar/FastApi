from sqlalchemy import create_engine, engine, Column, Integer, String, Text, ForeignKey, Enum, DateTime
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import sessionmaker, relationship, Session
from fastapi import FastAPI,HTTPException, status
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional
from passlib.context import CryptContext
from jose import jwt,JWTError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY='32db92a32a3f14df9e89e0bef46ed21fa6a9a8c678a3d8b178693b1c1f2506ae'
ALGORITHM='HS256'
ACCESS_TOKEN_EXPIRE_MINUTES=20
oauth2_scheme=OAuth2PasswordBearer(tokenUrl='api/login')
SQLALCHEMY_DATABASE_URL = ""

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker( bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class UserRole(PyEnum):
    admin = "admin"
    author = "author"
    reader = "reader"

class User(Base):
    __tablename__ = "pragadeesh_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.reader)

class Post(Base):
    __tablename__ = "pragadeesh_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("pragadeesh_users.id"))
    created_at = Column(TIMESTAMP(timezone=True),nullable=False,server_default=text('now()'))
    author = relationship("User")

class Comment(Base):
    __tablename__ = "pragadeesh_comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    post_id = Column(Integer, ForeignKey("pragadeesh_posts.id"))
    user_id = Column(Integer, ForeignKey("pragadeesh_users.id"))
    created_at = Column(TIMESTAMP(timezone=True),nullable=False,server_default=text('now()'))
    user = relationship("User")
    post = relationship("Post")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password_hash: str
    role: UserRole = Field(default=UserRole.reader)

class Login(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[int]=None

class PostCreate(BaseModel):
    title: str
    content: str

def generate_token(data:dict):
    to_encode=data.copy()
    expire = datetime.now()+timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp':expire})
    encoded_jwt=jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("user_id")
        if id is None:
            raise credentials_exception
        token_data=TokenData(id=id)
        user = db.query(User).filter(User.id == token_data.id).first()
        if user is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user

@app.post("/api/register", response_model=UserCreate)
def register(request: UserCreate, db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(request.password_hash)
    db_user = User(username=request.username, email=request.email, password_hash=hashed_password, role=request.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/login")
def login(request: OAuth2PasswordRequestForm=Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    access_token=generate_token(data={'user_id':user.id})
    return {'access_token':access_token,'token_type':'bearer'}

@app.post("/api/posts")
def create_post(request: PostCreate, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    db_user = db.query(User).filter(User.id == current_user.id).first()
    if db_user.role not in [UserRole.admin, UserRole.author]:
        raise HTTPException(status_code=403)
    new_post = Post(title=request.title, content=request.content, author_id=current_user.id,created_at=datetime.now())
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@app.get("/api/posts")
def get_posts(author: Optional[str] = None, page: int = 1, db: Session = Depends(get_db)):
    query = db.query(Post)
    if author:
        query = query.join(User).filter(User.username == author)
    posts = query.offset((page-1)*2).limit(2).all()
    return posts

@app.post("/api/posts/{post_id}/comments")
def add_comment(post_id: int, comment: str, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404)
    new_comment = Comment(content=comment, post_id=post_id, user_id=current_user.id,created_at=datetime.now())
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment
