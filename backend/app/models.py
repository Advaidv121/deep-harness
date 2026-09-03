from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Text, Float, DateTime, Integer, LargeBinary, Index, Computed
)
try:
    from pgvector.sqlalchemy import Vector  # type: ignore
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    Vector = None  # type: ignore

from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Fact(Base):
    __tablename__ = "facts"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    category = Column(String(32), nullable=False, index=True)
    content = Column(Text, nullable=False)
    salience_score = Column(Float, nullable=False, default=1.0)
    valid_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    invalidated_at = Column(DateTime, nullable=True)
    linked_to = Column(String(36), nullable=True)
    # Keep LargeBinary for offline portability; when pgvector is available the column
    # can store VECTOR(1024) — we keep LargeBinary as fallback so tests without pgvector pass.
    # In Postgres we also add a generated tsvector column via migration in database.py.
    embedding = Column(LargeBinary, nullable=True)
    # content_tsv is added via ALTER TABLE in init_db (not declared here to avoid DDL mismatch)

    __table_args__ = (
        Index("ix_facts_active_user", "user_id", "valid_until"),
    )

class Tombstone(Base):
    __tablename__ = "tombstones"

    id = Column(String(36), primary_key=True)
    fact_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    reason = Column(String(255), nullable=False)
    superseded_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class Turn(Base):
    __tablename__ = "turns"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    turn_index = Column(Integer, nullable=False)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_turns_session_turn", "session_id", "turn_index"),
    )

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    role = Column(String(256), nullable=False, default="Software Engineer")
    location = Column(String(256), nullable=False, default="Remote")
    avatar_bg = Column(String(64), nullable=False, default="from-amber-500 to-orange-600")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ChatThread(Base):
    __tablename__ = "chat_threads"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=False, default="New Conversation")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_chat_threads_user_updated", "user_id", "updated_at"),
    )
