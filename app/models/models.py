from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.database import Base
import uuid
from datetime import datetime


class Provider(Base):
    """LLM Providers (OpenAI, Anthropic, Groq, etc.)"""
    __tablename__ = "providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(100))
    api_key_encrypted = Column(Text)
    base_url = Column(String(255))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    models = relationship("Model", back_populates="provider", cascade="all, delete-orphan")


class Model(Base):
    """Specific models belonging to providers"""
    __tablename__ = "models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False)
    name = Column(String(100), nullable=False)
    identifier = Column(String(100), nullable=False)
    context_window = Column(Integer)
    input_cost_per_1k = Column(Numeric(10, 6), default=0.0)
    output_cost_per_1k = Column(Numeric(10, 6), default=0.0)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    provider = relationship("Provider", back_populates="models")


class App(Base):
    """Applications (The Products/Solutions: AURA, Sales Analyzer)"""
    __tablename__ = "apps"
    
    id = Column(String, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    type = Column(String(50), default="SaaS")
    status = Column(String(20), default="active")
    settings = Column(JSONB, default={"default_chunk_size": 400, "retrieval_depth": 8})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clients = relationship("Client", back_populates="app", cascade="all, delete-orphan")
    allowed_providers = relationship("AppAllowedProvider", cascade="all, delete-orphan")


class AppAllowedProvider(Base):
    """Many-to-Many: Apps can use multiple LLMs"""
    __tablename__ = "app_allowed_providers"
    
    app_id = Column(String, ForeignKey("apps.id"), primary_key=True)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), primary_key=True)
    daily_token_limit = Column(Integer, default=100000)


class Client(Base):
    """Clients (Paying Customers of Apps)"""
    __tablename__ = "clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(String, ForeignKey("apps.id"), nullable=False)
    name = Column(String(255), nullable=False)
    external_id = Column(String(255))
    plan = Column(String(50), default="Basic")
    status = Column(String(20), default="active")
    scope_id = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    app = relationship("App", back_populates="clients")
    documents = relationship("Document", back_populates="client", cascade="all, delete-orphan")
    assigned_providers = relationship("ClientAssignedProvider", cascade="all, delete-orphan")


class ClientAssignedProvider(Base):
    """Many-to-Many: Clients can have specific LLMs enabled"""
    __tablename__ = "client_assigned_providers"
    
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), primary_key=True)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), primary_key=True)
    monthly_budget_cap = Column(Numeric(10, 2))


class APIKey(Base):
    """API Keys (Hierarchy: Platform -> App -> Client)"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_prefix = Column(String(30), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    scope_level = Column(String(20), nullable=False)
    app_id = Column(String, ForeignKey("apps.id"))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminUser(Base):
    """Admin Users (Super Admins for this Dashboard)"""
    __tablename__ = "admin_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    """Documents (Metadata for ingested files)"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(String, ForeignKey("apps.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    file_name = Column(String(255))
    file_type = Column(String(50))
    storage_path = Column(String(500))
    status = Column(String(20), default="processing")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="documents")


class UsageLog(Base):
    """Usage Logs (Audit & Billing)"""
    __tablename__ = "usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(String, ForeignKey("apps.id"))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"))
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"))
    request_type = Column(String(50))
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_cost = Column(Numeric(10, 6))
    latency_ms = Column(Integer)
    status_code = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)