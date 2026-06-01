from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from schemas.wish import WishListResponse


class TopicCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)


class TopicUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1)


class TopicCreatorResponse(BaseModel):
    id: int
    nickname: Optional[str]
    avatar: Optional[str]

    class Config:
        from_attributes = True


class TopicResponse(BaseModel):
    id: int
    title: str
    description: str
    creator_id: int
    created_at: datetime
    wish_count: int
    is_hot: bool
    creator: Optional[TopicCreatorResponse]

    class Config:
        from_attributes = True


class TopicListResponse(BaseModel):
    id: int
    title: str
    description: str
    creator_id: int
    created_at: datetime
    wish_count: int
    is_hot: bool
    creator: Optional[TopicCreatorResponse]

    class Config:
        from_attributes = True


class PaginatedTopicsResponse(BaseModel):
    items: List[TopicListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedTopicWishesResponse(BaseModel):
    topic: TopicResponse
    items: List[WishListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CheckinResponse(BaseModel):
    id: int
    user_id: int
    checkin_date: date
    streak: int
    created_at: datetime

    class Config:
        from_attributes = True


class CheckinResult(BaseModel):
    success: bool
    streak: int
    checkin_date: date
    message: str


class CheckinHistoryResponse(BaseModel):
    items: List[CheckinResponse]
    current_streak: int
    total_checkins: int


class WishStoryCreate(BaseModel):
    wish_id: int
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)


class WishStoryUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1)


class WishStoryAuthorResponse(BaseModel):
    id: int
    nickname: Optional[str]
    avatar: Optional[str]

    class Config:
        from_attributes = True


class WishStoryResponse(BaseModel):
    id: int
    wish_id: int
    user_id: int
    title: str
    content: str
    created_at: datetime
    like_count: int
    author: Optional[WishStoryAuthorResponse]
    is_liked: bool = False

    class Config:
        from_attributes = True


class WishStoryListResponse(BaseModel):
    id: int
    wish_id: int
    user_id: int
    title: str
    content: str
    created_at: datetime
    like_count: int
    author: Optional[WishStoryAuthorResponse]

    class Config:
        from_attributes = True


class PaginatedStoriesResponse(BaseModel):
    items: List[WishStoryListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True


class StoryLikeResponse(BaseModel):
    liked: bool
    like_count: int

    class Config:
        from_attributes = True


class PartnerResponse(BaseModel):
    id: int
    nickname: Optional[str]
    avatar: Optional[str]
    bio: Optional[str]
    level: Optional[str]
    match_count: int
    common_categories: List[str]

    class Config:
        from_attributes = True


class PaginatedPartnersResponse(BaseModel):
    items: List[PartnerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RankingUserResponse(BaseModel):
    id: int
    nickname: Optional[str]
    avatar: Optional[str]
    level: Optional[str]
    count: int
    rank: int

    class Config:
        from_attributes = True


class RankingResponse(BaseModel):
    type: str
    items: List[RankingUserResponse]

    class Config:
        from_attributes = True
