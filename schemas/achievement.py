from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AchievementBase(BaseModel):
    name: str = Field(..., max_length=50)
    description: str = Field(..., max_length=200)
    icon: str = Field(..., max_length=100)
    condition_type: str = Field(..., max_length=50)
    condition_value: int
    points: int = Field(default=10)
    is_hidden: bool = Field(default=False)


class AchievementCreate(AchievementBase):
    pass


class AchievementResponse(AchievementBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserAchievementBase(BaseModel):
    user_id: int
    achievement_id: int
    progress: int = Field(default=0)


class UserAchievementCreate(UserAchievementBase):
    pass


class UserAchievementResponse(BaseModel):
    id: int
    user_id: int
    achievement: AchievementResponse
    progress: int
    unlocked: bool
    unlocked_at: Optional[datetime]
    progress_text: str
    remaining: int

    class Config:
        from_attributes = True


class AchievementProgressResponse(BaseModel):
    achievement: AchievementResponse
    current: int
    target: int
    progress_percent: float
    is_unlocked: bool
    progress_text: str


class UserAchievementListResponse(BaseModel):
    items: List[UserAchievementResponse]
    total: int
    unlocked_count: int
    locked_count: int


class AchievementRankResponse(BaseModel):
    rank: int
    user_id: int
    username: str
    nickname: Optional[str]
    avatar: str
    level: str
    achievement_points: int
    unlocked_count: int


class PaginatedRankResponse(BaseModel):
    items: List[AchievementRankResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AchievementInitializeResponse(BaseModel):
    message: str
    added_count: int
    skipped_count: int


class AchievementLevelInfo(BaseModel):
    current_level: str
    current_points: int
    next_level: Optional[str]
    next_level_points: Optional[int]
    progress_to_next: float
