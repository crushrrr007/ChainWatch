# test_specific_agent.py - Test with specific wallet
import asyncio
import aiohttp
import json

async def test_specific_wallet_agent():
    """Test deploying a specific wallet monitoring agent"""
    
    url = "http://localhost:8000/api/v1/agents/deploy"
    
    payload = {
        "mission_prompt": "Alert me if wallet 0x742d35Cc6bf8e1d6D8aEc8967c96e5e5E2DbDcf5 sends more than 5 ETH",
        "telegram_user_id": "test_user_123",
        "telegram_username": "test_user", 
        "agent_name": "Vitalik Wallet Monitor",
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
                    print("✅ Specific wallet agent deployed successfully!")
                    print(f"Agent ID: {result['data']['agent_id']}")
                    print(f"Action Type: {result['data']['structured_plan']['action_type']}")
                    print(f"Target: {result['data']['structured_plan']['target']}")
                    
                    # Test running the agent
                    agent_id = result['data']['agent_id']
                    run_url = f"http://localhost:8000/api/v1/agents/{agent_id}/run"
                    
                    async with session.post(run_url) as run_response:
                        run_result = await run_response.json()
                        
                        if run_result.get("success"):
                            print("✅ Agent executed successfully!")
                            print(f"Execution result: {json.dumps(run_result.get('data', {}), indent=2)}")
                        else:
                            print(f"❌ Agent execution failed: {run_result.get('message')}")
                
                else:
                    print(f"❌ Agent deployment failed: {result}")
                    
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing Specific Wallet Agent...")
    asyncio.run(test_specific_wallet_agent())