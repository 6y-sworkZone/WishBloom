from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timedelta
import math
import json
import random

from database import get_db
from models import WishTree, Watering, Wish, User, Checkin, Friendship
from api.deps import get_current_user, get_current_active_user
from schemas.tree import (
    WishTreeResponse,
    WishLeafResponse,
    WateringCreate,
    WateringResponse,
    DecorationListResponse,
    DecorationResponse,
    ForestStatsResponse,
    CategoryStats,
    GrowthInfoResponse
)
from config import settings

router = APIRouter()

DECORATIONS = [
    {
        "id": "star_10",
        "name": "小星星",
        "description": "许愿达到10个解锁",
        "icon": "⭐",
        "condition": "wishes >= 10"
    },
    {
        "id": "star_50",
        "name": "闪亮星星",
        "description": "许愿达到50个解锁",
        "icon": "🌟",
        "condition": "wishes >= 50"
    },
    {
        "id": "moon_7",
        "name": "小月亮",
        "description": "连续许愿7天解锁",
        "icon": "🌙",
        "condition": "streak >= 7"
    },
    {
        "id": "moon_30",
        "name": "圆月亮",
        "description": "连续许愿30天解锁",
        "icon": "🌕",
        "condition": "streak >= 30"
    },
    {
        "id": "heart_5",
        "name": "小红心",
        "description": "实现5个愿望解锁",
        "icon": "❤️",
        "condition": "fulfilled >= 5"
    },
    {
        "id": "heart_20",
        "name": "双心",
        "description": "实现20个愿望解锁",
        "icon": "💖",
        "condition": "fulfilled >= 20"
    },
    {
        "id": "flower_spring",
        "name": "春天花朵",
        "description": "春季许愿10个解锁",
        "icon": "🌸",
        "condition": "spring_wishes >= 10"
    },
    {
        "id": "snowflake_winter",
        "name": "冬日雪花",
        "description": "冬季许愿10个解锁",
        "icon": "❄️",
        "condition": "winter_wishes >= 10"
    },
    {
        "id": "rainbow_all",
        "name": "彩虹",
        "description": "所有分类各有一个愿望解锁",
        "icon": "🌈",
        "condition": "all_categories"
    },
    {
        "id": "crown_100",
        "name": "皇冠",
        "description": "能量达到100解锁",
        "icon": "👑",
        "condition": "energy >= 100"
    }
]

GROWTH_LEVELS = [
    {"level": 1, "wishes": 0, "fulfilled": 0},
    {"level": 2, "wishes": 5, "fulfilled": 1},
    {"level": 3, "wishes": 10, "fulfilled": 3},
    {"level": 4, "wishes": 20, "fulfilled": 6},
    {"level": 5, "wishes": 35, "fulfilled": 10},
    {"level": 6, "wishes": 50, "fulfilled": 15},
    {"level": 7, "wishes": 75, "fulfilled": 25},
    {"level": 8, "wishes": 100, "fulfilled": 40},
    {"level": 9, "wishes": 150, "fulfilled": 60},
    {"level": 10, "wishes": 200, "fulfilled": 100}
]


def get_or_create_wish_tree(db: Session, user_id: int) -> WishTree:
    tree = db.query(WishTree).filter(WishTree.user_id == user_id).first()
    if not tree:
        tree = WishTree(
            user_id=user_id,
            energy=0,
            growth_level=1,
            water_count=0,
            decorations="[]"
        )
        db.add(tree)
        db.commit()
        db.refresh(tree)
    return tree


def calculate_growth_level(wish_count: int, fulfilled_count: int) -> int:
    for level_config in reversed(GROWTH_LEVELS):
        if wish_count >= level_config["wishes"] and fulfilled_count >= level_config["fulfilled"]:
            return level_config["level"]
    return 1


