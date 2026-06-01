from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
import calendar

from database import get_db
from models import Wish, Reminder, User
from api.deps import get_current_user
from schemas.calendar import (
    CalendarViewResponse,
    CalendarDayData,
    CalendarWishItem,
    CountdownResponse,
    ReminderCreate,
    ReminderResponse,
    ReminderListResponse,
    YearlyReviewResponse,
    FulfillmentStatsResponse,
    CategoryStats,
    ImportantDayMarker
)
from config import settings

router = APIRouter()


IMPORTANT_DAY_TYPES = {
    "生日": {"label": "🎂 生日许愿", "icon": "🎂"},
    "新年": {"label": "🎉 新年许愿", "icon": "🎉"},
    "考试前": {"label": "📚 考试祈福", "icon": "📚"},
    "其他": {"label": "✨ 重要日子", "icon": "✨"}
}


def get_important_day_marker(important_type: Optional[str]) -> Optional[ImportantDayMarker]:
    if important_type and important_type in IMPORTANT_DAY_TYPES:
        info = IMPORTANT_DAY_TYPES[important_type]
        return ImportantDayMarker(type=important_type, label=info["label"], icon=info["icon"])
    return None


@router.get("/calendar", response_model=CalendarViewResponse)
def get_calendar_view(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _, num_days = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days)

    wishes = db.query(Wish).filter(
        Wish.user_id == current_user.id,
        or_(
            and_(
                func.date(Wish.created_at) >= start_date,
                func.date(Wish.created_at) <= end_date
            ),
            and_(
                func.date(Wish.fulfilled_at) >= start_date,
                func.date(Wish.fulfilled_at) <= end_date
            )
        )
    ).all()

    days = {}
    total_wishes = 0
    total_fulfilled = 0

    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        date_str = current_date.isoformat()

        day_wishes = []
        for wish in wishes:
            wish_created = wish.created_at.date() if wish.created_at else None
            wish_fulfilled = wish.fulfilled_at.date() if wish.fulfilled_at else None

            if wish_created == current_date or wish_fulfilled == current_date:
                day_wishes.append(CalendarWishItem(
                    id=wish.id,
                    title=wish.title,
                    category=wish.category,
                    is_fulfilled=wish.is_fulfilled,
                    is_important=wish.is_important,
                    important_type=wish.important_type,
                    target_date=wish.target_date,
                    created_at=wish.created_at,
                    fulfilled_at=wish.fulfilled_at
                ))

        fulfilled_count = sum(1 for w in day_wishes if w.is_fulfilled)
        total_count = len(day_wishes)
        has_important = any(w.is_important for w in day_wishes)

        total_wishes += total_count
        total_fulfilled += fulfilled_count

        days[date_str] = CalendarDayData(
            date=current_date,
            wishes=day_wishes,
            fulfilled_count=fulfilled_count,
            total_count=total_count,
            has_important=has_important
        )

    return CalendarViewResponse(
        year=year,
        month=month,
        days=days,
        total_wishes=total_wishes,
        total_fulfilled=total_fulfilled
    )


@router.get("/countdown/{wish_id}", response_model=CountdownResponse)
def get_wish_countdown(
    wish_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish = db.query(Wish).filter(
        Wish.id == wish_id,
        Wish.user_id == current_user.id
    ).first()

    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    if not wish.target_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该许愿没有设置目标日期"
        )

    today = date.today()
    days_left = (wish.target_date - today).days

    if days_left > 0:
        message = f"距离「{wish.title}」还有 {days_left} 天"
    elif days_left == 0:
        message = f"今天就是「{wish.title}」的目标日期！"
    else:
        message = f"「{wish.title}」的目标日期已过去 {-days_left} 天"

    return CountdownResponse(
        wish_id=wish.id,
        wish_title=wish.title,
        target_date=wish.target_date,
        days_left=days_left,
        message=message
    )


@router.get("/countdowns", response_model=List[CountdownResponse])
def get_all_countdowns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wishes = db.query(Wish).filter(
        Wish.user_id == current_user.id,
        Wish.target_date.isnot(None),
        Wish.is_fulfilled == False
    ).order_by(Wish.target_date).all()

    results = []
    today = date.today()

    for wish in wishes:
        days_left = (wish.target_date - today).days

        if days_left > 0:
            message = f"距离「{wish.title}」还有 {days_left} 天"
        elif days_left == 0:
            message = f"今天就是「{wish.title}」的目标日期！"
        else:
            message = f"「{wish.title}」的目标日期已过去 {-days_left} 天"

        results.append(CountdownResponse(
            wish_id=wish.id,
            wish_title=wish.title,
            target_date=wish.target_date,
            days_left=days_left,
            message=message
        ))

    return results


@router.post("/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(
    reminder_in: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish = db.query(Wish).filter(
        Wish.id == reminder_in.wish_id,
        Wish.user_id == current_user.id
    ).first()

    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    db_reminder = Reminder(
        user_id=current_user.id,
        wish_id=reminder_in.wish_id,
        remind_date=reminder_in.remind_date,
        message=reminder_in.message
    )

    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)

    return ReminderResponse(
        id=db_reminder.id,
        wish_id=db_reminder.wish_id,
        wish_title=wish.title,
        remind_date=db_reminder.remind_date,
        message=db_reminder.message,
        is_sent=db_reminder.is_sent,
        created_at=db_reminder.created_at
    )


