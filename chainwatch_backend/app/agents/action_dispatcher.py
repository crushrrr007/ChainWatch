# app/agents/action_dispatcher.py - Notification and Action Dispatcher
import asyncio
import logging
from typing import Dict, Any, Optional
import aiohttp
from app.core.config import settings
from app.core.database import AsyncSession, Alert, Agent, User

logger = logging.getLogger(__name__)

class ActionDispatcher:
    """Handles notification delivery and other actions"""
    
    def __init__(self):
        self.telegram_bot_token = settings.TELEGRAM_BOT_TOKEN
        self.telegram_base_url = f"https://api.telegram.org/bot{self.telegram_bot_token}"
        
    async def dispatch_alert(
        self, 
        alert: Alert, 
        agent: Agent, 
        user: User, 
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Dispatch an alert through configured channels
        
        Args:
            alert: Alert database object
            agent: Agent that triggered the alert
            user: User to notify
            analysis: Analysis results from analysis_engine
        
        Returns:
            Dict containing dispatch results
        """
        results = {
            "success": True,
            "channels": {},
            "errors": []
        }
        
        try:
            # Send Telegram notification
            telegram_result = await self._send_telegram_alert(alert, agent, user, analysis)
            results["channels"]["telegram"] = telegram_result
            
            # Future: Add other notification channels (email, webhook, etc.)
            
            return results
            
        except Exception as e:
            logger.error(f"Alert dispatch failed: {str(e)}")
            results["success"] = False
            results["errors"].append(str(e))
            return results
    
    async def _send_telegram_alert(
        self, 
        alert: Alert, 
        agent: Agent, 
        user: User, 
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send alert via Telegram"""
        try:
            # Determine chat ID
            chat_id = user.telegram_user_id or settings.TELEGRAM_CHAT_ID
            
            if not chat_id:
                return {
                    "success": False,
                    "error": "No Telegram chat ID available"
                }
            
            # Generate message from analysis
            from app.agents.analysis_engine import AnalysisEngine
            engine = AnalysisEngine()
            message = await engine.generate_telegram_message(analysis, agent.agent_name)
            
            # Send message
            response = await self._send_telegram_message(chat_id, message)
            
            if response["success"]:
                # Update alert with delivery info
                alert.sent_to_telegram = True
                alert.telegram_message_id = response.get("message_id")
                alert.sent_at = asyncio.get_event_loop().time()
                
                return {
                    "success": True,
                    "message_id": response.get("message_id"),
                    "chat_id": chat_id
                }
            else:
                alert.delivery_error = response.get("error")
                return response
                
        except Exception as e:
            logger.error(f"Telegram alert failed: {str(e)}")
            alert.delivery_error = str(e)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_telegram_message(self, chat_id: str, message: str) -> Dict[str, Any]:
        """Send a message via Telegram Bot API"""
        try:
            url = f"{self.telegram_base_url}/sendMessage"
            
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    response_data = await response.json()
                    
                    if response.status == 200 and response_data.get("ok"):
                        message_info = response_data.get("result", {})
                        return {
                            "success": True,
                            "message_id": str(message_info.get("message_id")),
                            "chat_id": str(message_info.get("chat", {}).get("id"))
                        }
                    else:
                        error_msg = response_data.get("description", f"HTTP {response.status}")
                        logger.error(f"Telegram API error: {error_msg}")
                        return {
                            "success": False,
                            "error": error_msg
                        }
                        
        except Exception as e:
            logger.error(f"Telegram message send failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_test_message(self, chat_id: str, message: str = None) -> Dict[str, Any]:
        """Send a test message to verify Telegram integration"""
        test_message = message or """
🤖 **ChainWatch Test Alert**

🟢 **TEST MESSAGE**

📋 **Summary:** This is a test message to verify Telegram integration is working correctly.

🔔 **Test Alert:** System connectivity check
📝 All systems operational and ready for monitoring

💡 **Recommended Actions:**
• Confirm you received this message
• Deploy your first monitoring agent

⏰ Test completed successfully
"""
        
        return await self._send_telegram_message(chat_id, test_message)
    
    async def get_telegram_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """Get information about a Telegram chat"""
        try:
            url = f"{self.telegram_base_url}/getChat"
            params = {"chat_id": chat_id}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response_data = await response.json()
                    
                    if response.status == 200 and response_data.get("ok"):
                        chat_info = response_data.get("result", {})
                        return {
                            "success": True,
                            "chat_info": {
                                "id": chat_info.get("id"),
                                "type": chat_info.get("type"),
                                "title": chat_info.get("title"),
                                "username": chat_info.get("username"),
                                "first_name": chat_info.get("first_name"),
                                "last_name": chat_info.get("last_name")
                            }
                        }
                    else:
                        error_msg = response_data.get("description", f"HTTP {response.status}")
                        return {
                            "success": False,
                            "error": error_msg
                        }
                        
        except Exception as e:
            logger.error(f"Get chat info failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def setup_telegram_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Setup Telegram webhook for receiving messages (optional for future features)"""
        try:
            url = f"{self.telegram_base_url}/setWebhook"
            payload = {
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    response_data = await response.json()
                    
                    if response.status == 200 and response_data.get("ok"):
                        return {
                            "success": True,
                            "webhook_info": response_data.get("result")
                        }
                    else:
                        error_msg = response_data.get("description", f"HTTP {response.status}")
                        return {
                            "success": False,
                            "error": error_msg
                        }
                        
        except Exception as e:
            logger.error(f"Webhook setup failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# Helper functions for demo and testing
async def test_telegram_integration():
    """Test Telegram integration"""
    dispatcher = ActionDispatcher()
    
    # Test with default chat ID from settings
    if settings.TELEGRAM_CHAT_ID:
        print("Testing Telegram integration...")
        
        # Send test message
        result = await dispatcher.send_test_message(settings.TELEGRAM_CHAT_ID)
        
        if result["success"]:
            print("✅ Test message sent successfully!")
            print(f"Message ID: {result.get('message_id')}")
        else:
            print("❌ Test message failed!")
            print(f"Error: {result.get('error')}")
        
        # Get chat info
        chat_info = await dispatcher.get_telegram_chat_info(settings.TELEGRAM_CHAT_ID)
        if chat_info["success"]:
            print("✅ Chat info retrieved:")
            print(f"Chat details: {chat_info['chat_info']}")
        else:
            print("❌ Chat info failed:")
            print(f"Error: {chat_info.get('error')}")
    else:
        print("❌ No Telegram chat ID configured in settings")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_telegram_integration())