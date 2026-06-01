from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    nickname = Column(String(50))
    avatar = Column(String(255), default="/static/avatar/default.png")
    bio = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    level = Column(String(20), default="青铜")
    achievement_points = Column(Integer, default=0)
    theme = Column(String(50), default="default")
    card_style = Column(String(50), default="default")

    wishes = relationship("Wish", back_populates="user")
    replies = relationship("Reply", back_populates="user")
    likes = relationship("Like", back_populates="user")
    blessings = relationship("Blessing", back_populates="user")
    checkins = relationship("Checkin", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    wish_tree = relationship("WishTree", uselist=False, back_populates="user")
    favorites = relationship("Favorite", back_populates="user")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")


class Wish(Base):
    __tablename__ = "wishes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200))
    content = Column(Text)
    category = Column(String(20))
    visibility = Column(String(20), default="公开")
    is_anonymous = Column(Boolean, default=False)
    status = Column(String(20), default="还在等待")
    is_pinned = Column(Boolean, default=False)
    bg_color = Column(String(20))
    font_color = Column(String(20))
    font_family = Column(String(50))
    target_date = Column(Date, nullable=True)
    is_important = Column(Boolean, default=False)
    important_type = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    fulfilled_at = Column(DateTime, nullable=True)
    like_count = Column(Integer, default=0)
    blessing_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    is_fulfilled = Column(Boolean, default=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)

    user = relationship("User", back_populates="wishes")
    replies = relationship("Reply", back_populates="wish", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="wish", cascade="all, delete-orphan")
    blessings = relationship("Blessing", back_populates="wish", cascade="all, delete-orphan")
    progress_updates = relationship("WishProgress", back_populates="wish", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="wish", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="wish", cascade="all, delete-orphan")
    topic = relationship("Topic", back_populates="wishes")


class WishProgress(Base):
    __tablename__ = "wish_progress"
    id = Column(Integer, primary_key=True, index=True)
    wish_id = Column(Integer, ForeignKey("wishes.id"))
    status = Column(String(20))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    wish = relationship("Wish", back_populates="progress_updates")


class Reply(Base):
    __tablename__ = "replies"
    id = Column(Integer, primary_key=True, index=True)
    wish_id = Column(Integer, ForeignKey("wishes.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    wish = relationship("Wish", back_populates="replies")
    user = relationship("User", back_populates="replies")


class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    wish_id = Column(Integer, ForeignKey("wishes.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    wish = relationship("Wish", back_populates="likes")
    user = relationship("User", back_populates="likes")


class Blessing(Base):
    __tablename__ = "blessings"
    id = Column(Integer, primary_key=True, index=True)
    wish_id = Column(Integer, ForeignKey("wishes.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    wish = relationship("Wish", back_populates="blessings")
    user = relationship("User", back_populates="blessings")


class Topic(Base):
    __tablename__ = "topics"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    description = Column(Text)
    creator_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    wish_count = Column(Integer, default=0)
    is_hot = Column(Boolean, default=False)

    wishes = relationship("Wish", back_populates="topic")


class Checkin(Base):
    __tablename__ = "checkins"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    checkin_date = Column(Date, default=datetime.utcnow().date)
    streak = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="checkins")


class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    description = Column(String(200))
    icon = Column(String(100))
    condition_type = Column(String(50))
    condition_value = Column(Integer)
    points = Column(Integer, default=10)
    is_hidden = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(Integer, ForeignKey("achievements.id"))
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    progress = Column(Integer, default=0)

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")


class WishTree(Base):
    __tablename__ = "wish_trees"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    energy = Column(Integer, default=0)
    growth_level = Column(Integer, default=1)
    water_count = Column(Integer, default=0)
    decorations = Column(String(500), default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="wish_tree")
    waterings = relationship("Watering", back_populates="tree", cascade="all, delete-orphan")


class Watering(Base):
    __tablename__ = "waterings"
    id = Column(Integer, primary_key=True, index=True)
    tree_id = Column(Integer, ForeignKey("wish_trees.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tree = relationship("WishTree", back_populates="waterings")


class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    wish_id = Column(Integer, ForeignKey("wishes.id"))
    folder = Column(String(50), default="默认收藏夹")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    wish = relationship("Wish", back_populates="favorites")


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    wish_id = Column(Integer, ForeignKey("wishes.id"))
    reporter_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(String(200))
    description = Column(Text)
    status = Column(String(20), default="待处理")
    created_at = Column(DateTime, default=datetime.utcnow)
    handled_at = Column(DateTime, nullable=True)
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    wish = relationship("Wish", back_populates="reports")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")


class DriftBottle(Base):
    __tablename__ = "drift_bottles"
    id = Column(Integer, primary_key=True, index=True)
    wish_id = Column(Integer, ForeignKey("wishes.id"))
    picked_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    wish = relationship("Wish")


class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    wish_id = Column(Integer, ForeignKey("wishes.id"))
    remind_date = Column(Date)
    message = Column(String(200))
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class WishStory(Base):
    __tablename__ = "wish_stories"
    id = Column(Integer, primary_key=True, index=True)
    wish_id = Column(Integer, ForeignKey("wishes.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    like_count = Column(Integer, default=0)


class Friendship(Base):
    __tablename__ = "friendships"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    friend_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default="待确认")
    created_at = Column(DateTime, default=datetime.utcnow)
