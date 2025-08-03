# test_collection_agent.py - Test collection monitoring
import asyncio
import aiohttp
import json

async def test_collection_agent():
    """Test deploying a collection monitoring agent"""
    
    url = "http://localhost:8000/api/v1/agents/deploy"
    
    payload = {
        "mission_prompt": "Monitor Bored Ape Yacht Club for any volume spikes above 200% increase",
        "telegram_user_id": "test_user_123",
        "telegram_username": "test_user",
        "agent_name": "BAYC Volume Monitor", 
        "schedule_interval": 300
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("success"):
                    print("✅ Collection agent deployed successfully!")
                    print(f"Agent ID: {result['data']['agent_id']}")
                    print(f"Action Type: {result['data']['structured_plan']['action_type']}")
                    print(f"Target: {result['data']['structured_plan']['target']}")
                    print(f"Conditions: {result['data']['structured_plan']['conditions']}")
                    
                    # Test running the agent
                    agent_id = result['data']['agent_id']
                    run_url = f"http://localhost:8000/api/v1/agents/{agent_id}/run"
                    
                    async with session.post(run_url) as run_response:
                        run_result = await run_response.json()
                        
                        if run_result.get("success"):
                            print("✅ Collection agent executed successfully!")
                            alerts_count = run_result.get('data', {}).get('alerts_count', 0)
                            print(f"Alerts triggered: {alerts_count}")
                            
                            if alerts_count > 0:
                                print("🚨 ALERTS DETECTED! Check your Telegram!")
                            else:
                                print("📊 No alerts (normal activity)")
                                
                        else:
                            print(f"❌ Agent execution failed: {run_result.get('message')}")
                
                else:
                    print(f"❌ Agent deployment failed: {result}")
                    
    except Exception as e:
        print(f"❌ Test failed: {e}")

async def list_all_agents():
    """List all deployed agents"""
    url = "http://localhost:8000/api/v1/agents/"
    params = {"telegram_user_id": "test_user_123"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                result = await response.json()
                
                agents = result.get('items', [])
                print(f"\n📋 Total agents deployed: {len(agents)}")
                
                for agent in agents:
                    print(f"\n🤖 Agent {agent['id']}: {agent.get('agent_name', 'Unnamed')}")
                    print(f"   Status: {agent['status']}")
                    print(f"   Mission: {agent['mission_prompt'][:60]}...")
                    print(f"   Last Run: {agent.get('last_run_at', 'Never')}")
                    
    except Exception as e:
        print(f"❌ Failed to list agents: {e}")

async def check_alerts():
    """Check for any alerts generated"""
    url = "http://localhost:8000/api/v1/alerts/"
    params = {"telegram_user_id": "test_user_123"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                result = await response.json()
                
                alerts = result.get('items', [])
                print(f"\n🚨 Total alerts: {len(alerts)}")
                
                for alert in alerts:
                    print(f"\n🔔 Alert {alert['id']}: {alert['title']}")
                    print(f"   Severity: {alert['severity']}")
                    print(f"   Type: {alert['alert_type']}")
                    print(f"   Triggered: {alert['triggered_at']}")
                    print(f"   Sent to Telegram: {alert['sent_to_telegram']}")
                    
    except Exception as e:
        print(f"❌ Failed to check alerts: {e}")

if __name__ == "__main__":
    print("🧪 Testing Collection Monitoring Agent...")
    
    async def run_all_tests():
        await test_collection_agent()
        await list_all_agents()
        await check_alerts()
    
    asyncio.run(run_all_tests())