from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import random
import os

from config import settings
from database import engine, Base, get_db
from models import User, Achievement, WishTree
from core.achievement import init_achievements

from api.v1.endpoints.auth import router as auth_router
from api.v1.endpoints.wishes import router as wishes_router
from api.v1.endpoints.interactions import router as interactions_router
from api.v1.endpoints.calendar import router as calendar_router
from api.v1.endpoints.tree import router as tree_router
from api.v1.endpoints.community import router as community_router
from api.v1.endpoints.achievements import router as achievements_router
from api.v1.endpoints.privacy import router as privacy_router


def get_random_port():
    used_ports = [8080, 3000, 8000, 5000, 4200, 5173, 8081, 3001]
    while True:
        port = random.randint(10000, 60000)
        if port not in used_ports:
            return port


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    db = next(get_db())
    try:
        achievement_count = db.query(Achievement).count()
        if achievement_count == 0:
            init_achievements(db)
            print("已初始化成就数据")
    except Exception as e:
        print(f"初始化成就数据失败: {e}")
    finally:
        db.close()

    yield


app = FastAPI(
    title="许愿墙 API",
    description="线上许愿墙系统 - 许下你的愿望，让梦想成真",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["认证"])
app.include_router(wishes_router, prefix=f"{settings.API_V1_STR}/wishes", tags=["许愿瓶"])
app.include_router(interactions_router, prefix=f"{settings.API_V1_STR}/interactions", tags=["许愿互动"])
app.include_router(calendar_router, prefix=f"{settings.API_V1_STR}/calendar", tags=["许愿日历"])
app.include_router(tree_router, prefix=f"{settings.API_V1_STR}/tree", tags=["许愿树"])
app.include_router(community_router, prefix=f"{settings.API_V1_STR}/community", tags=["社区"])
app.include_router(achievements_router, prefix=f"{settings.API_V1_STR}/achievements", tags=["成就系统"])
app.include_router(privacy_router, prefix=f"{settings.API_V1_STR}/privacy", tags=["隐私与安全"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/create", response_class=HTMLResponse)
async def create_wish_page(request: Request):
    return templates.TemplateResponse("create_wish.html", {"request": request})


@app.get("/wish/{wish_id}", response_class=HTMLResponse)
async def wish_detail_page(request: Request, wish_id: int):
    return templates.TemplateResponse("wish_detail.html", {"request": request, "wish_id": wish_id})


@app.get("/tree", response_class=HTMLResponse)
async def tree_page(request: Request):
    return templates.TemplateResponse("tree.html", {"request": request})


@app.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request):
    return templates.TemplateResponse("calendar.html", {"request": request})


@app.get("/community", response_class=HTMLResponse)
async def community_page(request: Request):
    return templates.TemplateResponse("community.html", {"request": request})


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "许愿墙服务运行正常"}


@app.get("/api/v1/stats")
async def get_site_stats(db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    from models import Wish
    wish_count = db.query(Wish).count()
    fulfilled_count = db.query(Wish).filter(Wish.is_fulfilled == True).count()
    tree_count = db.query(WishTree).count()
    total_energy = db.query(WishTree).all()
    total_energy_sum = sum(t.energy for t in total_energy) if total_energy else 0

    return {
        "user_count": user_count,
        "wish_count": wish_count,
        "fulfilled_count": fulfilled_count,
        "tree_count": tree_count,
        "total_energy": total_energy_sum
    }


if __name__ == "__main__":
    import uvicorn
    port = get_random_port()
    print(f"🌟 许愿墙服务启动中...")
    print(f"📱 访问地址: http://localhost:{port}")
    print(f"📚 API文档: http://localhost:{port}/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
