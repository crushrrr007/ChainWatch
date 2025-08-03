# app/models/schemas.py - Pydantic Models for API
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator

# User Schemas
class UserBase(BaseModel):
    telegram_user_id: str
    telegram_username: Optional[str] = None
    wallet_address: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Agent Schemas
class AgentCreate(BaseModel):
    mission_prompt: str = Field(..., min_length=10, max_length=1000, description="Natural language mission description")
    telegram_user_id: str = Field(..., description="Telegram user ID for alerts")
    telegram_username: Optional[str] = None
    agent_name: Optional[str] = Field(None, max_length=100, description="Optional friendly name for the agent")
    schedule_interval: Optional[int] = Field(300, ge=60, le=3600, description="Check interval in seconds (1-60 minutes)")
    
    @validator('mission_prompt')
    def validate_mission_prompt(cls, v):
        if not v.strip():
            raise ValueError('Mission prompt cannot be empty')
        return v.strip()

class AgentStructuredPlan(BaseModel):
    """Schema for AI-generated agent plan"""
    action_type: str = Field(..., description="Type of monitoring: wallet_monitor, nft_monitor, collection_monitor")
    target: Dict[str, Any] = Field(..., description="Target to monitor (wallet address, NFT contract, etc.)")
    conditions: List[Dict[str, Any]] = Field(..., description="Trigger conditions")
    blockchain: str = Field(..., description="Target blockchain")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")

class AgentUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(active|paused|triggered|error)$")
    schedule_interval: Optional[int] = Field(None, ge=60, le=3600)
    agent_name: Optional[str] = Field(None, max_length=100)

class Agent(BaseModel):
    id: int
    user_id: int
    mission_prompt: str
    structured_plan: Dict[str, Any]
    agent_name: Optional[str]
    status: str
    schedule_interval: int
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    error_count: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AgentWithUser(Agent):
    user: User

# Alert Schemas
class AlertCreate(BaseModel):
    agent_id: int
    title: str = Field(..., max_length=200)
    report_content: str
    raw_data: Optional[Dict[str, Any]] = None
    alert_type: str
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")

class Alert(BaseModel):
    id: int
    agent_id: int
    title: str
    report_content: str
    raw_data: Optional[Dict[str, Any]]
    alert_type: str
    severity: str
    sent_to_telegram: bool
    telegram_message_id: Optional[str]
    delivery_error: Optional[str]
    triggered_at: datetime
    sent_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class AlertWithAgent(Alert):
    agent: Agent

# API Response Schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int

# Mission Parser Schemas
class MissionParseRequest(BaseModel):
    mission_prompt: str
    context: Optional[Dict[str, Any]] = None

class MissionParseResponse(BaseModel):
    success: bool
    structured_plan: Optional[AgentStructuredPlan] = None
    error: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

# External API Schemas (bitsCrunch)
class WalletBalanceResponse(BaseModel):
    """Schema for bitsCrunch wallet balance response"""
    wallet_address: str
    blockchain: str
    chain_id: int
    tokens: List[Dict[str, Any]]

class NFTTransactionResponse(BaseModel):
    """Schema for bitsCrunch NFT transaction response"""
    transaction_hash: str
    block_number: int
    timestamp: datetime
    from_address: str
    to_address: str
    token_id: str
    price: Optional[float]
    marketplace: Optional[str]
    
# Demo Schemas
class DemoMissionExamples(BaseModel):
    wallet_monitoring: List[str] = [
        "Alert me if wallet 0x742d35Cc6bf8e1d6D8aEc8967c96e5e5E2DbDcf5 sends more than 5 ETH to any new address",
        "Monitor wallet 0x742d35Cc6bf8e1d6D8aEc8967c96e5e5E2DbDcf5 for any NFT purchases over $1000",
        "Watch wallet 0x742d35Cc6bf8e1d6D8aEc8967c96e5e5E2DbDcf5 and alert me if it receives tokens from a new address"
    ]
    nft_monitoring: List[str] = [
        "Alert me if any Bored Ape Yacht Club NFT is sold for less than 10 ETH",
        "Monitor CryptoPunks for wash trading activity and alert if detected",
        "Watch for any rare trait Azuki NFTs being listed below floor price"
    ]
    collection_monitoring: List[str] = [
        "Monitor Pudgy Penguins collection for unusual trading volume spikes",
        "Alert me if World of Women collection shows signs of coordinated manipulation",
        "Track Art Blocks Curated for any pieces being flipped within 24 hours"
    ]

# Health Check Schema
class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]  # service_name -> status