def get_growth_info(wish_count: int, fulfilled_count: int) -> dict:
    current_level = calculate_growth_level(wish_count, fulfilled_count)
    current_config = None
    next_config = None

    for i, config in enumerate(GROWTH_LEVELS):
        if config["level"] == current_level:
            current_config = config
            if i + 1 < len(GROWTH_LEVELS):
                next_config = GROWTH_LEVELS[i + 1]
            break

    if not next_config:
        return {
            "current_level": current_level,
            "next_level": current_level,
            "current_wishes": wish_count,
            "wishes_needed": current_config["wishes"],
            "current_fulfilled": fulfilled_count,
            "fulfilled_needed": current_config["fulfilled"],
            "progress_percent": 100.0
        }

    wish_progress = (wish_count - current_config["wishes"]) / max(next_config["wishes"] - current_config["wishes"], 1)
    fulfilled_progress = (fulfilled_count - current_config["fulfilled"]) / max(next_config["fulfilled"] - current_config["fulfilled"], 1)
    progress_percent = min((wish_progress + fulfilled_progress) / 2 * 100, 100)

    return {
        "current_level": current_level,
        "next_level": next_config["level"],
        "current_wishes": wish_count,
        "wishes_needed": next_config["wishes"],
        "current_fulfilled": fulfilled_count,
        "fulfilled_needed": next_config["fulfilled"],
        "progress_percent": round(progress_percent, 2)
    }


def generate_leaf_coordinates(wish_count: int, growth_level: int) -> List[tuple]:
    coordinates = []
    tree_height = 100 + growth_level * 20
    tree_width = 80 + growth_level * 15

    for i in range(wish_count):
        angle = (i / max(wish_count, 1)) * 2 * math.pi + random.uniform(-0.2, 0.2)
        radius = random.uniform(tree_width * 0.3, tree_width * 0.5)
        x = 200 + radius * math.cos(angle)
        y = 150 + random.uniform(-tree_height * 0.4, tree_height * 0.2)
        coordinates.append((round(x, 2), round(y, 2)))

    return coordinates


def is_friend(db: Session, user_id: int, current_user_id: int) -> bool:
    if user_id == current_user_id:
        return True
    friendship = db.query(Friendship).filter(
        or_(
            (Friendship.user_id == user_id) & (Friendship.friend_id == current_user_id) & (Friendship.status == "已确认"),
            (Friendship.user_id == current_user_id) & (Friendship.friend_id == user_id) & (Friendship.status == "已确认")
        )
    ).first()
    return friendship is not None


def check_decoration_unlock(db: Session, user: User, decoration: dict, wish_count: int, fulfilled_count: int, energy: int) -> bool:
    condition = decoration["condition"]

    if condition.startswith("wishes >= "):
        threshold = int(condition.split(">= ")[1])
        return wish_count >= threshold

    if condition.startswith("fulfilled >= "):
        threshold = int(condition.split(">= ")[1])
        return fulfilled_count >= threshold

    if condition.startswith("streak >= "):
        threshold = int(condition.split(">= ")[1])
        latest_checkin = db.query(Checkin).filter(Checkin.user_id == user.id).order_by(Checkin.created_at.desc()).first()
        if latest_checkin:
            return latest_checkin.streak >= threshold
        return False

    if condition.startswith("spring_wishes >= "):
        threshold = int(condition.split(">= ")[1])
        spring_wishes = db.query(Wish).filter(
            Wish.user_id == user.id,
            func.strftime('%m', Wish.created_at).in_(['03', '04', '05'])
        ).count()
        return spring_wishes >= threshold

    if condition.startswith("winter_wishes >= "):
        threshold = int(condition.split(">= ")[1])
        winter_wishes = db.query(Wish).filter(
            Wish.user_id == user.id,
            func.strftime('%m', Wish.created_at).in_(['12', '01', '02'])
        ).count()
        return winter_wishes >= threshold

    if condition == "all_categories":
        categories = set(settings.CATEGORIES)
        user_categories = set()
        user_wishes = db.query(Wish).filter(Wish.user_id == user.id).all()
        for wish in user_wishes:
            user_categories.add(wish.category)
        return categories.issubset(user_categories)

    if condition.startswith("energy >= "):
        threshold = int(condition.split(">= ")[1])
        return energy >= threshold

    return False


