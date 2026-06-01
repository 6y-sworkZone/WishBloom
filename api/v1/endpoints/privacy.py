from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from datetime import datetime
import json

from database import get_db
from models import Wish, User, Report, Favorite, WishProgress, Reply, Like, Blessing
from api.deps import get_current_user
from schemas.privacy import (
    VisibilityUpdate,
    ReportCreate,
    ReportResponse,
    FavoriteCreate,
    FavoriteUpdate,
    FavoriteResponse,
    FavoriteListResponse,
    FavoriteFolderResponse,
    FavoriteWishResponse,
    UserExportData,
    WishExportData,
    AccountDeleteRequest,
    AnonymousWishResponse,
    ThemeUpdate,
    ThemeResponse
)
from config import settings

router = APIRouter()


def mask_anonymous_user(wish: Wish, current_user: Optional[User]) -> Wish:
    if wish.is_anonymous:
        if current_user is None or wish.user_id != current_user.id:
            wish.user_id = None
            if wish.user:
                wish.user.nickname = "匿名用户"
                wish.user.avatar = "/static/avatar/default.png"
                wish.user.username = None
    return wish


def can_view_wish(wish: Wish, current_user: Optional[User], db: Session) -> bool:
    if wish.visibility == "公开":
        return True
    if current_user is None:
        return False
    if wish.user_id == current_user.id:
        return True
    if wish.visibility == "好友可见":
        from models import Friendship
        from sqlalchemy import or_
        friendship = db.query(Friendship).filter(
            or_(
                (Friendship.user_id == wish.user_id) & (Friendship.friend_id == current_user.id) & (Friendship.status == "已确认"),
                (Friendship.user_id == current_user.id) & (Friendship.friend_id == wish.user_id) & (Friendship.status == "已确认")
            )
        ).first()
        return friendship is not None
    return False


@router.put("/visibility", response_model=dict)
def update_wish_visibility(
    visibility_in: VisibilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish = db.query(Wish).filter(Wish.id == visibility_in.wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )
    if wish.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能修改自己的许愿可见性"
        )
    wish.visibility = visibility_in.visibility
    db.commit()
    db.refresh(wish)
    return {"message": "可见性更新成功", "visibility": wish.visibility}


@router.post("/report", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    report_in: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish = db.query(Wish).filter(Wish.id == report_in.wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )
    if wish.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能举报自己的许愿"
        )
    existing_report = db.query(Report).filter(
        Report.wish_id == report_in.wish_id,
        Report.reporter_id == current_user.id
    ).first()
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经举报过该许愿"
        )
    db_report = Report(
        wish_id=report_in.wish_id,
        reporter_id=current_user.id,
        reason=report_in.reason,
        description=report_in.description,
        status="待处理"
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


@router.post("/favorite", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
def create_favorite(
    favorite_in: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wish = db.query(Wish).filter(Wish.id == favorite_in.wish_id).first()
    if not wish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="许愿不存在"
        )
    if wish.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能收藏自己的许愿"
        )
    if not can_view_wish(wish, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权收藏该许愿"
        )
    existing_favorite = db.query(Favorite).filter(
        Favorite.wish_id == favorite_in.wish_id,
        Favorite.user_id == current_user.id
    ).first()
    if existing_favorite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经收藏过该许愿"
        )
    db_favorite = Favorite(
        user_id=current_user.id,
        wish_id=favorite_in.wish_id,
        folder=favorite_in.folder
    )
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite


@router.delete("/favorite/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(
    favorite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    favorite = db.query(Favorite).filter(Favorite.id == favorite_id).first()
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在"
        )
    if favorite.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能取消自己的收藏"
        )
    db.delete(favorite)
    db.commit()
    return None


@router.put("/favorite/{favorite_id}", response_model=FavoriteResponse)
def update_favorite_folder(
    favorite_id: int,
    favorite_in: FavoriteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    favorite = db.query(Favorite).filter(Favorite.id == favorite_id).first()
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在"
        )
    if favorite.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能修改自己的收藏"
        )
    favorite.folder = favorite_in.folder
    db.commit()
    db.refresh(favorite)
    return favorite


@router.get("/favorites", response_model=FavoriteListResponse)
def get_favorites(
    folder: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Favorite).filter(Favorite.user_id == current_user.id)
    if folder:
        query = query.filter(Favorite.folder == folder)
    total = query.count()
    offset = (page - 1) * page_size
    favorites = query.order_by(desc(Favorite.created_at)).offset(offset).limit(page_size).all()
    for fav in favorites:
        if fav.wish:
            fav.wish = mask_anonymous_user(fav.wish, current_user)
    folder_stats = db.query(
        Favorite.folder,
        func.count(Favorite.id).label("count")
    ).filter(
        Favorite.user_id == current_user.id
    ).group_by(Favorite.folder).all()
    folders = [FavoriteFolderResponse(folder=f, count=c) for f, c in folder_stats]
    return {
        "folders": folders,
        "favorites": favorites,
        "total": total
    }