@router.get("/reminders", response_model=ReminderListResponse)
def get_reminders(
    include_sent: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Reminder, Wish).join(
        Wish, Reminder.wish_id == Wish.id
    ).filter(
        Reminder.user_id == current_user.id
    )

    if not include_sent:
        query = query.filter(Reminder.is_sent == False)

    results = query.order_by(Reminder.remind_date).all()

    items = []
    for reminder, wish in results:
        items.append(ReminderResponse(
            id=reminder.id,
            wish_id=reminder.wish_id,
            wish_title=wish.title,
            remind_date=reminder.remind_date,
            message=reminder.message,
            is_sent=reminder.is_sent,
            created_at=reminder.created_at
        ))

    return ReminderListResponse(
        items=items,
        total=len(items)
    )


@router.get("/reminders/upcoming", response_model=ReminderListResponse)
def get_upcoming_reminders(
    days_ahead: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    end_date = today + timedelta(days=days_ahead)

    results = db.query(Reminder, Wish).join(
        Wish, Reminder.wish_id == Wish.id
    ).filter(
        Reminder.user_id == current_user.id,
        Reminder.is_sent == False,
        Reminder.remind_date >= today,
        Reminder.remind_date <= end_date
    ).order_by(Reminder.remind_date).all()

    items = []
    for reminder, wish in results:
        items.append(ReminderResponse(
            id=reminder.id,
            wish_id=reminder.wish_id,
            wish_title=wish.title,
            remind_date=reminder.remind_date,
            message=reminder.message,
            is_sent=reminder.is_sent,
            created_at=reminder.created_at
        ))

    return ReminderListResponse(
        items=items,
        total=len(items)
    )


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reminder = db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id
    ).first()

    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提醒不存在"
        )

    db.delete(reminder)
    db.commit()
    return None


@router.get("/review/{year}", response_model=YearlyReviewResponse)
def get_yearly_review(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    total_wishes = db.query(Wish).filter(
        Wish.user_id == current_user.id,
        func.date(Wish.created_at) >= start_date,
        func.date(Wish.created_at) <= end_date
    ).count()

    fulfilled_wishes = db.query(Wish).filter(
        Wish.user_id == current_user.id,
        func.date(Wish.created_at) >= start_date,
        func.date(Wish.created_at) <= end_date,
        Wish.is_fulfilled == True
    ).count()

    fulfillment_rate = (fulfilled_wishes / total_wishes * 100) if total_wishes > 0 else 0.0

    if year == date.today().year:
        message = f"今年你许了 {total_wishes} 个愿，实现了 {fulfilled_wishes} 个，实现率 {fulfillment_rate:.1f}%"
    else:
        message = f"{year}年你许了 {total_wishes} 个愿，实现了 {fulfilled_wishes} 个，实现率 {fulfillment_rate:.1f}%"

    return YearlyReviewResponse(
        year=year,
        total_wishes=total_wishes,
        fulfilled_wishes=fulfilled_wishes,
        fulfillment_rate=round(fulfillment_rate, 1),
        message=message
    )


@router.get("/stats/fulfillment", response_model=FulfillmentStatsResponse)
def get_fulfillment_stats(
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Wish).filter(Wish.user_id == current_user.id)

    if year:
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        query = query.filter(
            func.date(Wish.created_at) >= start_date,
            func.date(Wish.created_at) <= end_date
        )

    all_wishes = query.all()

    total_count = len(all_wishes)
    total_fulfilled = sum(1 for w in all_wishes if w.is_fulfilled)
    overall_rate = (total_fulfilled / total_count * 100) if total_count > 0 else 0.0

    overall = CategoryStats(
        category="全部",
        total_count=total_count,
        fulfilled_count=total_fulfilled,
        fulfillment_rate=round(overall_rate, 1)
    )

    by_category = []
    for category in settings.CATEGORIES:
        category_wishes = [w for w in all_wishes if w.category == category]
        cat_total = len(category_wishes)
        cat_fulfilled = sum(1 for w in category_wishes if w.is_fulfilled)
        cat_rate = (cat_fulfilled / cat_total * 100) if cat_total > 0 else 0.0

        by_category.append(CategoryStats(
            category=category,
            total_count=cat_total,
            fulfilled_count=cat_fulfilled,
            fulfillment_rate=round(cat_rate, 1)
        ))

    return FulfillmentStatsResponse(
        year=year,
        overall=overall,
        by_category=by_category
    )


@router.get("/important-days/markers", response_model=List[ImportantDayMarker])
def get_important_day_markers():
    markers = []
    for type_key, info in IMPORTANT_DAY_TYPES.items():
        markers.append(ImportantDayMarker(
            type=type_key,
            label=info["label"],
            icon=info["icon"]
        ))
    return markers
