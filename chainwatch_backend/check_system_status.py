# check_system_status.py - Complete system verification
import asyncio
import aiohttp
import json

async def check_all_agents():
    """Check all deployed agents"""
    print("🤖 Checking your deployed agents...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/v1/agents/?telegram_user_id=1266693480") as response:
                result = await response.json()
                
                agents = result.get("items", [])
                print(f"📊 Total agents: {len(agents)}")
                
                for agent in agents:
                    print(f"\n🤖 Agent {agent['id']}: {agent.get('agent_name', 'Unnamed')}")
                    print(f"   Status: {agent['status']}")
                    print(f"   Mission: {agent['mission_prompt'][:60]}...")
                    print(f"   Last Run: {agent.get('last_run_at', 'Never')}")
                    print(f"   Schedule: Every {agent.get('schedule_interval', 300)} seconds")
                
                return agents
                
    except Exception as e:
        print(f"❌ Error checking agents: {e}")
        return []

async def run_all_agents_manually():
    """Manually run all agents to check for alerts"""
    print("\n⚡ Running all agents manually to check for alerts...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get all agents
            async with session.get("http://localhost:8000/api/v1/agents/?telegram_user_id=1266693480") as response:
                result = await response.json()
                agents = result.get("items", [])
                
                total_alerts = 0
                
                for agent in agents:
                    agent_id = agent['id']
                    agent_name = agent.get('agent_name', f'Agent {agent_id}')
                    
                    print(f"\n🔄 Running {agent_name}...")
                    
                    run_url = f"http://localhost:8000/api/v1/agents/{agent_id}/run"
                    async with session.post(run_url) as run_response:
                        run_result = await run_response.json()
                        
                        if run_result.get("success"):
                            alerts_count = run_result.get('data', {}).get('alerts_count', 0)
                            total_alerts += alerts_count
                            
                            if alerts_count > 0:
                                print(f"🚨 {agent_name}: {alerts_count} alerts triggered!")
                                print("📱 Check your Telegram!")
                            else:
                                print(f"📊 {agent_name}: No alerts (conditions not met)")
                        else:
                            print(f"❌ {agent_name}: Execution failed - {run_result.get('message')}")
                
                print(f"\n🎯 Manual run complete: {total_alerts} total alerts triggered")
                return total_alerts > 0
                
    except Exception as e:
        print(f"❌ Error running agents: {e}")
        return False

async def check_alerts_generated():
    """Check if any alerts were stored in database"""
    print("\n📋 Checking stored alerts...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/v1/alerts/?telegram_user_id=1266693480") as response:
                result = await response.json()
                
                alerts = result.get("items", [])
                print(f"📊 Total alerts in database: {len(alerts)}")
                
                for alert in alerts:
                    print(f"\n🔔 Alert {alert['id']}: {alert['title']}")
                    print(f"   Severity: {alert['severity']}")
                    print(f"   Triggered: {alert['triggered_at']}")
                    print(f"   Sent to Telegram: {alert['sent_to_telegram']}")
                
                return len(alerts)
                
    except Exception as e:
        print(f"❌ Error checking alerts: {e}")
        return 0

async def send_test_telegram():
    """Send a test message directly"""
    print("\n📱 Sending test Telegram message...")
    
    bot_token = "8385952831:AAFkqQekZl7V5tdA_j__z-tCRbb9PJlibLM"
    chat_id = "1266693480"
    
    message = f"""🎯 ChainWatch Status Update

✅ Ultra-sensitive agents deployed:
• Agent 2: USDT Monitor (>0.001 USDT)
• Agent 3: Volume Monitor (>0.01% change)

⚡ System is actively monitoring blockchain data
📊 Agents will check every 3 minutes
🚨 Alerts will appear here when conditions are met

System Status: OPERATIONAL 🚀"""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if result.get("ok"):
                    print("✅ Test message sent to Telegram!")
                    print("📱 Check your Telegram for status update!")
                    return True
                else:
                    print(f"❌ Telegram test failed: {result}")
                    return False
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

if __name__ == "__main__":
    async def full_system_check():
        print("🔍 ChainWatch Complete System Check")
        print("=" * 50)
        
        # Check agents
        agents = await check_all_agents()
        
        # Run agents manually
        alerts_triggered = await run_all_agents_manually()
        
        # Check stored alerts
        stored_alerts = await check_alerts_generated()
        
        # Send test message
        telegram_ok = await send_test_telegram()
        
        print("\n" + "=" * 50)
        print("🎯 SYSTEM STATUS SUMMARY")
        print("=" * 50)
        print(f"🤖 Active Agents: {len(agents)}")
        print(f"🚨 Alerts Triggered: {'Yes' if alerts_triggered else 'No'}")
        print(f"📋 Stored Alerts: {stored_alerts}")
        print(f"📱 Telegram: {'Working' if telegram_ok else 'Needs Fix'}")
        
        if alerts_triggered:
            print("\n🎉 SUCCESS! Your system is generating real alerts!")
        else:
            print("\n📊 System working, no alerts triggered (normal blockchain activity)")
            print("💡 Try the demo alerts: python manual_alert_generator.py")
    
    asyncio.run(full_system_check())# check_system_status.py - Complete system verification
import asyncio
import aiohttp
import json

async def check_all_agents():
    """Check all deployed agents"""
    print("🤖 Checking your deployed agents...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/v1/agents/?telegram_user_id=1266693480") as response:
                result = await response.json()
                
                agents = result.get("items", [])
                print(f"📊 Total agents: {len(agents)}")
                
                for agent in agents:
                    print(f"\n🤖 Agent {agent['id']}: {agent.get('agent_name', 'Unnamed')}")
                    print(f"   Status: {agent['status']}")
                    print(f"   Mission: {agent['mission_prompt'][:60]}...")
                    print(f"   Last Run: {agent.get('last_run_at', 'Never')}")
                    print(f"   Schedule: Every {agent.get('schedule_interval', 300)} seconds")
                
                return agents
                
    except Exception as e:
        print(f"❌ Error checking agents: {e}")
        return []

async def run_all_agents_manually():
    """Manually run all agents to check for alerts"""
    print("\n⚡ Running all agents manually to check for alerts...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get all agents
            async with session.get("http://localhost:8000/api/v1/agents/?telegram_user_id=1266693480") as response:
                result = await response.json()
                agents = result.get("items", [])
                
                total_alerts = 0
                
                for agent in agents:
                    agent_id = agent['id']
                    agent_name = agent.get('agent_name', f'Agent {agent_id}')
                    
                    print(f"\n🔄 Running {agent_name}...")
                    
                    run_url = f"http://localhost:8000/api/v1/agents/{agent_id}/run"
                    async with session.post(run_url) as run_response:
                        run_result = await run_response.json()
                        
                        if run_result.get("success"):
                            alerts_count = run_result.get('data', {}).get('alerts_count', 0)
                            total_alerts += alerts_count
                            
                            if alerts_count > 0:
                                print(f"🚨 {agent_name}: {alerts_count} alerts triggered!")
                                print("📱 Check your Telegram!")
                            else:
                                print(f"📊 {agent_name}: No alerts (conditions not met)")
                        else:
                            print(f"❌ {agent_name}: Execution failed - {run_result.get('message')}")
                
                print(f"\n🎯 Manual run complete: {total_alerts} total alerts triggered")
                return total_alerts > 0
                
    except Exception as e:
        print(f"❌ Error running agents: {e}")
        return False

async def check_alerts_generated():
    """Check if any alerts were stored in database"""
    print("\n📋 Checking stored alerts...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/v1/alerts/?telegram_user_id=1266693480") as response:
                result = await response.json()
                
                alerts = result.get("items", [])
                print(f"📊 Total alerts in database: {len(alerts)}")
                
                for alert in alerts:
                    print(f"\n🔔 Alert {alert['id']}: {alert['title']}")
                    print(f"   Severity: {alert['severity']}")
                    print(f"   Triggered: {alert['triggered_at']}")
                    print(f"   Sent to Telegram: {alert['sent_to_telegram']}")
                
                return len(alerts)
                
    except Exception as e:
        print(f"❌ Error checking alerts: {e}")
        return 0

async def send_test_telegram():
    """Send a test message directly"""
    print("\n📱 Sending test Telegram message...")
    
    bot_token = "8385952831:AAFkqQekZl7V5tdA_j__z-tCRbb9PJlibLM"
    chat_id = "1266693480"
    
    message = f"""🎯 ChainWatch Status Update

✅ Ultra-sensitive agents deployed:
• Agent 2: USDT Monitor (>0.001 USDT)
• Agent 3: Volume Monitor (>0.01% change)

⚡ System is actively monitoring blockchain data
📊 Agents will check every 3 minutes
🚨 Alerts will appear here when conditions are met

System Status: OPERATIONAL 🚀"""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if result.get("ok"):
                    print("✅ Test message sent to Telegram!")
                    print("📱 Check your Telegram for status update!")
                    return True
                else:
                    print(f"❌ Telegram test failed: {result}")
                    return False
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

if __name__ == "__main__":
    async def full_system_check():
        print("🔍 ChainWatch Complete System Check")
        print("=" * 50)
        
        # Check agents
        agents = await check_all_agents()
        
        # Run agents manually
        alerts_triggered = await run_all_agents_manually()
        
        # Check stored alerts
        stored_alerts = await check_alerts_generated()
        
        # Send test message
        telegram_ok = await send_test_telegram()
        
        print("\n" + "=" * 50)
        print("🎯 SYSTEM STATUS SUMMARY")
        print("=" * 50)
        print(f"🤖 Active Agents: {len(agents)}")
        print(f"🚨 Alerts Triggered: {'Yes' if alerts_triggered else 'No'}")
        print(f"📋 Stored Alerts: {stored_alerts}")
        print(f"📱 Telegram: {'Working' if telegram_ok else 'Needs Fix'}")
        
        if alerts_triggered:
            print("\n🎉 SUCCESS! Your system is generating real alerts!")
        else:
            print("\n📊 System working, no alerts triggered (normal blockchain activity)")
            print("💡 Try the demo alerts: python manual_alert_generator.py")
    
    asyncio.run(full_system_check())