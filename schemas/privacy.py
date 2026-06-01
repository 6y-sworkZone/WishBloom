from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from config import settings


class VisibilityUpdate(BaseModel):
    wish_id: int
    visibility: str = Field(..., max_length=20)

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        if v not in settings.VISIBILITY:
            raise ValueError(f"可见性必须是以下之一: {settings.VISIBILITY}")
        return v


class ReportCreate(BaseModel):
    wish_id: int
    reason: str = Field(..., max_length=200)
    description: Optional[str] = Field(default=None)


class ReportResponse(BaseModel):
    id: int
    wish_id: int
    reporter_id: int
    reason: str
    description: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FavoriteCreate(BaseModel):
    wish_id: int
    folder: str = Field(default="默认收藏夹", max_length=50)


class FavoriteUpdate(BaseModel):
    folder: str = Field(..., max_length=50)


class FavoriteWishResponse(BaseModel):
    id: int
    user_id: Optional[int]
    title: str
    content: str
    category: str
    visibility: str
    is_anonymous: bool
    status: str
    created_at: datetime
    like_count: int
    blessing_count: int
    reply_count: int
    nickname: Optional[str]
    avatar: Optional[str]


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    wish_id: int
    folder: str
    created_at: datetime
    wish: Optional[FavoriteWishResponse]

    class Config:
        from_attributes = True


class FavoriteFolderResponse(BaseModel):
    folder: str
    count: int


class FavoriteListResponse(BaseModel):
    folders: List[FavoriteFolderResponse]
    favorites: List[FavoriteResponse]
    total: int


class WishExportData(BaseModel):
    id: int
    title: str
    content: str
    category: str
    visibility: str
    is_anonymous: bool
    status: str
    target_date: Optional[date]
    is_important: bool
    important_type: Optional[str]
    created_at: datetime
    updated_at: datetime
    fulfilled_at: Optional[datetime]
    like_count: int
    blessing_count: int
    reply_count: int
    view_count: int
    is_fulfilled: bool
    progress_updates: List[Dict[str, Any]]
    replies: List[Dict[str, Any]]
    likes: List[Dict[str, Any]]
    blessings: List[Dict[str, Any]]


class UserExportData(BaseModel):
    user_id: int
    username: str
    nickname: str
    email: str
    bio: str
    created_at: datetime
    total_wishes: int
    wishes: List[WishExportData]


class AccountDeleteRequest(BaseModel):
    confirmation: str = Field(..., min_length=4, max_length=4)

    @field_validator("confirmation")
    @classmethod
    def validate_confirmation(cls, v: str) -> str:
        if v != "删除":
            raise ValueError('确认删除请输入"删除"')
        return v


class AnonymousWishResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    visibility: str
    is_anonymous: bool
    status: str
    created_at: datetime
    like_count: int
    blessing_count: int
    reply_count: int
    view_count: int
    user_id: Optional[int]
    nickname: Optional[str]
    avatar: Optional[str]

    class Config:
        from_attributes = True


class ThemeUpdate(BaseModel):
    theme: str = Field(..., max_length=50)
    card_style: str = Field(..., max_length=50)


class ThemeResponse(BaseModel):
    theme: str
    card_style: str

    class Config:
        from_attributes = True


class PaginatedFavoritesResponse(BaseModel):
    items: List[FavoriteResponse]
    folders: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True


class FavoriteFolderStats(BaseModel):
    folder: str
    count: int

    class Config:
        from_attributes = True


class ExportResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    download_url: Optional[str] = None

    class Config:
        from_attributes = True
