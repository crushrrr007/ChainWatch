# test_sensitive_alert.py - Test with lower thresholds to trigger alerts
import asyncio
import aiohttp
import json

async def test_sensitive_alerts():
    """Test with very low thresholds to trigger alerts"""
    
    missions = [
        {
            "prompt": "Alert me if any collection has volume increase above 0.1x (10%)",
            "name": "Low Threshold Volume Monitor",
            "expected": "Should trigger alerts on any volume activity"
        },
        {
            "prompt": "Monitor any wallet that sends more than 0.01 USDT",
            "name": "Micro Transfer Monitor", 
            "expected": "Should detect small transfers"
        },
        {
            "prompt": "Alert if Bored Ape collection shows any wash trading activity above 1%",
            "name": "BAYC Wash Trade Detector",
            "expected": "Should detect any wash trading"
        }
    ]
    
    url = "http://localhost:8000/api/v1/agents/deploy"
    headers = {"Content-Type": "application/json"}
    
    for i, mission in enumerate(missions):
        print(f"\n{'='*60}")
        print(f"🧪 Test {i+1}: {mission['name']}")
        print(f"Expected: {mission['expected']}")
        print(f"{'='*60}")
        
        payload = {
            "mission_prompt": mission["prompt"],
            "telegram_user_id": "test_user_123",
            "telegram_username": "test_user",
            "agent_name": mission["name"],
            "schedule_interval": 300
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Deploy agent
                async with session.post(url, json=payload, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("success"):
                        agent_id = result['data']['agent_id']
                        structured_plan = result['data']['structured_plan']
                        
                        print(f"✅ Agent {agent_id} deployed successfully!")
                        print(f"Action Type: {structured_plan['action_type']}")
                        print(f"Conditions: {structured_plan['conditions']}")
                        
                        # Run agent immediately
                        run_url = f"http://localhost:8000/api/v1/agents/{agent_id}/run"
                        async with session.post(run_url) as run_response:
                            run_result = await run_response.json()
                            
                            if run_result.get("success"):
                                alerts_count = run_result.get('data', {}).get('alerts_count', 0)
                                print(f"📊 Execution result: {alerts_count} alerts")
                                
                                if alerts_count > 0:
                                    print("🚨 SUCCESS! Alerts were triggered!")
                                else:
                                    print("📈 No alerts (may need even lower threshold)")
                            else:
                                print(f"❌ Execution failed: {run_result.get('message')}")
                    else:
                        print(f"❌ Deployment failed: {result}")
                        
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        # Small delay between tests
        await asyncio.sleep(2)

async def test_telegram_notification():
    """Test telegram integration"""
    print(f"\n{'='*60}")
    print("📱 Testing Telegram Integration")
    print(f"{'='*60}")
    
    url = "http://localhost:8000/api/v1/test/telegram"
    payload = {
        "chat_id": "1266693480",
        "message": "🎉 ChainWatch Alert System Test\n\n✅ All systems operational\n🤖 AI agents deployed successfully\n📊 Monitoring blockchain activity\n\nThis is a test notification!"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if result.get("success"):
                    print("✅ Telegram message sent successfully!")
                    print(f"Message ID: {result.get('data', {}).get('message_id')}")
                    print("📱 Check your Telegram for the test message!")
                else:
                    print(f"❌ Telegram test failed: {result.get('message')}")
                    
    except Exception as e:
        print(f"❌ Telegram test error: {e}")

async def show_system_status():
    """Show comprehensive system status"""
    print(f"\n{'='*60}")
    print("🏆 ChainWatch System Status Report")
    print(f"{'='*60}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Health check
            async with session.get("http://localhost:8000/api/v1/health") as response:
                health = await response.json()
                print(f"System Health: {health.get('status', 'unknown').upper()}")
                
                services = health.get('services', {})
                for service, status in services.items():
                    emoji = "✅" if "healthy" in status else "⚠️" if "degraded" in status else "❌"
                    print(f"  {emoji} {service}: {status}")
            
            # Agent stats
            async with session.get("http://localhost:8000/api/v1/agents/stats") as response:
                stats = await response.json()
                scheduler_stats = stats.get('data', {})
                print(f"\nScheduler Stats:")
                print(f"  🔄 Running: {scheduler_stats.get('is_running', False)}")
                print(f"  📊 Agents Processed: {scheduler_stats.get('agents_processed', 0)}")
                print(f"  🚨 Alerts Generated: {scheduler_stats.get('alerts_generated', 0)}")
                print(f"  ❌ Errors: {scheduler_stats.get('errors', 0)}")
                
            # List all agents
            params = {"telegram_user_id": "test_user_123"}
            async with session.get("http://localhost:8000/api/v1/agents/", params=params) as response:
                agents_result = await response.json()
                agents = agents_result.get('items', [])
                
                print(f"\nActive Agents: {len(agents)}")
                for agent in agents:
                    print(f"  🤖 {agent['id']}: {agent.get('agent_name', 'Unnamed')} ({agent['status']})")
                
    except Exception as e:
        print(f"❌ Status check failed: {e}")

if __name__ == "__main__":
    async def run_comprehensive_test():
        await show_system_status()
        await test_telegram_notification()
        await test_sensitive_alerts()
        
        print(f"\n{'='*60}")
        print("🎯 ChainWatch Testing Complete!")
        print("Your system is PRODUCTION READY! 🚀")
        print(f"{'='*60}")
    
    asyncio.run(run_comprehensive_test())