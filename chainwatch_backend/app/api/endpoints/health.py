# app/api/endpoints/health.py - Fixed Health Check
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiohttp
import asyncio
from sqlalchemy import text  # Import text
from app.models.schemas import HealthCheck, APIResponse
from app.core.config import settings
from app.core.database import get_db, AsyncSession
from app.agents.action_dispatcher import ActionDispatcher

router = APIRouter()

@router.get("/health", response_model=HealthCheck)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check for all system components"""
    
    services = {}
    overall_status = "healthy"
    
    # Check database (FIXED)
    try:
        await db.execute(text("SELECT 1"))  # Use text() wrapper
        services["database"] = "healthy"
    except Exception as e:
        services["database"] = f"unhealthy: {str(e)}"
        overall_status = "unhealthy"
    
    # Check bitsCrunch API
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(
                f"{settings.BITSCRUNCH_BASE_URL}/nft/collection/analytics?blockchain=ethereum&limit=1",
                headers={"x-api-key": settings.BITSCRUNCH_API_KEY}
            ) as response:
                if response.status == 200:
                    services["bitscrunch_api"] = "healthy"
                else:
                    services["bitscrunch_api"] = f"unhealthy: HTTP {response.status}"
                    overall_status = "degraded"
    except Exception as e:
        services["bitscrunch_api"] = f"unhealthy: {str(e)}"
        overall_status = "unhealthy"
    
    # Check Gemini API
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # Simple test generation
        response = model.generate_content("Test: respond with 'OK'")
        if "OK" in response.text.upper():
            services["gemini_api"] = "healthy"
        else:
            services["gemini_api"] = "degraded: unexpected response"
            overall_status = "degraded"
    except Exception as e:
        services["gemini_api"] = f"unhealthy: {str(e)}"
        overall_status = "unhealthy"
    
    # Check Telegram API
    try:
        dispatcher = ActionDispatcher()
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        services["telegram_api"] = "healthy"
                    else:
                        services["telegram_api"] = "degraded: API returned not ok"
                        overall_status = "degraded"
                else:
                    services["telegram_api"] = f"unhealthy: HTTP {response.status}"
                    overall_status = "degraded"
    except Exception as e:
        services["telegram_api"] = f"unhealthy: {str(e)}"
        overall_status = "degraded"
    
    # Check scheduler
    try:
        from main import scheduler
        if scheduler and scheduler.is_running:
            services["scheduler"] = "healthy"
        else:
            services["scheduler"] = "unhealthy: not running"
            overall_status = "degraded"
    except Exception as e:
        services["scheduler"] = f"unhealthy: {str(e)}"
        overall_status = "unhealthy"
    
    return HealthCheck(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        services=services
    )

@router.get("/ping", response_model=APIResponse)
async def ping():
    """Simple ping endpoint for basic availability check"""
    return APIResponse(
        success=True,
        message="pong",
        data={
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ChainWatch API"
        }
    )

@router.post("/test/telegram", response_model=APIResponse)
async def test_telegram_integration(payload: dict):
    """Test Telegram integration by sending a message"""
    try:
        chat_id = payload.get("chat_id")
        message = payload.get("message", "🤖 ChainWatch Test Message - Integration working correctly!")
        
        if not chat_id:
            return APIResponse(
                success=False,
                message="chat_id is required"
            )
        
        dispatcher = ActionDispatcher()
        result = await dispatcher.send_test_message(chat_id, message)
        
        if result["success"]:
            return APIResponse(
                success=True,
                message="Test message sent successfully",
                data=result
            )
        else:
            return APIResponse(
                success=False,
                message=f"Test message failed: {result.get('error')}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telegram test failed: {str(e)}")

@router.get("/config/info", response_model=APIResponse)
async def get_config_info():
    """Get non-sensitive configuration information"""
    return APIResponse(
        success=True,
        message="Configuration information",
        data={
            "environment": settings.ENVIRONMENT,
            "debug_mode": settings.DEBUG,
            "rate_limiting_enabled": settings.ENABLE_RATE_LIMITING,
            "agent_check_interval": settings.AGENT_CHECK_INTERVAL,
            "max_concurrent_agents": settings.MAX_CONCURRENT_AGENTS,
            "bitscrunch_rate_limits": {
                "per_minute": settings.BITSCRUNCH_RATE_LIMIT_PER_MINUTE,
                "per_month": settings.BITSCRUNCH_RATE_LIMIT_PER_MONTH
            }
        }
    )