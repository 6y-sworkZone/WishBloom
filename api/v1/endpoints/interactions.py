from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime
import random

from database import get_db
from models import Reply, Like, Blessing, DriftBottle, Wish, User
from schemas.interaction import (
    ReplyCreate,
    ReplyResponse,
    LikeResponse,
    LikeToggleResponse,
    BlessingCreate,
    BlessingResponse,
    BlessingResult,
    DriftBottleResponse,
    WishWithStats,
    CardGenerateRequest,
    CardGenerateResponse
)
from api.deps import get_current_active_user, get_current_user
from utils.card_generator import generate_wish_card

router = APIRouter(tags=["interactions"])

picked_wishes_cache = {}


@router.get("/drift-bottle", response_model=DriftBottleResponse)
async def pick_drift_bottle(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user_id = current_user.id

    cache_key = f"user_{user_id}"
    if cache_key not in picked_wishes_cache:
        picked_wishes_cache[cache_key] = set()

    picked_ids = picked_wishes_cache[cache_key]

    subquery = db.query(DriftBottle.wish_id).distinct().subquery()

    query = db.query(Wish).filter(
        Wish.visibility == "公开",
        Wish.user_id != user_id,
        Wish.id.in_(subquery),
        ~Wish.id.in_(picked_ids) if picked_ids else True
    )

    available_wishes = query.all()

    if not available_wishes:
        picked_wishes_cache[cache_key].clear()
        available_wishes = query.all()

    if not available_wishes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂时没有可拾取的漂流瓶，请稍后再试"
        )

    selected_wish = random.choice(available_wishes)
    picked_wishes_cache[cache_key].add(selected_wish.id)

    drift_bottle = db.query(DriftBottle).filter(
        DriftBottle.wish_id == selected_wish.id
    ).first()
    if drift_bottle:
        drift_bottle.picked_count += 1
        db.commit()

    selected_wish.view_count += 1
    db.commit()

    author_nickname = None
    if not selected_wish.is_anonymous:
        author = db.query(User).filter(User.id == selected_wish.user_id).first()
        if author:
            author_nickname = author.nickname or author.username

    return DriftBottleResponse(
        id=drift_bottle.id if drift_bottle else 0,
        wish_id=selected_wish.id,
        wish_title=selected_wish.title,
        wish_content=selected_wish.content,
        wish_category=selected_wish.category,
        wish_created_at=selected_wish.created_at,
        user_nickname=author_nickname,
        is_anonymous=selected_wish.is_anonymous,
        like_count=selected_wish.like_count,
        blessing_count=selected_wish.blessing_count,
        reply_count=selected_wish.reply_count,
        view_count=selected_wish.view_count
    )


@router.post("/throw-drift-bottle/{wish_id}", status_code=status.HTTP_201_CREATED)
async def throw_drift_bottle(
    wish_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
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
            detail="只能将自己的许愿投入漂流瓶"
        )
    if wish.visibility != "公开":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有公开的许愿才能投入漂流瓶"
        )

    existing = db.query(DriftBottle).filter(DriftBottle.wish_id == wish_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该许愿已经在漂流瓶中了"
        )

    drift_bottle = DriftBottle(wish_id=wish_id)
    db.add(drift_bottle)
    db.commit()
    db.refresh(drift_bottle)

    return {"message": "许愿已成功投入漂流瓶", "drift_bottle_id": drift_bottle.id}


