import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models import Achievement, UserAchievement, User, Wish, Reply, Like, Blessing, Checkin, Favorite, Topic, WishTree
from config import settings


ACHIEVEMENT_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "achievements.json")


def load_achievements_from_json() -> List[Dict]:
    with open(ACHIEVEMENT_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def init_achievements(db: Session) -> Tuple[int, int]:
    achievement_data = load_achievements_from_json()
    added_count = 0
    skipped_count = 0

    for data in achievement_data:
        existing = db.query(Achievement).filter(
            Achievement.name == data["name"]
        ).first()
        if existing:
            skipped_count += 1
            continue

        db_achievement = Achievement(
            name=data["name"],
            description=data["description"],
            icon=data["icon"],
            condition_type=data["condition_type"],
            condition_value=data["condition_value"],
            points=data["points"],
            is_hidden=data["is_hidden"]
        )
        db.add(db_achievement)
        added_count += 1

    db.commit()
    return added_count, skipped_count


def get_current_value(db: Session, user_id: int, condition_type: str, **kwargs) -> int:
    if condition_type == "wish_count":
        return db.query(Wish).filter(Wish.user_id == user_id).count()

    elif condition_type == "consecutive_wish":
        return calculate_consecutive_days(db, user_id, "wish")

    elif condition_type == "fulfilled_wish":
        return db.query(Wish).filter(
            Wish.user_id == user_id,
            Wish.is_fulfilled == True
        ).count()

    elif condition_type == "received_replies":
        return db.query(Reply).join(Wish).filter(Wish.user_id == user_id).count()

    elif condition_type == "sent_replies":
        return db.query(Reply).filter(Reply.user_id == user_id).count()

    elif condition_type == "blessing_count":
        return db.query(Blessing).filter(Blessing.user_id == user_id).count()

    elif condition_type == "like_count":
        return db.query(Like).filter(Like.user_id == user_id).count()

    elif condition_type == "received_likes":
        return db.query(func.sum(Wish.like_count)).filter(Wish.user_id == user_id).scalar() or 0

    elif condition_type == "night_wish":
        wish = kwargs.get("wish")
        if wish and wish.created_at.hour <= kwargs.get("hour_threshold", 2):
            return 1
        return 0

    elif condition_type == "early_wish":
        wish = kwargs.get("wish")
        if wish and wish.created_at.hour < kwargs.get("hour_threshold", 6):
            return 1
        return 0

    elif condition_type == "favorite_count":
        return db.query(Favorite).filter(Favorite.user_id == user_id).count()

    elif condition_type == "tree_level":
        tree = db.query(WishTree).filter(WishTree.user_id == user_id).first()
        return tree.growth_level if tree else 0

    elif condition_type == "checkin_streak":
        return calculate_consecutive_days(db, user_id, "checkin")

    elif condition_type == "all_fulfilled":
        total_wishes = db.query(Wish).filter(Wish.user_id == user_id).count()
        if total_wishes == 0:
            return 0
        fulfilled_wishes = db.query(Wish).filter(
            Wish.user_id == user_id,
            Wish.is_fulfilled == True
        ).count()
        return 1 if total_wishes > 0 and total_wishes == fulfilled_wishes else 0

    elif condition_type == "view_count":
        return db.query(func.sum(Wish.view_count)).filter(Wish.user_id == user_id).scalar() or 0

    elif condition_type == "topic_count":
        return db.query(Topic).filter(Topic.creator_id == user_id).count()

    return 0


def calculate_consecutive_days(db: Session, user_id: int, source: str) -> int:
    today = datetime.utcnow().date()

    if source == "wish":
        dates = db.query(func.date(Wish.created_at)).filter(
            Wish.user_id == user_id
        ).distinct().order_by(func.date(Wish.created_at).desc()).all()
    elif source == "checkin":
        latest_checkin = db.query(Checkin).filter(
            Checkin.user_id == user_id
        ).order_by(Checkin.checkin_date.desc()).first()
        return latest_checkin.streak if latest_checkin else 0
    else:
        return 0

    date_list = [d[0] for d in dates]

    if not date_list:
        return 0

    if date_list[0] < today - timedelta(days=1):
        return 0

    streak = 0
    current_date = date_list[0]

    for d in date_list:
        if d == current_date:
            streak += 1
            current_date = current_date - timedelta(days=1)
        elif d < current_date:
            break

    return streak


def get_progress_text(condition_type: str, current: int, target: int) -> str:
    remaining = max(0, target - current)

    if current >= target:
        return "已达成"

    text_map = {
        "wish_count": f"还差 {remaining} 个愿望",
        "consecutive_wish": f"还差 {remaining} 天连续许愿",
        "fulfilled_wish": f"还差 {remaining} 个愿望实现",
        "received_replies": f"还差 {remaining} 条回信",
        "sent_replies": f"还差 {remaining} 条回信送出",
        "blessing_count": f"还差 {remaining} 次祈福",
        "like_count": f"还差 {remaining} 次点赞",
        "received_likes": f"还差 {remaining} 个点赞",
        "night_wish": "在凌晨2点许愿即可解锁",
        "early_wish": "在早上6点前许愿即可解锁",
        "favorite_count": f"还差 {remaining} 个收藏",
        "tree_level": f"许愿树还需升级 {remaining} 级",
        "checkin_streak": f"还差 {remaining} 天签到",
        "all_fulfilled": "实现所有愿望即可解锁",
        "view_count": f"还差 {remaining} 次浏览",
        "topic_count": f"还差 {remaining} 个话题"
    }

    return text_map.get(condition_type, f"还差 {remaining}")


def calculate_achievement_level(points: int) -> str:
    levels = sorted(settings.ACHIEVEMENT_LEVELS.items(), key=lambda x: x[1], reverse=True)
    for level, required_points in levels:
        if points >= required_points:
            return level
    return "青铜"


def update_user_level(db: Session, user_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        new_level = calculate_achievement_level(user.achievement_points)
        if user.level != new_level:
            user.level = new_level
            db.commit()


def check_and_unlock_achievement(
    db: Session,
    user_id: int,
    condition_type: Optional[str] = None,
    **kwargs
) -> List[Dict]:
    unlocked_achievements = []

    query = db.query(Achievement)
    if condition_type:
        query = query.filter(Achievement.condition_type == condition_type)
    achievements = query.all()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return unlocked_achievements

    for achievement in achievements:
        current_value = get_current_value(db, user_id, achievement.condition_type, **kwargs)

        existing = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.id
        ).first()

        if existing:
            existing.progress = current_value
            if existing.unlocked_at is None and current_value >= achievement.condition_value:
                existing.unlocked_at = datetime.utcnow()
                user.achievement_points += achievement.points
                unlocked_achievements.append({
                    "id": achievement.id,
                    "name": achievement.name,
                    "icon": achievement.icon,
                    "description": achievement.description,
                    "points": achievement.points
                })
        else:
            unlocked_at = datetime.utcnow() if current_value >= achievement.condition_value else None
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                progress=current_value,
                unlocked_at=unlocked_at
            )
            db.add(user_achievement)

            if unlocked_at:
                user.achievement_points += achievement.points
                unlocked_achievements.append({
                    "id": achievement.id,
                    "name": achievement.name,
                    "icon": achievement.icon,
                    "description": achievement.description,
                    "points": achievement.points
                })

    db.commit()
    update_user_level(db, user_id)

    return unlocked_achievements