def update_tree_decorations(db: Session, tree: WishTree, user: User):
    wish_count = db.query(Wish).filter(Wish.user_id == user.id).count()
    fulfilled_count = db.query(Wish).filter(Wish.user_id == user.id, Wish.is_fulfilled == True).count()

    current_decorations = json.loads(tree.decorations) if tree.decorations else []
    new_decorations = []

    for decoration in DECORATIONS:
        if check_decoration_unlock(db, user, decoration, wish_count, fulfilled_count, tree.energy):
            if decoration["id"] not in current_decorations:
                current_decorations.append(decoration["id"])
            new_decorations.append(decoration["id"])

    tree.decorations = json.dumps(current_decorations, ensure_ascii=False)
    tree.growth_level = calculate_growth_level(wish_count, fulfilled_count)
    db.commit()


@router.get("/me", response_model=WishTreeResponse)
def get_my_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    tree = get_or_create_wish_tree(db, current_user.id)
    update_tree_decorations(db, tree, current_user)

    wish_count = db.query(Wish).filter(Wish.user_id == current_user.id).count()
    fulfilled_count = db.query(Wish).filter(Wish.user_id == current_user.id, Wish.is_fulfilled == True).count()

    return {
        "id": tree.id,
        "user_id": tree.user_id,
        "energy": tree.energy,
        "growth_level": tree.growth_level,
        "water_count": tree.water_count,
        "decorations": json.loads(tree.decorations) if tree.decorations else [],
        "wish_count": wish_count,
        "fulfilled_count": fulfilled_count,
        "created_at": tree.created_at,
        "updated_at": tree.updated_at
    }


@router.get("/{user_id}", response_model=WishTreeResponse)
def get_user_tree(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if not is_friend(db, user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能查看好友的许愿树"
        )

    tree = get_or_create_wish_tree(db, user_id)
    update_tree_decorations(db, tree, user)

    wish_count = db.query(Wish).filter(Wish.user_id == user_id).count()
    fulfilled_count = db.query(Wish).filter(Wish.user_id == user_id, Wish.is_fulfilled == True).count()

    return {
        "id": tree.id,
        "user_id": tree.user_id,
        "energy": tree.energy,
        "growth_level": tree.growth_level,
        "water_count": tree.water_count,
        "decorations": json.loads(tree.decorations) if tree.decorations else [],
        "wish_count": wish_count,
        "fulfilled_count": fulfilled_count,
        "created_at": tree.created_at,
        "updated_at": tree.updated_at
    }


@router.get("/me/leaves", response_model=List[WishLeafResponse])
def get_my_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    tree = get_or_create_wish_tree(db, current_user.id)
    wishes = db.query(Wish).filter(Wish.user_id == current_user.id).order_by(Wish.created_at).all()

    coordinates = generate_leaf_coordinates(len(wishes), tree.growth_level)
    leaves = []

    for i, wish in enumerate(wishes):
        x, y = coordinates[i] if i < len(coordinates) else (200.0, 150.0)
        leaves.append({
            "wish_id": wish.id,
            "category": wish.category,
            "is_fulfilled": wish.is_fulfilled,
            "x": x,
            "y": y,
            "created_at": wish.created_at
        })

    return leaves


@router.get("/{user_id}/leaves", response_model=List[WishLeafResponse])
def get_user_leaves(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if not is_friend(db, user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能查看好友的许愿树叶"
        )

    tree = get_or_create_wish_tree(db, user_id)
    wishes = db.query(Wish).filter(
        Wish.user_id == user_id,
        Wish.visibility != "仅自己可见"
    ).order_by(Wish.created_at).all()

    coordinates = generate_leaf_coordinates(len(wishes), tree.growth_level)
    leaves = []

    for i, wish in enumerate(wishes):
        x, y = coordinates[i] if i < len(coordinates) else (200.0, 150.0)
        leaves.append({
            "wish_id": wish.id,
            "category": wish.category,
            "is_fulfilled": wish.is_fulfilled,
            "x": x,
            "y": y,
            "created_at": wish.created_at
        })

    return leaves


@router.post("/{tree_id}/water", response_model=WateringResponse, status_code=status.HTTP_201_CREATED)
def water_tree(
    tree_id: int,
    watering_in: WateringCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tree = db.query(WishTree).filter(WishTree.id == tree_id).first()
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿树不存在"
        )

    if tree.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能给自己的许愿树浇水"
        )

    if not is_friend(db, tree.user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能给好友的许愿树浇水"
        )

    one_day_ago = datetime.utcnow() - timedelta(days=1)
    recent_watering = db.query(Watering).filter(
        Watering.tree_id == tree_id,
        Watering.user_id == current_user.id,
        Watering.created_at >= one_day_ago
    ).first()

    if recent_watering:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="24小时内只能给同一棵树浇水一次"
        )

    db_watering = Watering(
        tree_id=tree_id,
        user_id=current_user.id,
        message=watering_in.message
    )
    db.add(db_watering)

    tree.energy += 1
    tree.water_count += 1
    tree.updated_at = datetime.utcnow()

    user = db.query(User).filter(User.id == tree.user_id).first()
    update_tree_decorations(db, tree, user)

    db.commit()
    db.refresh(db_watering)

    return {
        "id": db_watering.id,
        "tree_id": db_watering.tree_id,
        "user_id": current_user.id,
        "username": current_user.username,
        "nickname": current_user.nickname,
        "avatar": current_user.avatar,
        "message": db_watering.message,
        "created_at": db_watering.created_at
    }


