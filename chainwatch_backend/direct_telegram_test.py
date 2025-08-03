# direct_telegram_test.py - Test Telegram directly
import asyncio
import aiohttp

async def test_telegram_direct():
    """Test Telegram bot directly"""
    
    bot_token = "8385952831:AAFkqQekZl7V5tdA_j__z-tCRbb9PJlibLM"
    chat_id = "1266693480"
    
    # Test 1: Check bot info
    print("🤖 Testing bot info...")
    bot_info_url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(bot_info_url) as response:
                result = await response.json()
                
                if result.get("ok"):
                    bot_info = result.get("result", {})
                    print(f"✅ Bot is active: @{bot_info.get('username')}")
                    print(f"   Bot Name: {bot_info.get('first_name')}")
                else:
                    print(f"❌ Bot info failed: {result}")
                    return False
    except Exception as e:
        print(f"❌ Bot info error: {e}")
        return False
    
    # Test 2: Send message directly
    print(f"\n📱 Sending test message to chat {chat_id}...")
    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    message = """🚀 ChainWatch Alert System Test

✅ Direct Telegram integration working!
🤖 Your AI blockchain monitoring agents are ready
📊 Real-time alerts will appear here

This is a direct API test message."""
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(send_url, json=payload) as response:
                result = await response.json()
                
                if result.get("ok"):
                    message_id = result.get("result", {}).get("message_id")
                    print(f"✅ Message sent successfully!")
                    print(f"   Message ID: {message_id}")
                    print(f"📱 Check your Telegram now!")
                    return True
                else:
                    print(f"❌ Message failed: {result}")
                    return False
    except Exception as e:
        print(f"❌ Message error: {e}")
        return False

async def test_backend_telegram():
    """Test Telegram via ChainWatch backend"""
    
    print("\n🔗 Testing via ChainWatch backend...")
    
    url = "http://localhost:8000/api/v1/test/telegram"
    payload = {
        "chat_id": "1266693480",
        "message": "🎯 ChainWatch Backend → Telegram Test\n\n✅ Backend integration working!\n🤖 Ready for real alerts!"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        print("✅ Backend → Telegram working!")
                        return True
                    else:
                        print(f"❌ Backend test failed: {result}")
                else:
                    error_text = await response.text()
                    print(f"❌ Backend error {response.status}: {error_text}")
    except Exception as e:
        print(f"❌ Backend test error: {e}")
    
    return False

if __name__ == "__main__":
    async def run_tests():
        print("📱 ChainWatch Telegram Integration Test")
        print("=" * 50)
        
        direct_ok = await test_telegram_direct()
        backend_ok = await test_backend_telegram()
        
        print("\n" + "=" * 50)
        if direct_ok and backend_ok:
            print("🎉 SUCCESS! Telegram integration fully working!")
            print("📱 You should have received 2 test messages")
        elif direct_ok:
            print("⚠️ Direct Telegram works, backend integration needs fixing")
        else:
            print("❌ Telegram integration needs debugging")
    
    asyncio.run(run_tests())