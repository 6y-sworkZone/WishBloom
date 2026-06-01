from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
import math

from database import get_db
from models import User
from api.deps import get_current_user
from core.achievement import (
    init_achievements,
    get_user_achievements,
    get_achievement_rank,
    get_user_level_info,
    check_all_achievements_for_user
)
from schemas.achievement import (
    AchievementResponse,
    UserAchievementResponse,
    UserAchievementListResponse,
    PaginatedRankResponse,
    AchievementInitializeResponse,
    AchievementLevelInfo
)

router = APIRouter()


@router.post("/init", response_model=AchievementInitializeResponse)
def initialize_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以初始化成就数据"
        )

    added_count, skipped_count = init_achievements(db)

    return {
        "message": "成就数据初始化完成",
        "added_count": added_count,
        "skipped_count": skipped_count
    }


@router.get("/me", response_model=UserAchievementListResponse)
def get_my_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    achievements = get_user_achievements(db, current_user.id)

    unlocked_count = sum(1 for a in achievements if a["unlocked"])
    locked_count = len(achievements) - unlocked_count

    return {
        "items": achievements,
        "total": len(achievements),
        "unlocked_count": unlocked_count,
        "locked_count": locked_count
    }


@router.get("/user/{user_id}", response_model=UserAchievementListResponse)
def get_user_achievements_list(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    achievements = get_user_achievements(db, user_id)

    unlocked_count = sum(1 for a in achievements if a["unlocked"])
    locked_count = len(achievements) - unlocked_count

    return {
        "items": achievements,
        "total": len(achievements),
        "unlocked_count": unlocked_count,
        "locked_count": locked_count
    }


@router.get("/level/me", response_model=AchievementLevelInfo)
def get_my_level_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_user_level_info(db, current_user.id)


@router.get("/level/{user_id}", response_model=AchievementLevelInfo)
def get_user_level(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    level_info = get_user_level_info(db, user_id)
    if not level_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return level_info


@router.get("/rank", response_model=PaginatedRankResponse)
def get_achievement_ranking(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    ranks, total = get_achievement_rank(db, page, page_size)
    total_pages = math.ceil(total / page_size)

    return {
        "items": ranks,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.post("/check-all")
def check_all_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    unlocked = check_all_achievements_for_user(db, current_user.id)

    return {
        "message": "成就检查完成",
        "newly_unlocked": unlocked,
        "unlocked_count": len(unlocked)
    }
