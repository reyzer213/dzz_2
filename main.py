from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import jwt
from jwt import PyJWTError

app = FastAPI()
templates = Jinja2Templates(directory="templates")


SQLALCHEMY_DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True)
    password_hash = Column(String)

# Створення таблиці в базі даних
Base.metadata.create_all(bind=engine)

# Хешування паролів
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserBase(BaseModel):
    login: str

class UserCreate(UserBase):
    password: str

class UserLogin(UserBase):
    password: str

# Функція для отримання хешу пароля
def get_password_hash(password):
    return pwd_context.hash(password)

# Функція для верифікації пароля
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Функція для отримання користувача з бази даних
def get_user(login: str):
    return db.query(User).filter(User.login == login).first()

# Реєстрація нового користувача
@app.post("/users/", response_model=User)
async def create_user(user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(login=user.login, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Аутентифікація користувача та видача токену доступу
@app.post("/login/")
async def login(user: UserLogin):
    db_user = get_user(user.login)
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Неправильний логін або пароль")
    access_token_expires = timedelta(minutes=30)
    to_encode = {"sub": db_user.login, "exp": datetime.utcnow() + access_token_expires}
    encoded_jwt = jwt.encode(to_encode, "SECRET_KEY", algorithm="HS256")
    return {"access_token": encoded_jwt, "token_type": "bearer"}



tracks = []  # Список для зберігання треків


class Track:
    def __init__(self, title: str, artist: str, duration: int):
        self.title = title
        self.artist = artist
        self.duration = duration


@app.get("/tracks", response_class=HTMLResponse)
async def get_tracks():
    return templates.TemplateResponse("tracks.html", {"request": None, "tracks": tracks})


@app.get("/track/{track_id}", response_class=HTMLResponse)
async def get_track(track_id: int):
    # Знайдемо трек з вказаним ідентифікатором (індексом у списку)
    try:
        track = tracks[track_id]
    except IndexError:
        raise HTTPException(status_code=404, detail="Track not found")
    return templates.TemplateResponse("track.html", {"request": None, "track": track})


@app.post("/tracks")
async def add_track(title: str, artist: str, duration: int):
    new_track = Track(title=title, artist=artist, duration=duration)
    tracks.append(new_track)
    return {"message": "Track added successfully"}


@app.put("/track/{track_id}")
async def update_track(track_id: int, title: str, artist: str, duration: int):
    try:
        track = tracks[track_id]
    except IndexError:
        raise HTTPException(status_code=404, detail="Track not found")

    track.title = title
    track.artist = artist
    track.duration = duration

    return {"message": "Track updated successfully"}


@app.delete("/track/{track_id}")
async def delete_track(track_id: int):
    try:
        del tracks[track_id]
    except IndexError:
        raise HTTPException(status_code=404, detail="Track not found")
    return {"message": "Track deleted successfully"}
