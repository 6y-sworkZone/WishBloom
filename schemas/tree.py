from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WishLeafResponse(BaseModel):
    wish_id: int
    category: str
    is_fulfilled: bool
    x: float
    y: float
    created_at: datetime

    class Config:
        from_attributes = True


class DecorationResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    unlocked: bool
    unlocked_at: Optional[datetime] = None
    condition: str

    class Config:
        from_attributes = True


class DecorationListResponse(BaseModel):
    unlocked: List[DecorationResponse]
    locked: List[DecorationResponse]


class WishTreeResponse(BaseModel):
    id: int
    user_id: int
    energy: int
    growth_level: int
    water_count: int
    decorations: List[str]
    wish_count: int
    fulfilled_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WateringCreate(BaseModel):
    message: Optional[str] = Field(default=None, max_length=200)


class WateringResponse(BaseModel):
    id: int
    tree_id: int
    user_id: int
    username: str
    nickname: Optional[str]
    avatar: Optional[str]
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryStats(BaseModel):
    category: str
    count: int


class ForestStatsResponse(BaseModel):
    total_wishes: int
    total_fulfilled: int
    total_energy: int
    total_trees: int
    category_stats: List[CategoryStats]


class GrowthInfoResponse(BaseModel):
    current_level: int
    next_level: int
    current_wishes: int
    wishes_needed: int
    current_fulfilled: int
    fulfilled_needed: int
    progress_percent: float
