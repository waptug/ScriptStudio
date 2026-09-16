"""Durable state. JSON documents are replaced, never mutated in place."""
import os
import time
from contextlib import contextmanager
from sqlalchemy import create_engine, String, Integer, Float, JSON, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .schemas import uid

engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:////tmp/scriptstudio.sqlite'), pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    original_script: Mapped[str] = mapped_column(Text)
    script: Mapped[str] = mapped_column(Text)
    script_revision: Mapped[int] = mapped_column(Integer, default=1)
    settings: Mapped[dict] = mapped_column(JSON)
    storyboard: Mapped[dict] = mapped_column(JSON, default=lambda: {'scenes': []})
    timeline: Mapped[dict] = mapped_column(JSON, default=lambda: {'version': 1, 'items': [], 'duck_music': True})
    revision: Mapped[int] = mapped_column(Integer, default=0)
    undo: Mapped[list] = mapped_column(JSON, default=list)
    redo: Mapped[list] = mapped_column(JSON, default=list)
    created: Mapped[float] = mapped_column(Float, default=time.time)


class Revision(Base):
    __tablename__ = 'revisions'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    number: Mapped[int] = mapped_column(Integer)
    document: Mapped[dict] = mapped_column(JSON)
    settings: Mapped[dict] = mapped_column(JSON)


class Asset(Base):
    __tablename__ = 'assets'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    kind: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    checksum: Mapped[str] = mapped_column(String)
    duration: Mapped[float] = mapped_column(Float)
    info: Mapped[dict] = mapped_column(JSON)
    provenance: Mapped[dict] = mapped_column(JSON)
    thumbnail: Mapped[str | None] = mapped_column(String, nullable=True)
    proxy: Mapped[str | None] = mapped_column(String, nullable=True)
    created: Mapped[float] = mapped_column(Float, default=time.time)


class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    kind: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String, default='local')
    state: Mapped[str] = mapped_column(String, default='queued', index=True)
    provider_id: Mapped[str | None] = mapped_column(String, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String)
    inputs: Mapped[dict] = mapped_column(JSON)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0)
    reported_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    asset_id: Mapped[str | None] = mapped_column(String, nullable=True)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    next_run: Mapped[float] = mapped_column(Float, default=0)
    created: Mapped[float] = mapped_column(Float, default=time.time)
    updated: Mapped[float] = mapped_column(Float, default=time.time)


@contextmanager
def transaction():
    with Session.begin() as session:
        yield session


def project_lock(session, project_id):
    project = session.query(Project).filter_by(id=project_id).with_for_update().one_or_none()
    if project is None:
        raise ValueError('Project not found')
    return project


def public(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}
