# demo_setup.py - Demo Setup and Testing Script
import asyncio
import aiohttp
import json
from datetime import datetime

# Demo configuration
BASE_URL = "http://localhost:8000"
DEMO_TELEGRAM_USER_ID = "demo_user_123"
DEMO_TELEGRAM_USERNAME = "demo_user"

class ChainWatchDemo:
    """Demo helper for testing ChainWatch backend"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self):
        """Check if the API is healthy"""
        print("🔍 Checking API health...")
        
        async with self.session.get(f"{self.base_url}/api/v1/health") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ API Status: {data['status']}")
                
                print("\n📊 Service Status:")
                for service, status in data['services'].items():
                    emoji = "✅" if "healthy" in status else "⚠️" if "degraded" in status else "❌"
                    print(f"  {emoji} {service}: {status}")
                
                return data['status'] == "healthy"
            else:
                print(f"❌ Health check failed: HTTP {response.status}")
                return False
    
    async def test_telegram(self, chat_id: str):
        """Test Telegram integration"""
        print(f"📱 Testing Telegram integration with chat ID: {chat_id}")
        
        payload = {
            "chat_id": chat_id,
            "message": "🤖 ChainWatch Demo Test - System is operational!"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/test/telegram", 
            json=payload
        ) as response:
            data = await response.json()
            
            if data['success']:
                print("✅ Telegram test message sent successfully!")
                return True
            else:
                print(f"❌ Telegram test failed: {data.get('message')}")
                return False
    
    async def deploy_demo_agent(self, mission: str):
        """Deploy a demo agent"""
        print(f"🚀 Deploying demo agent...")
        print(f"Mission: {mission}")
        
        payload = {
            "mission_prompt": mission,
            "telegram_user_id": DEMO_TELEGRAM_USER_ID,
            "telegram_username": DEMO_TELEGRAM_USERNAME,
            "agent_name": f"Demo Agent - {datetime.now().strftime('%H:%M:%S')}",
            "schedule_interval": 300
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/agents/deploy",
            json=payload
        ) as response:
            data = await response.json()
            
            if data['success']:
                agent_id = data['data']['agent_id']
                print(f"✅ Agent deployed successfully! ID: {agent_id}")
                
                # Show the structured plan
                plan = data['data']['structured_plan']
                print(f"\n📋 Generated Plan:")
                print(f"  Action Type: {plan['action_type']}")
                print(f"  Target: {plan['target']}")
                print(f"  Blockchain: {plan['blockchain']}")
                print(f"  Conditions: {len(plan['conditions'])} condition(s)")
                
                return agent_id
            else:
                print(f"❌ Agent deployment failed: {data.get('message')}")
                return None
    
    async def run_agent_manually(self, agent_id: int):
        """Manually trigger an agent"""
        print(f"⚡ Manually running agent {agent_id}...")
        
        async with self.session.post(
            f"{self.base_url}/api/v1/agents/{agent_id}/run"
        ) as response:
            data = await response.json()
            
            if data['success']:
                print("✅ Agent executed successfully!")
                if 'data' in data and 'alerts_count' in data['data']:
                    alerts_count = data['data']['alerts_count']
                    print(f"🚨 Alerts triggered: {alerts_count}")
                return True
            else:
                print(f"❌ Agent execution failed: {data.get('message')}")
                return False
    
    async def list_agents(self):
        """List all agents"""
        print("📋 Listing agents...")
        
        params = {"telegram_user_id": DEMO_TELEGRAM_USER_ID}
        
        async with self.session.get(
            f"{self.base_url}/api/v1/agents/",
            params=params
        ) as response:
            data = await response.json()
            
            agents = data.get('items', [])
            print(f"Found {len(agents)} agent(s)")
            
            for agent in agents:
                print(f"\n🤖 Agent ID: {agent['id']}")
                print(f"   Name: {agent.get('agent_name', 'Unnamed')}")
                print(f"   Status: {agent['status']}")
                print(f"   Mission: {agent['mission_prompt'][:60]}...")
                print(f"   Last Run: {agent.get('last_run_at', 'Never')}")
            
            return agents
    
    async def list_alerts(self):
        """List all alerts"""
        print("🚨 Listing alerts...")
        
        params = {"telegram_user_id": DEMO_TELEGRAM_USER_ID}
        
        async with self.session.get(
            f"{self.base_url}/api/v1/alerts/",
            params=params
        ) as response:
            data = await response.json()
            
            alerts = data.get('items', [])
            print(f"Found {len(alerts)} alert(s)")
            
            for alert in alerts:
                print(f"\n🚨 Alert ID: {alert['id']}")
                print(f"   Title: {alert['title']}")
                print(f"   Severity: {alert['severity']}")
                print(f"   Type: {alert['alert_type']}")
                print(f"   Triggered: {alert['triggered_at']}")
                print(f"   Sent to Telegram: {alert['sent_to_telegram']}")
            
            return alerts
    
    async def get_demo_missions(self):
        """Get example missions"""
        async with self.session.get(f"{self.base_url}/api/v1/agents/demo/missions") as response:
            data = await response.json()
            return data

async def run_full_demo():
    """Run a complete demo of the ChainWatch system"""
    print("🚀 Starting ChainWatch Demo")
    print("=" * 60)
    
    async with ChainWatchDemo() as demo:
        # Step 1: Health check
        if not await demo.health_check():
            print("❌ API is not healthy. Please check your setup.")
            return
        
        print("\n" + "=" * 60)
        
        # Step 2: Test Telegram (if configured)
        telegram_chat_id = input("Enter your Telegram chat ID (or press Enter to skip): ").strip()
        if telegram_chat_id:
            await demo.test_telegram(telegram_chat_id)
        else:
            print("⏭️ Skipping Telegram test")
        
        print("\n" + "=" * 60)
        
        # Step 3: Get demo missions
        missions_data = await demo.get_demo_missions()
        wallet_missions = missions_data.get('wallet_monitoring', [])
        nft_missions = missions_data.get('nft_monitoring', [])
        
        print("📝 Available Demo Missions:")
        all_missions = wallet_missions + nft_missions[:2]  # Limit for demo
        
        for i, mission in enumerate(all_missions, 1):
            print(f"  {i}. {mission}")
        
        print("\n" + "=" * 60)
        
        # Step 4: Deploy a demo agent
        demo_mission = wallet_missions[0]  # Use first wallet monitoring mission
        agent_id = await demo.deploy_demo_agent(demo_mission)
        
        if not agent_id:
            print("❌ Could not deploy demo agent")
            return
        
        print("\n" + "=" * 60)
        
        # Step 5: Run the agent manually to trigger demo alerts
        await demo.run_agent_manually(agent_id)
        
        print("\n" + "=" * 60)
        
        # Step 6: List agents and alerts
        await demo.list_agents()
        
        print("\n" + "=" * 60)
        
        await demo.list_alerts()
        
        print("\n" + "=" * 60)
        print("✅ Demo completed successfully!")
        print("\nNext steps:")
        print("1. Check your Telegram for alert messages (if configured)")
        print("2. Explore the API endpoints at http://localhost:8000/docs")
        print("3. Build the frontend to interact with these APIs")

async def quick_test():
    """Quick API test"""
    async with ChainWatchDemo() as demo:
        await demo.health_check()

if __name__ == "__main__":
    print("ChainWatch Backend Demo")
    print("Choose an option:")
    print("1. Quick health check")
    print("2. Full demo")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(quick_test())
    elif choice == "2":
        asyncio.run(run_full_demo())
    else:
        print("Invalid choice")