@router.get("/{tree_id}/waterings", response_model=List[WateringResponse])
def get_tree_waterings(
    tree_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tree = db.query(WishTree).filter(WishTree.id == tree_id).first()
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿树不存在"
        )

    if not is_friend(db, tree.user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能查看好友的浇水记录"
        )

    waterings = db.query(Watering).filter(Watering.tree_id == tree_id).order_by(Watering.created_at.desc()).all()

    result = []
    for watering in waterings:
        user = db.query(User).filter(User.id == watering.user_id).first()
        result.append({
            "id": watering.id,
            "tree_id": watering.tree_id,
            "user_id": watering.user_id,
            "username": user.username if user else "未知",
            "nickname": user.nickname if user else None,
            "avatar": user.avatar if user else None,
            "message": watering.message,
            "created_at": watering.created_at
        })

    return result


@router.get("/me/decorations", response_model=DecorationListResponse)
def get_my_decorations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tree = get_or_create_wish_tree(db, current_user.id)
    update_tree_decorations(db, tree, current_user)

    wish_count = db.query(Wish).filter(Wish.user_id == current_user.id).count()
    fulfilled_count = db.query(Wish).filter(Wish.user_id == current_user.id, Wish.is_fulfilled == True).count()

    unlocked_decorations = json.loads(tree.decorations) if tree.decorations else []
    unlocked = []
    locked = []

    for decoration in DECORATIONS:
        is_unlocked = decoration["id"] in unlocked_decorations
        deco_dict = {
            "id": decoration["id"],
            "name": decoration["name"],
            "description": decoration["description"],
            "icon": decoration["icon"],
            "unlocked": is_unlocked,
            "condition": decoration["condition"]
        }
        if is_unlocked:
            unlocked.append(deco_dict)
        else:
            locked.append(deco_dict)

    return {
        "unlocked": unlocked,
        "locked": locked
    }


@router.get("/forest/stats", response_model=ForestStatsResponse)
def get_forest_stats(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    total_wishes = db.query(Wish).count()
    total_fulfilled = db.query(Wish).filter(Wish.is_fulfilled == True).count()
    total_energy = db.query(func.sum(WishTree.energy)).scalar() or 0
    total_trees = db.query(WishTree).count()

    category_stats = []
    for category in settings.CATEGORIES:
        count = db.query(Wish).filter(Wish.category == category).count()
        category_stats.append({
            "category": category,
            "count": count
        })

    return {
        "total_wishes": total_wishes,
        "total_fulfilled": total_fulfilled,
        "total_energy": total_energy,
        "total_trees": total_trees,
        "category_stats": category_stats
    }


@router.get("/me/growth", response_model=GrowthInfoResponse)
def get_my_growth_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish_count = db.query(Wish).filter(Wish.user_id == current_user.id).count()
    fulfilled_count = db.query(Wish).filter(Wish.user_id == current_user.id, Wish.is_fulfilled == True).count()

    return get_growth_info(wish_count, fulfilled_count)