def check_achievement_on_wish_create(db: Session, user_id: int, wish: Wish) -> List[Dict]:
    results = check_and_unlock_achievement(db, user_id, "wish_count")
    results += check_and_unlock_achievement(db, user_id, "consecutive_wish")

    if wish.created_at.hour <= 2:
        results += check_and_unlock_achievement(db, user_id, "night_wish", wish=wish, hour_threshold=2)
    if wish.created_at.hour < 6:
        results += check_and_unlock_achievement(db, user_id, "early_wish", wish=wish, hour_threshold=6)

    return results


def check_achievement_on_wish_fulfilled(db: Session, user_id: int) -> List[Dict]:
    results = check_and_unlock_achievement(db, user_id, "fulfilled_wish")
    results += check_and_unlock_achievement(db, user_id, "all_fulfilled")
    return results


def check_achievement_on_reply(db: Session, user_id: int, wish_user_id: int) -> List[Dict]:
    results = check_and_unlock_achievement(db, user_id, "sent_replies")
    results += check_and_unlock_achievement(db, wish_user_id, "received_replies")
    return results


def check_achievement_on_like(db: Session, user_id: int, wish_user_id: int) -> List[Dict]:
    results = check_and_unlock_achievement(db, user_id, "like_count")
    results += check_and_unlock_achievement(db, wish_user_id, "received_likes")
    return results


