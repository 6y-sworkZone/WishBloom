from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, and_, or_
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import math
from collections import Counter

from database import get_db
from models import Wish, User, Topic, Checkin, WishStory, Like, Blessing, Reply
from api.deps import get_current_user
from schemas.community import (
    TopicCreate,
    TopicUpdate,
    TopicResponse,
    TopicListResponse,
    PaginatedTopicsResponse,
    PaginatedTopicWishesResponse,
    CheckinResponse,
    CheckinResult,
    CheckinHistoryResponse,
    WishStoryCreate,
    WishStoryUpdate,
    WishStoryResponse,
    WishStoryListResponse,
    PaginatedStoriesResponse,
    StoryLikeResponse,
    PartnerResponse,
    PaginatedPartnersResponse,
    RankingResponse,
    RankingUserResponse
)
from schemas.wish import WishListResponse, PaginatedWishesResponse

router = APIRouter()


def get_user_categories(db: Session, user_id: int) -> List[str]:
    wishes = db.query(Wish).filter(
        Wish.user_id == user_id,
        Wish.visibility == "公开"
    ).all()
    return [wish.category for wish in wishes]


@router.get("/square", response_model=PaginatedWishesResponse)
def get_square_wishes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("latest", pattern="^(latest|hottest|most_blessings)$"),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    query = db.query(Wish).filter(Wish.visibility == "公开")

    if category and category in ["爱情", "事业", "学业", "健康", "家庭", "其他"]:
        query = query.filter(Wish.category == category)

    if sort_by == "latest":
        query = query.order_by(desc(Wish.is_pinned), desc(Wish.created_at))
    elif sort_by == "hottest":
        query = query.order_by(
            desc(Wish.is_pinned),
            desc(Wish.like_count + Wish.blessing_count + Wish.reply_count),
            desc(Wish.created_at)
        )
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


@router.post("/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    topic_in: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_topic = Topic(
        title=topic_in.title,
        description=topic_in.description,
        creator_id=current_user.id
    )
    db.add(db_topic)
    db.commit()
    db.refresh(db_topic)
    return db_topic


