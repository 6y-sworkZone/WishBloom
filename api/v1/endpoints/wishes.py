from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, desc, func
from sqlalchemy.orm import Session
from datetime import datetime
import random
import math

from database import get_db
from models import Wish, WishProgress, User, Friendship
from api.deps import get_current_user
from schemas.wish import (
    WishCreate,
    WishUpdate,
    WishProgressUpdate,
    WishResponse,
    WishListResponse,
    PaginatedWishesResponse,
    WishProgressResponse
)
from config import settings

router = APIRouter()

BG_COLORS = [
    "#FFB6C1", "#87CEEB", "#98FB98", "#DDA0DD", "#F0E68C",
    "#E6E6FA", "#FFDAB9", "#B0E0E6", "#FFE4E1", "#D3D3D3",
    "#FAFAD2", "#E0FFFF", "#FFEFD5", "#FFE4B5", "#EE82EE"
]

FONT_COLORS = [
    "#333333", "#1A1A2E", "#16213E", "#0F3460", "#2C3E50",
    "#34495E", "#1C2833", "#17202A", "#181818", "#212121"
]

FONT_FAMILIES = [
    "Microsoft YaHei", "SimHei", "KaiTi", "SimSun", "STSong",
    "Arial", "Georgia", "Times New Roman", "Verdana", "Courier New"
]


def generate_random_style() -> dict:
    return {
        "bg_color": random.choice(BG_COLORS),
        "font_color": random.choice(FONT_COLORS),
        "font_family": random.choice(FONT_FAMILIES)
    }


def is_friend(db: Session, user_id: int, current_user_id: int) -> bool:
    friendship = db.query(Friendship).filter(
        or_(
            (Friendship.user_id == user_id) & (Friendship.friend_id == current_user_id) & (Friendship.status == "已确认"),
            (Friendship.user_id == current_user_id) & (Friendship.friend_id == user_id) & (Friendship.status == "已确认")
        )
    ).first()
    return friendship is not None


def can_view_wish(wish: Wish, current_user: Optional[User]) -> bool:
    if wish.visibility == "公开":
        return True
    if current_user is None:
        return False
    if wish.user_id == current_user.id:
        return True
    if wish.visibility == "好友可见":
        return is_friend(wish.user_id, current_user.id)
    return False


@router.post("", response_model=WishResponse, status_code=status.HTTP_201_CREATED)
def create_wish(
    wish_in: WishCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    style = generate_random_style()
    db_wish = Wish(
        user_id=current_user.id,
        title=wish_in.title,
        content=wish_in.content,
        category=wish_in.category,
        visibility=wish_in.visibility,
        is_anonymous=wish_in.is_anonymous,
        bg_color=style["bg_color"],
        font_color=style["font_color"],
        font_family=style["font_family"],
        target_date=wish_in.target_date,
        is_important=wish_in.is_important,
        important_type=wish_in.important_type
    )
    db.add(db_wish)
    db.commit()
    db.refresh(db_wish)
    return db_wish


@router.get("", response_model=PaginatedWishesResponse)
def get_wishes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("latest", pattern="^(latest|hottest|most_blessings)$"),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    query = db.query(Wish).filter(Wish.visibility == "公开")

    if category and category in settings.CATEGORIES:
        query = query.filter(Wish.category == category)

    if sort_by == "latest":
        query = query.order_by(desc(Wish.is_pinned), desc(Wish.created_at))
    elif sort_by == "hottest":
        query = query.order_by(desc(Wish.is_pinned), desc(Wish.like_count + Wish.blessing_count + Wish.reply_count), desc(Wish.created_at))
    elif sort_by == "most_blessings":
        query = query.order_by(desc(Wish.is_pinned), desc(Wish.blessing_count), desc(Wish.created_at))

    total = query.count()
    total_pages = math.ceil(total / page_size)
    offset = (page - 1) * page_size
    wishes = query.offset(offset).limit(page_size).all()

    return {
        "items": wishes,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/search", response_model=PaginatedWishesResponse)
def search_wishes(
    keyword: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    query = db.query(Wish).filter(Wish.visibility == "公开")

    if category and category in settings.CATEGORIES:
        query = query.filter(Wish.category == category)

    search_pattern = f"%{keyword}%"
    query = query.filter(
        or_(
            Wish.title.like(search_pattern),
            Wish.content.like(search_pattern),
            Wish.category.like(search_pattern)
        )
    )

    query = query.order_by(desc(Wish.is_pinned), desc(Wish.created_at))

    total = query.count()
    total_pages = math.ceil(total / page_size)
    offset = (page - 1) * page_size
    wishes = query.offset(offset).limit(page_size).all()

    return {
        "items": wishes,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/my", response_model=PaginatedWishesResponse)
def get_my_wishes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Wish).filter(Wish.user_id == current_user.id)
    query = query.order_by(desc(Wish.is_pinned), desc(Wish.created_at))

    total = query.count()
    total_pages = math.ceil(total / page_size)
    offset = (page - 1) * page_size
    wishes = query.offset(offset).limit(page_size).all()

    return {
        "items": wishes,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/{wish_id}", response_model=WishResponse)
def get_wish_detail(
    wish_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    wish = db.query(Wish).filter(Wish.id == wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    if not can_view_wish(wish, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看该许愿"
        )

    wish.view_count += 1
    db.commit()
    db.refresh(wish)

    return wish


@router.put("/{wish_id}", response_model=WishResponse)
def update_wish(
    wish_id: int,
    wish_in: WishUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish = db.query(Wish).filter(Wish.id == wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    if wish.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能编辑自己的许愿"
        )

    update_data = wish_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(wish, field, value)

    db.commit()
    db.refresh(wish)
    return wish


@router.delete("/{wish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wish(
    wish_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish = db.query(Wish).filter(Wish.id == wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    if wish.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能删除自己的许愿"
        )

    db.delete(wish)
    db.commit()
    return None


@router.post("/{wish_id}/pin", response_model=WishResponse)
def pin_wish(
    wish_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish = db.query(Wish).filter(Wish.id == wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    if wish.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能置顶自己的许愿"
        )

    wish.is_pinned = not wish.is_pinned
    db.commit()
    db.refresh(wish)
    return wish


@router.post("/{wish_id}/progress", response_model=WishProgressResponse, status_code=status.HTTP_201_CREATED)
def update_wish_progress(
    wish_id: int,
    progress_in: WishProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish = db.query(Wish).filter(Wish.id == wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    if wish.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能更新自己的许愿进度"
        )

    db_progress = WishProgress(
        wish_id=wish_id,
        status=progress_in.status,
        content=progress_in.content
    )
    db.add(db_progress)

    wish.status = progress_in.status
    if progress_in.status == "已经实现啦":
        wish.is_fulfilled = True
        wish.fulfilled_at = datetime.utcnow()
    else:
        wish.is_fulfilled = False
        wish.fulfilled_at = None

    db.commit()
    db.refresh(db_progress)
    return db_progress


@router.get("/{wish_id}/progress", response_model=List[WishProgressResponse])
def get_wish_progress(
    wish_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    wish = db.query(Wish).filter(Wish.id == wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    if not can_view_wish(wish, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看该许愿进度"
        )

    progress_list = db.query(WishProgress).filter(
        WishProgress.wish_id == wish_id
    ).order_by(desc(WishProgress.created_at)).all()

    return progress_list
