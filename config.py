from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    ALGORITHM: str = "HS256"

    DATABASE_URL: str = "sqlite:///./wishwall.db"

    CATEGORIES: list = ["爱情", "事业", "学业", "健康", "家庭", "其他"]
    VISIBILITY: list = ["公开", "好友可见", "仅自己可见"]
    WISH_STATUS: list = ["正在努力中", "已经实现啦", "还在等待"]

    ACHIEVEMENT_LEVELS: dict = {
        "青铜": 0,
        "白银": 100,
        "黄金": 500,
        "钻石": 1000
    }

    class Config:
        case_sensitive = True


settings = Settings()
