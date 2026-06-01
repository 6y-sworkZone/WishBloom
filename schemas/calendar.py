from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date, datetime


class CalendarWishItem(BaseModel):
    id: int
    title: str
    category: str
    is_fulfilled: bool
    is_important: bool
    important_type: Optional[str]
    target_date: Optional[date]
    created_at: datetime
    fulfilled_at: Optional[datetime]

    class Config:
        from_attributes = True


class CalendarDayData(BaseModel):
    date: date
    wishes: List[CalendarWishItem]
    fulfilled_count: int
    total_count: int
    has_important: bool


class CalendarViewResponse(BaseModel):
    year: int
    month: int
    days: Dict[str, CalendarDayData]
    total_wishes: int
    total_fulfilled: int


class ImportantDayMarker(BaseModel):
    type: str
    label: str
    icon: Optional[str] = None


class CountdownResponse(BaseModel):
    wish_id: int
    wish_title: str
    target_date: date
    days_left: int
    message: str


class ReminderCreate(BaseModel):
    wish_id: int
    remind_date: date
    message: str = Field(..., max_length=200)


class ReminderResponse(BaseModel):
    id: int
    wish_id: int
    wish_title: str
    remind_date: date
    message: str
    is_sent: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReminderListResponse(BaseModel):
    items: List[ReminderResponse]
    total: int


class YearlyReviewResponse(BaseModel):
    year: int
    total_wishes: int
    fulfilled_wishes: int
    fulfillment_rate: float
    message: str


class CategoryStats(BaseModel):
    category: str
    total_count: int
    fulfilled_count: int
    fulfillment_rate: float


class FulfillmentStatsResponse(BaseModel):
    year: Optional[int]
    overall: CategoryStats
    by_category: List[CategoryStats]
