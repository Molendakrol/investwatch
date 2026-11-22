from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import DATABASE_URL


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


is_sqlite = DATABASE_URL.startswith("sqlite")
if is_sqlite:
    from pathlib import Path

    Path(DATABASE_URL.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    pool_pre_ping=True,
    json_serializer=lambda o: json.dumps(o, ensure_ascii=False),
)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(conn, _):  # WAL = concurrent readers while the worker ingests
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    kind: Mapped[str] = mapped_column(String(20))  # html | social | meta_ads | knf_register
    name: Mapped[str] = mapped_column(String(300))
    group: Mapped[str] = mapped_column(String(40), default="web")  # register | demo | web | social
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(20))
    last_error: Mapped[str | None] = mapped_column(Text)
    items_found: Mapped[int] = mapped_column(Integer, default=0)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    url: Mapped[str] = mapped_column(String(1000))
    kind: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued|running|done|failed
    trigger: Mapped[str] = mapped_column(String(20), default="manual")  # manual|schedule|startup
    priority: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    worker: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    platform: Mapped[str] = mapped_column(String(60), default="www")
    title: Mapped[str] = mapped_column(String(500), default="")
    author: Mapped[str | None] = mapped_column(String(300))
    site_name: Mapped[str | None] = mapped_column(String(300))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    simhash: Mapped[str] = mapped_column(String(24))
    raw_key: Mapped[str | None] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text, default="")
    excerpt: Mapped[str] = mapped_column(Text, default="")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    scan_count: Mapped[int] = mapped_column(Integer, default=1)
    change_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_of: Mapped[int | None] = mapped_column(Integer)
    findings: Mapped[list["Finding"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("document_id", "module"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    module: Mapped[str] = mapped_column(String(4), index=True)  # m1 | m2 | m3
    score: Mapped[float] = mapped_column(Float, index=True)
    level: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="new")  # new|in_review|escalated|closed|false_positive
    summary: Mapped[str] = mapped_column(Text, default="")
    entity: Mapped[str | None] = mapped_column(String(300))
    firm: Mapped[str | None] = mapped_column(String(300))
    firm_category: Mapped[str | None] = mapped_column(String(40))
    signals: Mapped[list[Any]] = mapped_column(default=list)
    rules: Mapped[list[Any]] = mapped_column(default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    document: Mapped[Document] = relationship(back_populates="findings")


class GoldLabel(Base):
    """Ground truth for the labelled test corpus (used only by calibration)."""

    __tablename__ = "gold_labels"
    __table_args__ = (UniqueConstraint("url", "module"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1000), index=True)
    module: Mapped[str] = mapped_column(String(4))
    label: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str] = mapped_column(Text, default="")


class RegisterEntity(Base):
    __tablename__ = "register_entities"
    __table_args__ = (UniqueConstraint("name", "category"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(400))
    category: Mapped[str] = mapped_column(String(40))
    address: Mapped[str] = mapped_column(Text, default="")
    license_date: Mapped[str] = mapped_column(String(40), default="")
    scope: Mapped[str] = mapped_column(String(300), default="")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(default=dict)


class Activity(Base):
    __tablename__ = "activity"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    kind: Mapped[str] = mapped_column(String(20))  # sweep | flag | system | analyst
    message: Mapped[str] = mapped_column(Text)


def init_db() -> None:
    Base.metadata.create_all(engine)
