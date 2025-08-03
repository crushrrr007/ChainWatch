# app/core/database.py - Database Setup and Models
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from app.core.config import settings

# Database setup
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(String, unique=True, index=True)
    telegram_username = Column(String, nullable=True)
    wallet_address = Column(String, nullable=True)  # For future wallet auth
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Mission details
    mission_prompt = Column(Text, nullable=False)  # Original user input
    structured_plan = Column(JSON, nullable=False)  # AI-generated plan
    agent_name = Column(String, nullable=True)  # Optional friendly name
    
    # Status and scheduling
    status = Column(String, default="active")  # active, paused, triggered, error
    schedule_interval = Column(Integer, default=300)  # seconds between checks
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="agents")
    alerts = relationship("Alert", back_populates="agent", cascade="all, delete-orphan")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    
    # Alert content
    title = Column(String, nullable=False)
    report_content = Column(Text, nullable=False)  # AI-generated analysis
    raw_data = Column(JSON, nullable=True)  # Original API response
    
    # Alert metadata
    alert_type = Column(String, nullable=False)  # wallet_activity, nft_trade, price_change, etc.
    severity = Column(String, default="medium")  # low, medium, high, critical
    
    # Delivery status
    sent_to_telegram = Column(Boolean, default=False)
    telegram_message_id = Column(String, nullable=True)
    delivery_error = Column(Text, nullable=True)
    
    # Timestamps
    triggered_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="alerts")

class RateLimitTracker(Base):
    __tablename__ = "rate_limit_tracker"
    
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, nullable=False)  # bitscrunch, gemini
    time_window = Column(String, nullable=False)  # minute, hour, day, month
    window_start = Column(DateTime, nullable=False)
    request_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database functions
async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Drop all tables in development (comment out for production)
        if settings.ENVIRONMENT == "development":
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Helper functions for common queries
async def get_user_by_telegram_id(db: AsyncSession, telegram_user_id: str) -> Optional[User]:
    """Get user by Telegram ID"""
    from sqlalchemy import select
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, telegram_user_id: str, telegram_username: str = None) -> User:
    """Create new user"""
    user = User(
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_active_agents(db: AsyncSession):
    """Get all active agents"""
    from sqlalchemy import select
    result = await db.execute(
        select(Agent).where(Agent.status == "active")
    )
    return result.scalars().all()

async def get_agent_with_user(db: AsyncSession, agent_id: int):
    """Get agent with user information"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Agent)
        .options(selectinload(Agent.user))
        .where(Agent.id == agent_id)
    )
    return result.scalar_one_or_none()