import json
import os
import logging
import uuid
import hashlib
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
import bcrypt
import passlib
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session, sessionmaker, relationship

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants and paths
SERVER_DIR = r"C:\serverShiDari"
IMGS_DIR = os.path.join(SERVER_DIR, "Imgs")
CONFIG_PATH = os.path.join(SERVER_DIR, "db.json")
DEFAULT_DB_PATH = os.path.join(SERVER_DIR, "back.db")
DEFAULT_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "default.jpg")

os.makedirs(SERVER_DIR, exist_ok=True)
os.makedirs(IMGS_DIR, exist_ok=True)

# Database configuration
Base = declarative_base()
engine = create_engine(f"sqlite:///{os.path.abspath(DEFAULT_DB_PATH)}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# SQLAlchemy models
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    full_name = Column(String)
    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    parameter = Column(String, nullable=True)
    unit = Column(String)
    items = relationship("Item", back_populates="category", cascade="all, delete")

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    parameter_value = Column(String)
    unit = Column(String)
    image_id = Column(String, nullable=True)
    category = relationship("Category", back_populates="items")

# Pydantic schemas
class RoleBase(BaseModel):
    name: str

class RoleCreate(RoleBase):
    pass

class RoleResponse(RoleBase):
    id: int

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str
    full_name: str

class UserRegister(UserBase):
    password: str
    role_id: int

class UserResponse(UserBase):
    id: int
    role: Optional[str]  # Добавляем поле role

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str
    unit: str

class CategoryCreate(CategoryBase):
    parameter: Optional[str] = None

class CategoryResponse(CategoryCreate):
    id: int

    class Config:
        from_attributes = True

class ItemBase(BaseModel):
    name: str
    category_id: int
    parameter_value: str
    unit: str

class ItemCreate(ItemBase):
    image_id: Optional[str] = None

class ItemResponse(ItemCreate):
    id: int

    class Config:
        from_attributes = True

# Utility functions
def get_db_path():
    try:
        with open(CONFIG_PATH, "r") as f:
            return f"sqlite:///{os.path.abspath(json.load(f).get('db_file_path', DEFAULT_DB_PATH))}"
    except FileNotFoundError:
        logger.warning(f"Config file {CONFIG_PATH} not found. Using default path.")
        return f"sqlite:///{os.path.abspath(DEFAULT_DB_PATH)}"

def save_db_path(db_path: str):
    with open(CONFIG_PATH, "w") as f:
        json.dump({"db_file_path": db_path}, f)

def save_image(image_file: UploadFile) -> str:
    image_id = str(uuid.uuid4())
    image_path = os.path.join(IMGS_DIR, f"{image_id}.jpg")
    with open(image_path, "wb") as buffer:
        buffer.write(image_file.file.read())
    return image_id

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

# Database dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Service functions
def get_user_by_username(db: Session, username: str) -> User:
    return db.query(User).filter(User.username == username).first()

def get_role_by_id(db: Session, role_id: int) -> Role:
    return db.query(Role).filter(Role.id == role_id).first()

def get_category_by_id(db: Session, category_id: int) -> Category:
    return db.query(Category).filter(Category.id == category_id).first()

def get_item_by_id(db: Session, item_id: int) -> Item:
    return db.query(Item).filter(Item.id == item_id).first()

# API endpoints
@app.post("/register", response_model=UserResponse)
def register(user: UserRegister, db: Session = Depends(get_db)):
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    role = get_role_by_id(db, user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Role does not exist")
    
    # Используем passlib для хеширования пароля
    hashed_password = pwd_context.hash(user.password)
    
    new_user = User(
        username=user.username,
        password=hashed_password,
        full_name=user.full_name,
        role_id=user.role_id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Возвращаем пользователя с ролью
    return {
        "id": new_user.id,
        "username": new_user.username,
        "full_name": new_user.full_name,
        "role": role.name  # Добавляем имя роли в ответ
    }

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_username(db, form_data.username)
    
    if not user or not pwd_context.verify(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.username == "admin" and not os.path.exists(CONFIG_PATH):
        save_db_path(DEFAULT_DB_PATH)
        logger.info("Created default config for admin user")
    
    return {"message": "Login successful", "user_id": user.id}

# Role endpoints
@app.post("/roles", response_model=RoleResponse)
def create_role(role: RoleCreate, db: Session = Depends(get_db)):
    if db.query(Role).filter(Role.name == role.name).first():
        raise HTTPException(status_code=400, detail="Role already exists")
    
    new_role = Role(name=role.name)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role

@app.get("/roles", response_model=List[RoleResponse])
def get_roles(db: Session = Depends(get_db)):
    return db.query(Role).all()

@app.delete("/roles/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    role = db.query(Role).get(role_id)
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    db.delete(role)
    db.commit()
    return {"message": "Role deleted successfully"}

# User endpoints
@app.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for user in users:
        role = get_role_by_id(db, user.role_id)
        result.append({
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": role.name if role else None  # Добавляем имя роли в ответ
        })
    return result

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

# Category endpoints
@app.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    new_category = Category(**category.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@app.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

@app.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).get(category_id)
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}

# Item endpoints
@app.post("/items", response_model=ItemResponse)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    new_item = Item(**item.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.get("/items", response_model=List[ItemResponse])
def get_items(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Item)
    return query.filter(Item.category_id == category_id).all() if category_id else query.all()

@app.get("/items/search", response_model=List[ItemResponse])
def search_items(query: str, db: Session = Depends(get_db)):
    return db.query(Item).filter(Item.name.contains(query)).all()

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).get(item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    return {"message": "Item deleted successfully"}

# Image endpoints
@app.post("/upload_image")
def upload_image(image: UploadFile = File(...)):
    return {"image_id": save_image(image)}

@app.get("/imgs/{image_id}")
def get_image(image_id: str):
    image_path = os.path.join(IMGS_DIR, f"{image_id}.jpg")
    
    if not os.path.exists(image_path):
        if os.path.exists(DEFAULT_IMAGE_PATH):
            return FileResponse(DEFAULT_IMAGE_PATH)
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(image_path)

if __name__ == "__main__":
    import uvicorn
    Base.metadata.create_all(bind=engine)
    uvicorn.run(app, host="0.0.0.0", port=8000)