def check_achievement_on_blessing(db: Session, user_id: int) -> List[Dict]:
    return check_and_unlock_achievement(db, user_id, "blessing_count")


def check_achievement_on_favorite(db: Session, user_id: int) -> List[Dict]:
    return check_and_unlock_achievement(db, user_id, "favorite_count")


def check_achievement_on_checkin(db: Session, user_id: int) -> List[Dict]:
    return check_and_unlock_achievement(db, user_id, "checkin_streak")


def check_achievement_on_topic_create(db: Session, user_id: int) -> List[Dict]:
    return check_and_unlock_achievement(db, user_id, "topic_count")


def check_achievement_on_tree_upgrade(db: Session, user_id: int) -> List[Dict]:
    return check_and_unlock_achievement(db, user_id, "tree_level")


def check_achievement_on_view(db: Session, user_id: int) -> List[Dict]:
    return check_and_unlock_achievement(db, user_id, "view_count")


def get_user_achievements(db: Session, user_id: int) -> List[Dict]:
    achievements = db.query(Achievement).order_by(Achievement.points).all()
    result = []

    for achievement in achievements:
        user_achievement = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.id
        ).first()

        current = user_achievement.progress if user_achievement else 0
        unlocked = user_achievement.unlocked_at is not None if user_achievement else False
        progress_text = get_progress_text(achievement.condition_type, current, achievement.condition_value)
        remaining = max(0, achievement.condition_value - current)

        if achievement.is_hidden and not unlocked:
            continue

        result.append({
            "id": user_achievement.id if user_achievement else 0,
            "user_id": user_id,
            "achievement": achievement,
            "progress": current,
            "unlocked": unlocked,
            "unlocked_at": user_achievement.unlocked_at if user_achievement and unlocked else None,
            "progress_text": progress_text,
            "remaining": remaining
        })

    return result


def get_achievement_rank(db: Session, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
    query = db.query(User).filter(User.achievement_points > 0).order_by(
        User.achievement_points.desc(),
        User.id.asc()
    )

    total = query.count()
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()

    result = []
    for i, user in enumerate(users):
        unlocked_count = db.query(UserAchievement).filter(
            UserAchievement.user_id == user.id,
            UserAchievement.unlocked_at.isnot(None)
        ).count()

        result.append({
            "rank": offset + i + 1,
            "user_id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "level": user.level,
            "achievement_points": user.achievement_points,
            "unlocked_count": unlocked_count
        })

    return result, total


def get_user_level_info(db: Session, user_id: int) -> Dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {}

    current_points = user.achievement_points
    current_level = user.level

    levels = sorted(settings.ACHIEVEMENT_LEVELS.items(), key=lambda x: x[1])
    next_level = None
    next_level_points = None

    for level, points in levels:
        if points > current_points:
            next_level = level
            next_level_points = points
            break

    if next_level and next_level_points:
        current_level_min = settings.ACHIEVEMENT_LEVELS[current_level]
        progress_to_next = ((current_points - current_level_min) / (next_level_points - current_level_min)) * 100
    else:
        progress_to_next = 100.0

    return {
        "current_level": current_level,
        "current_points": current_points,
        "next_level": next_level,
        "next_level_points": next_level_points,
        "progress_to_next": round(progress_to_next, 2)
    }


def check_all_achievements_for_user(db: Session, user_id: int) -> List[Dict]:
    return check_and_unlock_achievement(db, user_id)
