from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, desc, asc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy import event
from passlib.context import CryptContext
from datetime import datetime, timedelta
from pydantic import BaseModel, constr
from typing import List, Optional
import jwt
import time

# -----------------------------
# Настройки приложения и БД
# -----------------------------
import os
from dotenv import load_dotenv

load_dotenv() # Загружаем переменные из .env файла

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASS = os.getenv("POSTGRES_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -----------------------------
# Модели БД
# -----------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    tasks = relationship("Task", back_populates="owner")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    status = Column(String, index=True, default="в ожидании")
    created_at = Column(DateTime, default=datetime.utcnow)
    priority = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="tasks")

# -----------------------------
# Pydantic-схемы
# -----------------------------
class TaskCreate(BaseModel):
    title: str
    description: str
    status: str = "в ожидании"
    priority: Optional[int] = 0

class TaskUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    status: Optional[str]
    priority: Optional[int]

class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    status: str
    created_at: datetime
    priority: int

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=6)

class Token(BaseModel):
    access_token: str
    token_type: str

# -----------------------------
# Безопасность и JWT
# -----------------------------
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

# -----------------------------
# Зависимости
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return user

# -----------------------------
# Кэширование (простой in-memory кэш для GET /tasks без параметров)
# -----------------------------
CACHE_TIMEOUT = 30  # секунд
cache_data = {
    "tasks": None,
    "timestamp": 0
}

def clear_cache():
    cache_data["tasks"] = None
    cache_data["timestamp"] = 0

# -----------------------------
# Инициализация приложения
# -----------------------------
app = FastAPI()

@app.on_event("startup")
def startup():
    # Автоматическая инициализация таблиц
    Base.metadata.create_all(bind=engine)
    # Автоматическое создание пользователя admin/admin, если не существует
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin")
            )
            db.add(admin_user)
            db.commit()
            print("Пользователь admin создан!")
    finally:
        db.close()

@event.listens_for(Task, "init", propagate=True)
def _task_init(target, args, kwargs):
    if "priority" not in kwargs:
        target.priority = 0

# -----------------------------
# Эндпоинты аутентификации
# -----------------------------
@app.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    new_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer", "username": new_user.username}

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверные имя пользователя или пароль")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# -----------------------------
# CRUD для задач
# -----------------------------
@app.post("/tasks", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        owner_id=current_user.id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    clear_cache()  # обновляем кэш
    return db_task

@app.get("/tasks", response_model=List[TaskOut])
def get_tasks(
    sort_by: Optional[str] = None,          # 'title', 'status', 'created_at', 'priority'
    order: Optional[str] = "asc",           # 'asc' или 'desc'
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Если нет параметров сортировки и поиска – проверяем кэш
    if sort_by is None and search is None:
        now = time.time()
        if cache_data["tasks"] is not None and now - cache_data["timestamp"] < CACHE_TIMEOUT:
            return cache_data["tasks"]

    query = db.query(Task).filter(Task.owner_id == current_user.id)
    if search:
        # простой поиск подстроки в заголовке или описании
        query = query.filter(
            (Task.title.contains(search)) | (Task.description.contains(search))
        )
    if sort_by:
        if sort_by not in {"title", "status", "created_at", "priority"}:
            raise HTTPException(status_code=400, detail="Неверный параметр сортировки")
        sort_column = getattr(Task, sort_by)
        if order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    tasks = query.all()

    if sort_by is None and search is None:
        cache_data["tasks"] = tasks
        cache_data["timestamp"] = time.time()
    return tasks

@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task

@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    for field, value in task_update.dict(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    clear_cache()  # обновляем кэш
    return task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    db.delete(task)
    db.commit()
    clear_cache()  # обновляем кэш
    return {"detail": "Задача удалена"}

# -----------------------------
# Эндпоинт топ-N задач по приоритету
# -----------------------------
@app.get("/tasks/top/", response_model=List[TaskOut])
def top_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    n: int = 5,
    priority: Optional[int] = Query(None, description="Если указан, выводим только задачи с этим приоритетом"),
    all_priorities: bool = False
):
    """
    Выводит список из n задач с учётом приоритета.
    Параметры:
    - n: количество выводимых задач
    - priority: если указан, выводим только этот приоритет
    - all_priorities: если True, выводим задачи всех приоритетов в порядке возрастания
      (при этом игнорируем значение 'priority')
    """
    query = db.query(Task).filter(Task.owner_id == current_user.id)

    if priority is not None and not all_priorities:
        # Если указан конкретный приоритет, фильтруем по нему
        query = query.filter(Task.priority == priority)
        # Логично отсортировать по дате создания (самые новые первыми) или как вам удобно
        tasks = query.order_by(desc(Task.created_at)).limit(n).all()

    elif all_priorities:
        # Если галочка "Все приоритеты", выводим n задач,
        # начиная с наименьшего приоритета и далее
        tasks = query.order_by(asc(Task.priority), desc(Task.created_at)).limit(n).all()

    else:
        # По умолчанию – "топ" в смысле самых высоких приоритетов
        tasks = query.order_by(desc(Task.priority), desc(Task.created_at)).limit(n).all()

    return tasks


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task

# -----------------------------
# Краткое объяснение кэширования:
#
# Для эндпоинта GET /tasks, когда нет дополнительных параметров сортировки или поиска,
# применяется простой in-memory кэш. Это позволяет ускорить выдачу часто запрашиваемых данных,
# поскольку список задач пользователя может меняться не очень часто. При изменении данных (create, update, delete)
# кэш очищается. В продакшене рекомендуется использовать внешнее решение (например, Redis) для кэширования.
# -----------------------------