@router.post("/replies", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED)
async def create_reply(
    reply_data: ReplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    wish = db.query(Wish).filter(Wish.id == reply_data.wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    if wish.visibility != "公开" and wish.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无法回复非公开的许愿"
        )

    reply = Reply(
        wish_id=reply_data.wish_id,
        user_id=current_user.id,
        content=reply_data.content,
        is_anonymous=reply_data.is_anonymous
    )
    db.add(reply)

    wish.reply_count += 1
    db.commit()
    db.refresh(reply)

    user_nickname = None
    user_avatar = None
    if not reply.is_anonymous:
        user_nickname = current_user.nickname or current_user.username
        user_avatar = current_user.avatar

    return ReplyResponse(
        id=reply.id,
        wish_id=reply.wish_id,
        user_id=reply.user_id if not reply.is_anonymous else None,
        content=reply.content,
        is_anonymous=reply.is_anonymous,
        created_at=reply.created_at,
        user_nickname=user_nickname,
        user_avatar=user_avatar
    )


@router.get("/replies/{wish_id}", response_model=List[ReplyResponse])
async def get_wish_replies(
    wish_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    wish = db.query(Wish).filter(Wish.id == wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    replies = db.query(Reply).filter(
        Reply.wish_id == wish_id
    ).order_by(Reply.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for reply in replies:
        user_nickname = None
        user_avatar = None
        if not reply.is_anonymous:
            user = db.query(User).filter(User.id == reply.user_id).first()
            if user:
                user_nickname = user.nickname or user.username
                user_avatar = user.avatar

        result.append(ReplyResponse(
            id=reply.id,
            wish_id=reply.wish_id,
            user_id=reply.user_id if not reply.is_anonymous else None,
            content=reply.content,
            is_anonymous=reply.is_anonymous,
            created_at=reply.created_at,
            user_nickname=user_nickname,
            user_avatar=user_avatar
        ))

    return result


@router.post("/likes/{wish_id}", response_model=LikeToggleResponse)
async def toggle_like(
    wish_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    wish = db.query(Wish).filter(Wish.id == wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    existing_like = db.query(Like).filter(
        Like.wish_id == wish_id,
        Like.user_id == current_user.id
    ).first()

    if existing_like:
        db.delete(existing_like)
        wish.like_count = max(0, wish.like_count - 1)
        db.commit()
        return LikeToggleResponse(liked=False, like_count=wish.like_count)
    else:
        like = Like(wish_id=wish_id, user_id=current_user.id)
        db.add(like)
        wish.like_count += 1
        db.commit()
        return LikeToggleResponse(liked=True, like_count=wish.like_count)


@router.get("/likes/{wish_id}", response_model=List[LikeResponse])
async def get_wish_likes(
    wish_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    likes = db.query(Like).filter(
        Like.wish_id == wish_id
    ).order_by(Like.created_at.desc()).offset(skip).limit(limit).all()
    return likes


@router.post("/blessings", response_model=BlessingResult, status_code=status.HTTP_201_CREATED)
async def create_blessing(
    blessing_data: BlessingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    wish = db.query(Wish).filter(Wish.id == blessing_data.wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )

    if wish.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能为自己的许愿祈福"
        )

    if wish.visibility != "公开":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能为公开的许愿祈福"
        )

    blessing = Blessing(
        wish_id=blessing_data.wish_id,
        user_id=current_user.id,
        message=blessing_data.message
    )
    db.add(blessing)
    wish.blessing_count += 1
    db.commit()
    db.refresh(blessing)

    return BlessingResult(
        success=True,
        blessing_count=wish.blessing_count,
        blessing_id=blessing.id
    )


@router.get("/blessings/{wish_id}", response_model=List[BlessingResponse])
async def get_wish_blessings(
    wish_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    blessings = db.query(Blessing).filter(
        Blessing.wish_id == wish_id
    ).order_by(Blessing.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for blessing in blessings:
        user = db.query(User).filter(User.id == blessing.user_id).first()
        user_nickname = user.nickname or user.username if user else None

        result.append(BlessingResponse(
            id=blessing.id,
            wish_id=blessing.wish_id,
            user_id=blessing.user_id,
            message=blessing.message,
            created_at=blessing.created_at,
            user_nickname=user_nickname
        ))

    return result


@router.get("/wishes", response_model=List[WishWithStats])
async def get_wishes_with_stats(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(lambda: None)
):
    query = db.query(Wish).filter(Wish.visibility == "公开")

    if category:
        query = query.filter(Wish.category == category)

    wishes = query.order_by(
        Wish.is_pinned.desc(),
        Wish.created_at.desc()
    ).offset(skip).limit(limit).all()

    result = []
    for wish in wishes:
        user = db.query(User).filter(User.id == wish.user_id).first()
        user_nickname = None
        user_avatar = None
        if not wish.is_anonymous and user:
            user_nickname = user.nickname or user.username
            user_avatar = user.avatar

        is_liked = False
        is_blessed = False
        if current_user:
            is_liked = db.query(Like).filter(
                Like.wish_id == wish.id,
                Like.user_id == current_user.id
            ).first() is not None
            is_blessed = db.query(Blessing).filter(
                Blessing.wish_id == wish.id,
                Blessing.user_id == current_user.id
            ).first() is not None

        result.append(WishWithStats(
            id=wish.id,
            user_id=wish.user_id,
            title=wish.title,
            content=wish.content,
            category=wish.category,
            visibility=wish.visibility,
            is_anonymous=wish.is_anonymous,
            status=wish.status,
            bg_color=wish.bg_color,
            created_at=wish.created_at,
            like_count=wish.like_count,
            blessing_count=wish.blessing_count,
            reply_count=wish.reply_count,
            view_count=wish.view_count,
            user_nickname=user_nickname,
            user_avatar=user_avatar,
            is_liked=is_liked,
            is_blessed=is_blessed
        ))

    return result


@router.get("/wishes/{wish_id}", response_model=WishWithStats)
async def get_wish_detail(
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

    if wish.visibility != "公开" and (not current_user or current_user.id != wish.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此许愿"
        )

    wish.view_count += 1
    db.commit()

    user = db.query(User).filter(User.id == wish.user_id).first()
    user_nickname = None
    user_avatar = None
    if not wish.is_anonymous and user:
        user_nickname = user.nickname or user.username
        user_avatar = user.avatar

    is_liked = False
    is_blessed = False
    if current_user:
        is_liked = db.query(Like).filter(
            Like.wish_id == wish.id,
            Like.user_id == current_user.id
        ).first() is not None
        is_blessed = db.query(Blessing).filter(
            Blessing.wish_id == wish.id,
            Blessing.user_id == current_user.id
        ).first() is not None

    return WishWithStats(
        id=wish.id,
        user_id=wish.user_id,
        title=wish.title,
        content=wish.content,
        category=wish.category,
        visibility=wish.visibility,
        is_anonymous=wish.is_anonymous,
        status=wish.status,
        bg_color=wish.bg_color,
        created_at=wish.created_at,
        like_count=wish.like_count,
        blessing_count=wish.blessing_count,
        reply_count=wish.reply_count,
        view_count=wish.view_count,
        user_nickname=user_nickname,
        user_avatar=user_avatar,
        is_liked=is_liked,
        is_blessed=is_blessed
    )


@router.post("/generate-card", response_model=CardGenerateResponse)
async def generate_wish_card_endpoint(
    request: CardGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    wish = db.query(Wish).filter(Wish.id == request.wish_id).first()
    if not wish:
        return CardGenerateResponse(
            success=False,
            message="许愿不存在"
        )

    if wish.visibility != "公开" and wish.user_id != current_user.id:
        return CardGenerateResponse(
            success=False,
            message="无权生成此许愿的分享卡片"
        )

    author_name = None
    if not wish.is_anonymous:
        user = db.query(User).filter(User.id == wish.user_id).first()
        if user:
            author_name = user.nickname or user.username

    try:
        bg_color = request.bg_color or wish.bg_color
        image_base64 = generate_wish_card(
            title=wish.title,
            content=wish.content,
            category=wish.category,
            bg_color=bg_color,
            author_name=author_name,
            created_at=wish.created_at
        )

        return CardGenerateResponse(
            success=True,
            image_base64=image_base64,
            message="卡片生成成功"
        )
    except Exception as e:
        return CardGenerateResponse(
            success=False,
            message=f"卡片生成失败: {str(e)}"
        )


@router.get("/my-interactions")
async def get_my_interactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    my_likes = db.query(Like).filter(Like.user_id == current_user.id).count()
    my_blessings = db.query(Blessing).filter(Blessing.user_id == current_user.id).count()
    my_replies = db.query(Reply).filter(Reply.user_id == current_user.id).count()

    received_likes = db.query(Like).join(Wish).filter(
        Wish.user_id == current_user.id
    ).count()
    received_blessings = db.query(Blessing).join(Wish).filter(
        Wish.user_id == current_user.id
    ).count()
    received_replies = db.query(Reply).join(Wish).filter(
        Wish.user_id == current_user.id
    ).count()

    drift_bottles_thrown = db.query(DriftBottle).join(Wish).filter(
        Wish.user_id == current_user.id
    ).count()

    return {
        "sent": {
            "likes": my_likes,
            "blessings": my_blessings,
            "replies": my_replies
        },
        "received": {
            "likes": received_likes,
            "blessings": received_blessings,
            "replies": received_replies
        },
        "drift_bottles_thrown": drift_bottles_thrown
    }
