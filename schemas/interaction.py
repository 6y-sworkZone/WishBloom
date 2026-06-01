from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class ReplyCreate(BaseModel):
    wish_id: int
    content: str = Field(..., min_length=1, max_length=500)
    is_anonymous: bool = False


class ReplyResponse(BaseModel):
    id: int
    wish_id: int
    user_id: Optional[int]
    content: str
    is_anonymous: bool
    created_at: datetime
    user_nickname: Optional[str] = None
    user_avatar: Optional[str] = None

    class Config:
        from_attributes = True


class LikeResponse(BaseModel):
    id: int
    wish_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LikeToggleResponse(BaseModel):
    liked: bool
    like_count: int


class BlessingCreate(BaseModel):
    wish_id: int
    message: Optional[str] = Field(None, max_length=200)


class BlessingResponse(BaseModel):
    id: int
    wish_id: int
    user_id: Optional[int]
    message: Optional[str]
    created_at: datetime
    user_nickname: Optional[str] = None

    class Config:
        from_attributes = True


class BlessingResult(BaseModel):
    success: bool
    blessing_count: int
    blessing_id: Optional[int] = None


class DriftBottleResponse(BaseModel):
    id: int
    wish_id: int
    wish_title: str
    wish_content: str
    wish_category: str
    wish_created_at: datetime
    user_nickname: Optional[str] = None
    is_anonymous: bool
    like_count: int
    blessing_count: int
    reply_count: int
    view_count: int

    class Config:
        from_attributes = True


class WishWithStats(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    category: str
    visibility: str
    is_anonymous: bool
    status: str
    bg_color: Optional[str] = None
    created_at: datetime
    like_count: int
    blessing_count: int
    reply_count: int
    view_count: int
    user_nickname: Optional[str] = None
    user_avatar: Optional[str] = None
    is_liked: bool = False
    is_blessed: bool = False

    class Config:
        from_attributes = True


class CardGenerateRequest(BaseModel):
    wish_id: int
    bg_color: Optional[str] = None


class CardGenerateResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    message: Optional[str] = None

    class Config:
        from_attributes = True


class CardResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    message: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedRepliesResponse(BaseModel):
    items: List[ReplyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True


class PaginatedLikesResponse(BaseModel):
    items: List[LikeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True


class PaginatedBlessingsResponse(BaseModel):
    items: List[BlessingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True


class WishInteractionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    category: str
    visibility: str
    is_anonymous: bool
    status: str
    bg_color: Optional[str] = None
    font_color: Optional[str] = None
    font_family: Optional[str] = None
    created_at: datetime
    like_count: int
    blessing_count: int
    reply_count: int
    view_count: int
    is_fulfilled: bool
    user_nickname: Optional[str] = None
    user_avatar: Optional[str] = None
    is_liked: bool = False
    is_blessed: bool = False

    class Config:
        from_attributes = True


class PaginatedWishesInteractionResponse(BaseModel):
    items: List[WishInteractionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True


class UserInteractionStats(BaseModel):
    sent_likes: int
    sent_blessings: int
    sent_replies: int
    received_likes: int
    received_blessings: int
    received_replies: int
    drift_bottles_thrown: int

    class Config:
        from_attributes = True
