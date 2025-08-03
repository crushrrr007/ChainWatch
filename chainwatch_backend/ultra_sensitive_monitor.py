# ultra_sensitive_monitor.py - Deploy agents with extremely low thresholds
import asyncio
import aiohttp

async def deploy_ultra_sensitive_agents():
    """Deploy agents with very low thresholds to trigger real alerts"""
    
    agents = [
        {
            "mission": "Alert me if any wallet sends more than 0.001 USDT",
            "name": "Ultra Sensitive USDT Monitor",
            "expected": "Will trigger on almost any USDT transfer"
        },
        {
            "mission": "Alert me if any collection has volume change above 0.01% (tiny change)",
            "name": "Micro Volume Change Monitor", 
            "expected": "Will trigger on any collection activity"
        }
    ]
    
    url = "http://localhost:8000/api/v1/agents/deploy"
    headers = {"Content-Type": "application/json"}
    
    for agent in agents:
        payload = {
            "mission_prompt": agent["mission"],
            "telegram_user_id": "1266693480",  # Your actual chat ID
            "telegram_username": "your_username",
            "agent_name": agent["name"],
            "schedule_interval": 180  # Check every 3 minutes
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("success"):
                        agent_id = result['data']['agent_id']
                        print(f"✅ Deployed: {agent['name']} (Agent {agent_id})")
                        print(f"   Expected: {agent['expected']}")
                        
                        # Run immediately
                        run_url = f"http://localhost:8000/api/v1/agents/{agent_id}/run"
                        async with session.post(run_url) as run_response:
                            run_result = await run_response.json()
                            
                            if run_result.get("success"):
                                alerts = run_result.get('data', {}).get('alerts_count', 0)
                                if alerts > 0:
                                    print(f"🚨 REAL ALERT TRIGGERED! {alerts} alerts sent to Telegram!")
                                else:
                                    print("📊 No immediate alerts, but agent is now monitoring...")
                    else:
                        print(f"❌ Failed to deploy {agent['name']}: {result}")
                        
        except Exception as e:
            print(f"❌ Error deploying {agent['name']}: {e}")
        
        await asyncio.sleep(1)

async def check_scheduler_status():
    """Check if the scheduler is running to process agents automatically"""
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/v1/agents/stats") as response:
                result = await response.json()
                
                if result.get("success"):
                    stats = result.get("data", {})
                    is_running = stats.get("is_running", False)
                    
                    if is_running:
                        print("✅ Scheduler is running - agents will check every 3 minutes")
                        print("📱 You should receive Telegram alerts when conditions are met!")
                    else:
                        print("⚠️ Scheduler not running - manually triggering agents")
                        
                        # Manually run all agents
                        async with session.get("http://localhost:8000/api/v1/agents/?telegram_user_id=1266693480") as agents_response:
                            agents_result = await agents_response.json()
                            agents = agents_result.get("items", [])
                            
                            for agent in agents:
                                agent_id = agent["id"]
                                run_url = f"http://localhost:8000/api/v1/agents/{agent_id}/run"
                                
                                async with session.post(run_url) as run_response:
                                    run_result = await run_response.json()
                                    
                                    if run_result.get("success"):
                                        alerts = run_result.get('data', {}).get('alerts_count', 0)
                                        if alerts > 0:
                                            print(f"🚨 Agent {agent_id} triggered {alerts} alerts!")
                                    
                else:
                    print("❌ Could not check scheduler status")
                    
    except Exception as e:
        print(f"❌ Error checking scheduler: {e}")

if __name__ == "__main__":
    async def setup_real_monitoring():
        print("⚡ Setting up Real Alert Monitoring")
        print("=" * 50)
        
        await deploy_ultra_sensitive_agents()
        print("\n" + "=" * 30)
        await check_scheduler_status()
        
        print("\n🎯 Real monitoring setup complete!")
        print("📱 Your Telegram will receive alerts when blockchain activity matches conditions")
        print("⏰ Agents check every 3 minutes automatically")
    
    asyncio.run(setup_real_monitoring())