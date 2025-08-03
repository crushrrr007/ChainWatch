# manual_alert_generator.py - Manually trigger alerts for demo
import asyncio
import aiohttp
from datetime import datetime

async def send_demo_alert():
    """Send a realistic demo alert to your Telegram"""
    
    bot_token = "8385952831:AAFkqQekZl7V5tdA_j__z-tCRbb9PJlibLM"
    chat_id = "1266693480"
    
    # Create realistic alert message
    alert_message = f"""🤖 **ChainWatch Alert**

🔴 **HIGH ALERT**

📋 **Summary:** Large wallet transfer detected - 15,847 USDT moved

🔔 **Alert 1:** Wallet Threshold Exceeded
📝 Wallet 0x742d...96045 sent 15,847 USDT (threshold: 1,000 USDT)

💡 **Recommended Actions:**
• Monitor for additional large transfers
• Check if this is part of a larger pattern

📊 **Technical Details:**
• Transaction: 0xabcd...1234
• Block: 18,547,892
• Gas Used: 21,000
• Confidence: 98%

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": alert_message,
        "parse_mode": "Markdown"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if result.get("ok"):
                    print("🚨 DEMO ALERT SENT!")
                    print("📱 Check your Telegram for the alert!")
                    return True
                else:
                    print(f"❌ Alert failed: {result}")
                    return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def send_collection_alert():
    """Send a collection monitoring alert"""
    
    bot_token = "8385952831:AAFkqQekZl7V5tdA_j__z-tCRbb9PJlibLM"
    chat_id = "1266693480"
    
    alert_message = f"""🤖 **ChainWatch Alert**

🟠 **MEDIUM ALERT**

📋 **Summary:** Bored Ape Yacht Club volume spike detected

🔔 **Alert 1:** Volume Spike Detected
📝 BAYC trading volume increased by 287% in the last hour

🔔 **Alert 2:** Whale Activity
📝 3 new whale wallets started accumulating BAYC NFTs

💡 **Recommended Actions:**
• Investigate potential market catalyst
• Monitor floor price movements
• Check for wash trading patterns

📊 **Collection Stats:**
• Volume: 1,247 ETH (↑287%)
• Sales: 156 (↑45%)
• Floor Price: 12.4 ETH (↑8%)
• Active Traders: 89 (↑34%)

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": alert_message,
        "parse_mode": "Markdown"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if result.get("ok"):
                    print("🚨 COLLECTION ALERT SENT!")
                    print("📱 Check your Telegram for the collection alert!")
                    return True
                else:
                    print(f"❌ Alert failed: {result}")
                    return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def send_wash_trade_alert():
    """Send a wash trading detection alert"""
    
    bot_token = "8385952831:AAFkqQekZl7V5tdA_j__z-tCRbb9PJlibLM"
    chat_id = "1266693480"
    
    alert_message = f"""🤖 **ChainWatch Alert**

🔴 **CRITICAL ALERT**

📋 **Summary:** Wash trading activity detected in monitored collection

🔔 **Alert 1:** Wash Trading Detected
📝 Suspicious back-and-forth trading pattern identified

⚠️ **Warning Signs:**
• Same wallet buying/selling repeatedly
• Artificial volume inflation: 34%
• Price manipulation indicators
• Coordinated activity across 7 wallets

💡 **Recommended Actions:**
• ⚠️ AVOID trading this collection temporarily
• Report to marketplace if confirmed
• Monitor for regulatory action

📊 **Detection Details:**
• Wash Trade Ratio: 34.7%
• Affected Volume: 89.3 ETH
• Suspicious Wallets: 7
• Pattern Confidence: 94%

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

🚨 **This is a high-confidence alert. Exercise caution.**
"""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": alert_message,
        "parse_mode": "Markdown"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if result.get("ok"):
                    print("🚨 WASH TRADE ALERT SENT!")
                    print("📱 Check your Telegram for the critical alert!")
                    return True
                else:
                    print(f"❌ Alert failed: {result}")
                    return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    async def demo_all_alerts():
        print("🚨 ChainWatch Demo Alert Generator")
        print("=" * 50)
        print("Sending 3 different types of alerts to your Telegram...")
        
        print("\n1. 💰 Wallet Transfer Alert...")
        await send_demo_alert()
        await asyncio.sleep(2)
        
        print("\n2. 📊 Collection Volume Alert...")
        await send_collection_alert()
        await asyncio.sleep(2)
        
        print("\n3. ⚠️ Wash Trading Alert...")
        await send_wash_trade_alert()
        
        print("\n🎯 Demo complete! Check your Telegram for 3 different alert types!")
        print("This shows exactly what your users will receive when real conditions are met.")
    
    asyncio.run(demo_all_alerts())