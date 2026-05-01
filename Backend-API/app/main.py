from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from jose import JWTError, jwt
import redis.asyncio as redis
import aioredis
import json
import time
import os

# Config
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Redis client
redis_client: Optional[redis.Redis] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    yield
    await redis_client.close()

app = FastAPI(
    title="Backend API",
    description="Production backend with auth, RBAC, CRUD, caching & rate limiting",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# In-memory DB (replace with PostgreSQL in production)
users_db = {}
items_db = {}
item_counter = 0

# Roles
class Role:
    USER = "user"
    ADMIN = "admin"

# Models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=6)
    role: str = Role.USER

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: str

class UserInDB(UserOut):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class ItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    tags: List[str] = []

class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class ItemOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    tags: List[str]
    owner_id: int
    created_at: str
    updated_at: str

class PaginatedItems(BaseModel):
    items: List[ItemOut]
    total: int
    page: int
    page_size: int
    pages: int

# Helpers
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = users_db.get(int(user_id))
    if user is None:
        raise credentials_exception
    return UserInDB(**user)

async def require_admin(current_user: UserInDB = Depends(get_current_user)):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Rate limiting middleware
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if redis_client is None:
        return await call_next(request)

    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"

    current = await redis_client.get(key)
    if current is None:
        await redis_client.setex(key, 60, 1)
    elif int(current) >= 100:  # 100 requests per minute
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."}
        )
    else:
        await redis_client.incr(key)

    return await call_next(request)

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": str(request.url)}
    )

# Auth Routes
@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(user: UserCreate):
    if any(u["username"] == user.username for u in users_db.values()):
        raise HTTPException(status_code=400, detail="Username already registered")

    user_id = len(users_db) + 1
    user_data = {
        "id": user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "hashed_password": hash_password(user.password),
        "created_at": datetime.utcnow().isoformat()
    }
    users_db[user_id] = user_data
    return UserOut(**{k: v for k, v in user_data.items() if k != "hashed_password"})

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = next((u for u in users_db.values() if u["username"] == form_data.username), None)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access = create_token(
        {"sub": str(user["id"]), "role": user["role"]},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh = create_token(
        {"sub": str(user["id"]), "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return Token(access_token=access, refresh_token=refresh)

@app.post("/auth/refresh", response_model=Token)
def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        user = users_db.get(int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access = create_token(
        {"sub": str(user["id"]), "role": user["role"]},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh = create_token(
        {"sub": str(user["id"]), "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return Token(access_token=access, refresh_token=new_refresh)

# User Routes
@app.get("/users/me", response_model=UserOut)
def get_me(current: UserInDB = Depends(get_current_user)):
    return UserOut(**{k: v for k, v in current.dict().items() if k != "hashed_password"})

@app.get("/users", response_model=List[UserOut])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    role: Optional[str] = None,
    current: UserInDB = Depends(require_admin)
):
    all_users = list(users_db.values())
    if role:
        all_users = [u for u in all_users if u["role"] == role]

    total = len(all_users)
    start = (page - 1) * page_size
    end = start + page_size
    pages = (total + page_size - 1) // page_size

    return [UserOut(**{k: v for k, v in u.items() if k != "hashed_password"}) 
            for u in all_users[start:end]]

# Item Routes (CRUD with caching)
@app.post("/items", response_model=ItemOut, status_code=201)
async def create_item(item: ItemCreate, current: UserInDB = Depends(get_current_user)):
    global item_counter
    item_counter += 1
    now = datetime.utcnow().isoformat()
    item_data = {
        "id": item_counter,
        "title": item.title,
        "description": item.description,
        "tags": item.tags,
        "owner_id": current.id,
        "created_at": now,
        "updated_at": now
    }
    items_db[item_counter] = item_data

    # Invalidate cache
    if redis_client:
        await redis_client.delete(f"items:user:{current.id}")

    return ItemOut(**item_data)

@app.get("/items", response_model=PaginatedItems)
async def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current: UserInDB = Depends(get_current_user)
):
    cache_key = f"items:{current.id}:{page}:{page_size}:{search}:{tag}:{sort_by}:{sort_order}"

    # Try cache
    if redis_client:
        cached = await redis_client.get(cache_key)
        if cached:
            return PaginatedItems(**json.loads(cached))

    all_items = [v for v in items_db.values() if v["owner_id"] == current.id or current.role == Role.ADMIN]

    if search:
        all_items = [i for i in all_items if search.lower() in i["title"].lower()]
    if tag:
        all_items = [i for i in all_items if tag in i.get("tags", [])]

    reverse = sort_order == "desc"
    all_items.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)

    total = len(all_items)
    pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size

    result = PaginatedItems(
        items=[ItemOut(**i) for i in all_items[start:end]],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )

    # Cache for 5 minutes
    if redis_client:
        await redis_client.setex(cache_key, 300, result.json())

    return result

@app.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, current: UserInDB = Depends(get_current_user)):
    item = items_db.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["owner_id"] != current.id and current.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    return ItemOut(**item)

@app.put("/items/{item_id}", response_model=ItemOut)
async def update_item(
    item_id: int,
    update: ItemUpdate,
    current: UserInDB = Depends(get_current_user)
):
    item = items_db.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["owner_id"] != current.id and current.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    if update.title is not None:
        item["title"] = update.title
    if update.description is not None:
        item["description"] = update.description
    if update.tags is not None:
        item["tags"] = update.tags
    item["updated_at"] = datetime.utcnow().isoformat()

    # Invalidate cache
    if redis_client:
        pattern = f"items:{current.id}:*"
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)

    return ItemOut(**item)

@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int, current: UserInDB = Depends(get_current_user)):
    item = items_db.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["owner_id"] != current.id and current.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    del items_db[item_id]

    if redis_client:
        pattern = f"items:{current.id}:*"
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)

    return None

# Admin stats
@app.get("/admin/stats")
def admin_stats(current: UserInDB = Depends(require_admin)):
    return {
        "total_users": len(users_db),
        "total_items": len(items_db),
        "timestamp": datetime.utcnow().isoformat()
    }