@router.get("/export")
def export_user_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    wishes = db.query(Wish).filter(Wish.user_id == current_user.id).all()
    wish_data_list = []
    for wish in wishes:
        progress_updates = db.query(WishProgress).filter(WishProgress.wish_id == wish.id).all()
        replies = db.query(Reply).filter(Reply.wish_id == wish.id).all()
        likes = db.query(Like).filter(Like.wish_id == wish.id).all()
        blessings = db.query(Blessing).filter(Blessing.wish_id == wish.id).all()
        wish_data = WishExportData(
            id=wish.id,
            title=wish.title,
            content=wish.content,
            category=wish.category,
            visibility=wish.visibility,
            is_anonymous=wish.is_anonymous,
            status=wish.status,
            target_date=wish.target_date,
            is_important=wish.is_important,
            important_type=wish.important_type,
            created_at=wish.created_at,
            updated_at=wish.updated_at,
            fulfilled_at=wish.fulfilled_at,
            like_count=wish.like_count,
            blessing_count=wish.blessing_count,
            reply_count=wish.reply_count,
            view_count=wish.view_count,
            is_fulfilled=wish.is_fulfilled,
            progress_updates=[
                {
                    "id": p.id,
                    "status": p.status,
                    "content": p.content,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                } for p in progress_updates
            ],
            replies=[
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "content": r.content,
                    "is_anonymous": r.is_anonymous,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                } for r in replies
            ],
            likes=[
                {
                    "id": l.id,
                    "user_id": l.user_id,
                    "created_at": l.created_at.isoformat() if l.created_at else None
                } for l in likes
            ],
            blessings=[
                {
                    "id": b.id,
                    "user_id": b.user_id,
                    "message": b.message,
                    "created_at": b.created_at.isoformat() if b.created_at else None
                } for b in blessings
            ]
        )
        wish_data_list.append(wish_data)
    export_data = UserExportData(
        user_id=current_user.id,
        username=current_user.username,
        nickname=current_user.nickname,
        email=current_user.email,
        bio=current_user.bio,
        created_at=current_user.created_at,
        total_wishes=len(wish_data_list),
        wishes=wish_data_list
    )
    filename = f"wishbloom_export_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    content = json.loads(export_data.model_dump_json())
    return JSONResponse(
        content=content,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/json"
        }
    )


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    delete_request: AccountDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.query(Report).filter(Report.reporter_id == current_user.id).delete()
    db.query(Favorite).filter(Favorite.user_id == current_user.id).delete()
    db.query(Like).filter(Like.user_id == current_user.id).delete()
    db.query(Blessing).filter(Blessing.user_id == current_user.id).delete()
    db.query(Reply).filter(Reply.user_id == current_user.id).delete()
    db.query(WishProgress).filter(
        WishProgress.wish_id.in_(
            db.query(Wish.id).filter(Wish.user_id == current_user.id)
        )
    ).delete(synchronize_session=False)
    db.query(Report).filter(
        Report.wish_id.in_(
            db.query(Wish.id).filter(Wish.user_id == current_user.id)
        )
    ).delete(synchronize_session=False)
    db.query(Favorite).filter(
        Favorite.wish_id.in_(
            db.query(Wish.id).filter(Wish.user_id == current_user.id)
        )
    ).delete(synchronize_session=False)
    db.query(Like).filter(
        Like.wish_id.in_(
            db.query(Wish.id).filter(Wish.user_id == current_user.id)
        )
    ).delete(synchronize_session=False)
    db.query(Blessing).filter(
        Blessing.wish_id.in_(
            db.query(Wish.id).filter(Wish.user_id == current_user.id)
        )
    ).delete(synchronize_session=False)
    db.query(Reply).filter(
        Reply.wish_id.in_(
            db.query(Wish.id).filter(Wish.user_id == current_user.id)
        )
    ).delete(synchronize_session=False)
    db.query(Wish).filter(Wish.user_id == current_user.id).delete()
    db.delete(current_user)
    db.commit()
    return None


@router.get("/wishes/anonymous", response_model=List[AnonymousWishResponse])
def get_anonymous_wishes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    query = db.query(Wish).filter(
        Wish.visibility == "公开",
        Wish.is_anonymous == True
    )
    total = query.count()
    offset = (page - 1) * page_size
    wishes = query.order_by(desc(Wish.created_at)).offset(offset).limit(page_size).all()
    result = []
    for wish in wishes:
        wish = mask_anonymous_user(wish, current_user)
        user_nickname = None
        user_avatar = None
        if wish.user:
            user_nickname = wish.user.nickname
            user_avatar = wish.user.avatar
        result.append(AnonymousWishResponse(
            id=wish.id,
            title=wish.title,
            content=wish.content,
            category=wish.category,
            visibility=wish.visibility,
            is_anonymous=wish.is_anonymous,
            status=wish.status,
            created_at=wish.created_at,
            like_count=wish.like_count,
            blessing_count=wish.blessing_count,
            reply_count=wish.reply_count,
            view_count=wish.view_count,
            user_id=wish.user_id,
            nickname=user_nickname,
            avatar=user_avatar
        ))
    return result


@router.put("/theme", response_model=ThemeResponse)
def update_user_theme(
    theme_in: ThemeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.theme = theme_in.theme
    current_user.card_style = theme_in.card_style
    db.commit()
    db.refresh(current_user)
    return ThemeResponse(
        theme=current_user.theme,
        card_style=current_user.card_style
    )


@router.get("/theme", response_model=ThemeResponse)
def get_user_theme(
    current_user: User = Depends(get_current_user)
):
    return ThemeResponse(
        theme=current_user.theme,
        card_style=current_user.card_style
    )
