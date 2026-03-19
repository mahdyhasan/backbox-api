from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.database import Base
import uuid
from datetime import datetime


class App(Base):
    __tablename__ = "apps"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    status = Column(String, default="active")
    key_hash = Column(String, nullable=False)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class Client(Base):
    __tablename__ = "clients"
    
    id = Column(String, primary_key=True)
    app_id = Column(String, ForeignKey("apps.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String)
    status = Column(String, default="active")
    plan = Column(String, default="free")
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(String, ForeignKey("apps.id"), nullable=False)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)
    filename = Column(String)
    status = Column(String, default="processing")
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(String, nullable=False)
    client_id = Column(String)
    query = Column(String)
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    cost_usd = Column(Float)
    model_used = Column(String)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)