# app/core/config.py - Configuration Management
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://chainwatch:password@localhost/chainwatch"
    
    # bitsCrunch API
    BITSCRUNCH_API_KEY: str
    BITSCRUNCH_BASE_URL: str = "https://api.unleashnfts.com/api/v1"
    BITSCRUNCH_RATE_LIMIT_PER_MINUTE: int = 20
    BITSCRUNCH_RATE_LIMIT_PER_MONTH: int = 25000
    
    # Google Gemini API
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: Optional[str] = None  # Default chat for demos
    
    # Agent Scheduler
    AGENT_CHECK_INTERVAL: int = 300  # 5 minutes default
    MAX_CONCURRENT_AGENTS: int = 4
    
    # Rate Limiting
    ENABLE_RATE_LIMITING: bool = True
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    @validator('BITSCRUNCH_API_KEY', 'GEMINI_API_KEY', 'TELEGRAM_BOT_TOKEN')
    def validate_required_keys(cls, v):
        if not v:
            raise ValueError('This field is required')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings instance
settings = Settings()

# Supported blockchains mapping
SUPPORTED_BLOCKCHAINS = {
    "ethereum": 1,
    "polygon": 137,
    "avalanche": 43114,
    "bsc": 57,  # Binance Smart Chain
    "linea": 59144,
    "solana": 900
}

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "bitscrunch": {
        "per_minute": settings.BITSCRUNCH_RATE_LIMIT_PER_MINUTE,
        "per_month": settings.BITSCRUNCH_RATE_LIMIT_PER_MONTH
    }
}