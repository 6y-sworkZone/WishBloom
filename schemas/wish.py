from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from config import settings

class WishCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = Field(..., max_length=20)
    visibility: str = Field(default="公开", max_length=20)
    is_anonymous: bool = Field(default=False)
    target_date: Optional[date] = None
    is_important: bool = Field(default=False)
    important_type: Optional[str] = Field(default=None, max_length=20)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in settings.CATEGORIES:
            raise ValueError(f"分类必须是以下之一: {settings.CATEGORIES}")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        if v not in settings.VISIBILITY:
            raise ValueError(f"可见性必须是以下之一: {settings.VISIBILITY}")
        return v

    @field_validator("important_type")
    @classmethod
    def validate_important_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["生日", "新年", "考试前", "其他"]:
            raise ValueError("重要日子类型必须是以下之一: 生日, 新年, 考试前, 其他")
        return v

class WishUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1)
    category: Optional[str] = Field(default=None, max_length=20)
    visibility: Optional[str] = Field(default=None, max_length=20)
    is_anonymous: Optional[bool] = None
    target_date: Optional[date] = None
    is_important: Optional[bool] = None
    important_type: Optional[str] = Field(default=None, max_length=20)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in settings.CATEGORIES:
            raise ValueError(f"分类必须是以下之一: {settings.CATEGORIES}")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in settings.VISIBILITY:
            raise ValueError(f"可见性必须是以下之一: {settings.VISIBILITY}")
        return v

    @field_validator("important_type")
    @classmethod
    def validate_important_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["生日", "新年", "考试前", "其他"]:
            raise ValueError('重要日子类型必须是以下之一: 生日, 新年, 考试前, 其他')
        return v

class WishProgressUpdate(BaseModel):
    status: str = Field(..., max_length=20)
    content: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in settings.WISH_STATUS:
            raise ValueError(f"状态必须是以下之一: {settings.WISH_STATUS}")
        return v

class WishProgressResponse(BaseModel):
    id: int
    wish_id: int
    status: str
    content: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class WishUserResponse(BaseModel):
    id: int
    username: Optional[str]
    nickname: Optional[str]
    avatar: Optional[str]

    class Config:
        from_attributes = True

class WishResponse(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    category: str
    visibility: str
    is_anonymous: bool
    status: str
    is_pinned: bool
    bg_color: str
    font_color: str
    font_family: str
    target_date: Optional[date]
    is_important: bool
    important_type: Optional[str]
    created_at: datetime
    updated_at: datetime
    like_count: int
    blessing_count: int
    reply_count: int
    view_count: int
    is_fulfilled: bool
    user: Optional[WishUserResponse]
    progress_updates: List[WishProgressResponse]

    class Config:
        from_attributes = True

class WishListResponse(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    category: str
    visibility: str
    is_anonymous: bool
    status: str
    is_pinned: bool
    bg_color: str
    font_color: str
    font_family: str
    target_date: Optional[date]
    is_important: bool
    important_type: Optional[str]
    created_at: datetime
    like_count: int
    blessing_count: int
    reply_count: int
    view_count: int
    is_fulfilled: bool
    user: Optional[WishUserResponse]

    class Config:
        from_attributes = True

class PaginatedWishesResponse(BaseModel):
    items: List[WishListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True

class PaginatedProgressResponse(BaseModel):
    items: List[WishProgressResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True