@router.get("/topics", response_model=PaginatedTopicsResponse)
def get_topics(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("latest", pattern="^(latest|hottest|most_wishes)$"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    query = db.query(Topic)

    if sort_by == "latest":
        query = query.order_by(desc(Topic.is_hot), desc(Topic.created_at))
    elif sort_by == "hottest":
        query = query.order_by(desc(Topic.is_hot), desc(Topic.wish_count), desc(Topic.created_at))
    elif sort_by == "most_wishes":
        query = query.order_by(desc(Topic.wish_count), desc(Topic.created_at))

    total = query.count()
    total_pages = math.ceil(total / page_size)
    offset = (page - 1) * page_size
    topics = query.offset(offset).limit(page_size).all()

    return {
        "items": topics,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/topics/{topic_id}", response_model=TopicResponse)
def get_topic_detail(
    topic_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="话题不存在"
        )
    return topic


@router.get("/topics/{topic_id}/wishes", response_model=PaginatedTopicWishesResponse)
def get_topic_wishes(
    topic_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("latest", pattern="^(latest|hottest|most_blessings)$"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="话题不存在"
        )

    query = db.query(Wish).filter(
        Wish.topic_id == topic_id,
        Wish.visibility == "公开"
    )

    if sort_by == "latest":
        query = query.order_by(desc(Wish.created_at))
    elif sort_by == "hottest":
        query = query.order_by(
            desc(Wish.like_count + Wish.blessing_count + Wish.reply_count),
            desc(Wish.created_at)
        )
    elif sort_by == "most_blessings":
        query = query.order_by(desc(Wish.blessing_count), desc(Wish.created_at))

    total = query.count()
    total_pages = math.ceil(total / page_size)
    offset = (page - 1) * page_size
    wishes = query.offset(offset).limit(page_size).all()

    return {
        "topic": topic,
        "items": wishes,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.post("/checkin", response_model=CheckinResult)
def daily_checkin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = datetime.utcnow().date()

    existing_checkin = db.query(Checkin).filter(
        Checkin.user_id == current_user.id,
        Checkin.checkin_date == today
    ).first()

    if existing_checkin:
        return {
            "success": False,
            "streak": existing_checkin.streak,
            "checkin_date": today,
            "message": "今天已经打卡过啦~"
        }

    yesterday = today - timedelta(days=1)
    last_checkin = db.query(Checkin).filter(
        Checkin.user_id == current_user.id
    ).order_by(desc(Checkin.checkin_date)).first()

    streak = 1
    if last_checkin and last_checkin.checkin_date == yesterday:
        streak = last_checkin.streak + 1

    db_checkin = Checkin(
        user_id=current_user.id,
        checkin_date=today,
        streak=streak
    )
    db.add(db_checkin)
    db.commit()
    db.refresh(db_checkin)

    return {
        "success": True,
        "streak": streak,
        "checkin_date": today,
        "message": f"打卡成功！已连续打卡{streak}天"
    }


@router.get("/checkin/history", response_model=CheckinHistoryResponse)
def get_checkin_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    checkins = db.query(Checkin).filter(
        Checkin.user_id == current_user.id
    ).order_by(desc(Checkin.checkin_date)).all()

    current_streak = 0
    today = datetime.utcnow().date()

    if checkins:
        latest_checkin = checkins[0]
        if latest_checkin.checkin_date == today or latest_checkin.checkin_date == today - timedelta(days=1):
            current_streak = latest_checkin.streak

    return {
        "items": checkins,
        "current_streak": current_streak,
        "total_checkins": len(checkins)
    }


@router.get("/checkin/status")
def get_checkin_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = datetime.utcnow().date()
    checked_in = db.query(Checkin).filter(
        Checkin.user_id == current_user.id,
        Checkin.checkin_date == today
    ).first() is not None

    last_checkin = db.query(Checkin).filter(
        Checkin.user_id == current_user.id
    ).order_by(desc(Checkin.checkin_date)).first()

    current_streak = last_checkin.streak if last_checkin else 0

    return {
        "checked_in_today": checked_in,
        "current_streak": current_streak
    }


@router.get("/partners", response_model=PaginatedPartnersResponse)
def find_partners(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    my_categories = get_user_categories(db, current_user.id)

    if not my_categories:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0
        }

    category_counter = Counter(my_categories)
    top_categories = [cat for cat, _ in category_counter.most_common(3)]

    subquery = db.query(Wish.user_id).filter(
        Wish.visibility == "公开",
        Wish.category.in_(top_categories)
    ).subquery()

    query = db.query(User).filter(
        User.id != current_user.id,
        User.id.in_(subquery)
    )

    total = query.count()
    total_pages = math.ceil(total / page_size)
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()

    partners = []
    for user in users:
        user_categories = get_user_categories(db, user.id)
        common_cats = list(set(my_categories) & set(user_categories))
        partners.append({
            "id": user.id,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "bio": user.bio,
            "level": user.level,
            "match_count": len(common_cats),
            "common_categories": common_cats
        })

    partners.sort(key=lambda x: x["match_count"], reverse=True)

    return {
        "items": partners,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.post("/stories", response_model=WishStoryResponse, status_code=status.HTTP_201_CREATED)
def create_story(
    story_in: WishStoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish = db.query(Wish).filter(
        Wish.id == story_in.wish_id,
        Wish.user_id == current_user.id
    ).first()

    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在或无权分享"
        )

    if not wish.is_fulfilled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能分享已实现的愿望"
        )

    existing_story = db.query(WishStory).filter(
        WishStory.wish_id == story_in.wish_id
    ).first()

    if existing_story:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该愿望已经分享过故事了"
        )

    db_story = WishStory(
        wish_id=story_in.wish_id,
        user_id=current_user.id,
        title=story_in.title,
        content=story_in.content
    )
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    return db_story


@router.get("/stories", response_model=PaginatedStoriesResponse)
def get_stories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("latest", pattern="^(latest|hottest)$"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    query = db.query(WishStory)

    if sort_by == "latest":
        query = query.order_by(desc(WishStory.created_at))
    elif sort_by == "hottest":
        query = query.order_by(desc(WishStory.like_count), desc(WishStory.created_at))

    total = query.count()
    total_pages = math.ceil(total / page_size)
    offset = (page - 1) * page_size
    stories = query.offset(offset).limit(page_size).all()

    return {
        "items": stories,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/stories/{story_id}", response_model=WishStoryResponse)
def get_story_detail(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    story = db.query(WishStory).filter(WishStory.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="故事不存在"
        )

    is_liked = False
    if current_user:
        liked = db.query(Like).filter(
            Like.user_id == current_user.id,
            Like.wish_id == story.wish_id
        ).first()
        is_liked = liked is not None

    result = {c.name: getattr(story, c.name) for c in story.__table__.columns}
    result["is_liked"] = is_liked
    return result


@router.post("/stories/{story_id}/like", response_model=StoryLikeResponse)
def like_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    story = db.query(WishStory).filter(WishStory.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="故事不存在"
        )

    existing_like = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.wish_id == story.wish_id
    ).first()

    if existing_like:
        db.delete(existing_like)
        story.like_count = max(0, story.like_count - 1)
        liked = False
    else:
        new_like = Like(
            wish_id=story.wish_id,
            user_id=current_user.id
        )
        db.add(new_like)
        story.like_count += 1
        liked = True

    db.commit()
    db.refresh(story)

    return {
        "liked": liked,
        "like_count": story.like_count
    }


@router.get("/ranking", response_model=RankingResponse)
def get_ranking(
    rank_type: str = Query("most_wishes", pattern="^(most_wishes|most_blessings|most_fulfilled|most_replies)$"),
    top_n: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    if rank_type == "most_wishes":
        results = db.query(
            Wish.user_id,
            func.count(Wish.id).label("count")
        ).filter(
            Wish.visibility == "公开"
        ).group_by(Wish.user_id).order_by(desc("count")).limit(top_n).all()
    elif rank_type == "most_blessings":
        results = db.query(
            Wish.user_id,
            func.sum(Wish.blessing_count).label("count")
        ).filter(
            Wish.visibility == "公开"
        ).group_by(Wish.user_id).order_by(desc("count")).limit(top_n).all()
    elif rank_type == "most_fulfilled":
        results = db.query(
            Wish.user_id,
            func.count(Wish.id).label("count")
        ).filter(
            Wish.visibility == "公开",
            Wish.is_fulfilled == True
        ).group_by(Wish.user_id).order_by(desc("count")).limit(top_n).all()
    elif rank_type == "most_replies":
        results = db.query(
            Wish.user_id,
            func.sum(Wish.reply_count).label("count")
        ).filter(
            Wish.visibility == "公开"
        ).group_by(Wish.user_id).order_by(desc("count")).limit(top_n).all()

    ranking_items = []
    for idx, (user_id, count) in enumerate(results):
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            ranking_items.append({
                "id": user.id,
                "nickname": user.nickname,
                "avatar": user.avatar,
                "level": user.level,
                "count": count,
                "rank": idx + 1
            })

    type_names = {
        "most_wishes": "许愿最多榜",
        "most_blessings": "祈福最多榜",
        "most_fulfilled": "实现最多榜",
        "most_replies": "回信最多榜"
    }

    return {
        "type": type_names.get(rank_type, "排行榜"),
        "items": ranking_items
    }
