# app/agents/tool_executor.py - bitsCrunch v2 Metrics API Integration
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import aiohttp
from app.core.config import settings, SUPPORTED_BLOCKCHAINS
from app.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class ToolExecutor:
    """Executes monitoring tasks using bitsCrunch v2 Metrics API"""
    
    def __init__(self):
        self.base_url = "https://api.unleashnfts.com/api/v2"  # Updated to v2
        self.api_key = settings.BITSCRUNCH_API_KEY
        self.rate_limiter = RateLimiter()
        
    async def execute_plan(self, structured_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a structured monitoring plan with REAL bitsCrunch v2 data
        
        Args:
            structured_plan: The parsed plan from mission_parser
            
        Returns:
            Dict containing the fetched data and alerts
        """
        try:
            action_type = structured_plan["action_type"]
            target = structured_plan["target"]
            conditions = structured_plan["conditions"]
            blockchain = structured_plan["blockchain"]
            parameters = structured_plan.get("parameters", {})
            
            # Route to appropriate executor
            if action_type == "wallet_monitor":
                return await self._execute_wallet_monitoring(target, conditions, blockchain, parameters)
            elif action_type == "collection_monitor":
                return await self._execute_collection_monitoring(target, conditions, blockchain, parameters)
            elif action_type == "nft_monitor":
                return await self._execute_nft_monitoring(target, conditions, blockchain, parameters)
            else:
                raise ValueError(f"Unsupported action type: {action_type}")
                
        except Exception as e:
            logger.error(f"Plan execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def _execute_wallet_monitoring(
        self, 
        target: Dict[str, Any], 
        conditions: List[Dict[str, Any]], 
        blockchain: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monitor wallet activity using bitsCrunch v2 Metrics API"""
        wallet_address = target["address"]
        
        results = {
            "success": True,
            "action_type": "wallet_monitor",
            "target": target,
            "data": {},
            "alerts": []
        }
        
        try:
            # Get REAL wallet metrics from bitsCrunch v2
            current_metrics = await self._fetch_wallet_metrics(wallet_address, blockchain)
            results["data"]["current_metrics"] = current_metrics
            
            # Get stored previous metrics from database (for comparison)
            previous_metrics = await self._get_previous_metrics(wallet_address)
            results["data"]["previous_metrics"] = previous_metrics
            
            # Check conditions against REAL data changes
            for condition in conditions:
                alert = await self._check_wallet_condition_metrics(
                    condition, wallet_address, current_metrics, previous_metrics, parameters
                )
                if alert:
                    results["alerts"].append(alert)
            
            # Store current metrics for next comparison
            await self._store_current_metrics(wallet_address, current_metrics)
            
            return results
            
        except Exception as e:
            logger.error(f"Wallet monitoring failed: {str(e)}")
            results["success"] = False
            results["error"] = str(e)
            return results
    
    async def _execute_collection_monitoring(
        self, 
        target: Dict[str, Any], 
        conditions: List[Dict[str, Any]], 
        blockchain: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monitor NFT collection activity - placeholder for now"""
        results = {
            "success": True,
            "action_type": "collection_monitor",
            "target": target,
            "data": {"message": "Collection monitoring not yet implemented with v2 API"},
            "alerts": []
        }
        return results
    
    async def _execute_nft_monitoring(
        self, 
        target: Dict[str, Any], 
        conditions: List[Dict[str, Any]], 
        blockchain: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monitor specific NFT activity - placeholder for now"""
        results = {
            "success": True,
            "action_type": "nft_monitor", 
            "target": target,
            "data": {"message": "NFT monitoring not yet implemented with v2 API"},
            "alerts": []
        }
        return results
    
    # bitsCrunch v2 API Methods
    async def _fetch_wallet_metrics(self, wallet_address: str, blockchain: str) -> Dict[str, Any]:
        """Fetch REAL wallet metrics from bitsCrunch v2 API"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/wallet/metrics"
        params = {
            "blockchain": blockchain,
            "wallet": wallet_address,
            "time_range": "all",  # Get all-time metrics
            "offset": 0,
            "limit": 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"x-api-key": self.api_key, "accept": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Return the first wallet data
                    if data.get("data") and len(data["data"]) > 0:
                        return data["data"][0]
                    else:
                        raise Exception("No wallet data returned")
                else:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
    
    # Metrics Storage and Comparison Methods
    async def _get_previous_metrics(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """Get previously stored metrics for comparison"""
        try:
            from app.core.database import AsyncSessionLocal
            from sqlalchemy import select, text
            
            async with AsyncSessionLocal() as db:
                # Query for stored metrics (we'll use a simple approach for now)
                query = text("""
                    SELECT raw_data FROM alerts 
                    WHERE raw_data->>'wallet_address' = :wallet_address 
                    AND alert_type = 'previous_metrics'
                    ORDER BY triggered_at DESC 
                    LIMIT 1
                """)
                
                result = await db.execute(query, {"wallet_address": wallet_address})
                row = result.fetchone()
                
                if row:
                    return row[0]  # Return the JSON data
                else:
                    return None
                    
        except Exception as e:
            logger.warning(f"Could not fetch previous metrics: {e}")
            return None
    
    async def _store_current_metrics(self, wallet_address: str, metrics: Dict[str, Any]) -> None:
        """Store current metrics for next comparison"""
        try:
            from app.core.database import AsyncSessionLocal, Alert
            
            async with AsyncSessionLocal() as db:
                # Store metrics as a special "alert" type for persistence
                # This is a simple approach - in production you'd want a dedicated table
                metrics_with_address = {**metrics, "wallet_address": wallet_address}
                
                # Delete old metrics record
                delete_query = text("""
                    DELETE FROM alerts 
                    WHERE raw_data->>'wallet_address' = :wallet_address 
                    AND alert_type = 'previous_metrics'
                """)
                await db.execute(delete_query, {"wallet_address": wallet_address})
                
                # Insert new metrics record (we need a dummy agent_id)
                # In production, you'd want a proper metrics storage table
                dummy_alert = Alert(
                    agent_id=1,  # Dummy agent ID
                    title="Metrics Storage",
                    report_content="Previous metrics for comparison",
                    raw_data=metrics_with_address,
                    alert_type="previous_metrics",
                    severity="low"
                )
                
                db.add(dummy_alert)
                await db.commit()
                
        except Exception as e:
            logger.warning(f"Could not store current metrics: {e}")
    
    # REAL Condition Checking with Metrics Comparison
    async def _check_wallet_condition_metrics(
        self, 
        condition: Dict[str, Any], 
        wallet_address: str, 
        current_metrics: Dict[str, Any],
        previous_metrics: Optional[Dict[str, Any]],
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check wallet condition by comparing current vs previous metrics"""
        
        condition_type = condition["type"]
        parameter = condition["parameter"]
        operator = condition["operator"]
        value = condition["value"]
        
        if parameter == "outgoing_transfer" and condition_type == "threshold":
            threshold = float(value)
            
            # Get current outflow amount
            current_outflow = current_metrics.get("outflow_amount_eth", 0)
            
            if previous_metrics:
                # Compare with previous outflow
                previous_outflow = previous_metrics.get("outflow_amount_eth", 0)
                outflow_increase = current_outflow - previous_outflow
                
                logger.info(f"Outflow comparison: Previous={previous_outflow:.6f} ETH, Current={current_outflow:.6f} ETH, Increase={outflow_increase:.6f} ETH")
                
                # Check if outflow increased by more than threshold
                if operator == "gt" and outflow_increase > threshold:
                    # Also check transaction count increase to confirm new transaction
                    current_out_txn = current_metrics.get("out_txn", 0)
                    previous_out_txn = previous_metrics.get("out_txn", 0)
                    txn_increase = current_out_txn - previous_out_txn
                    
                    return {
                        "type": "wallet_outflow_increase",
                        "message": f"Wallet {wallet_address} outflow increased by {outflow_increase:.6f} ETH (threshold: {threshold} ETH)",
                        "severity": "high" if outflow_increase > threshold * 10 else "medium",
                        "details": {
                            "wallet_address": wallet_address,
                            "outflow_increase": outflow_increase,
                            "threshold": threshold,
                            "current_outflow": current_outflow,
                            "previous_outflow": previous_outflow,
                            "transaction_count_increase": txn_increase,
                            "current_out_txn": current_out_txn,
                            "previous_out_txn": previous_out_txn,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
            else:
                # First run - no previous data to compare
                logger.info(f"First run for wallet {wallet_address}, storing baseline metrics")
                logger.info(f"Current outflow: {current_outflow:.6f} ETH, Out transactions: {current_metrics.get('out_txn', 0)}")
                
                # For first run, we could alert if current outflow is above threshold
                # But this might give false positives for existing wallets
                return None
        
        elif parameter == "incoming_transfer" and condition_type == "threshold":
            threshold = float(value)
            
            # Get current inflow amount
            current_inflow = current_metrics.get("inflow_amount_eth", 0)
            
            if previous_metrics:
                previous_inflow = previous_metrics.get("inflow_amount_eth", 0)
                inflow_increase = current_inflow - previous_inflow
                
                logger.info(f"Inflow comparison: Previous={previous_inflow:.6f} ETH, Current={current_inflow:.6f} ETH, Increase={inflow_increase:.6f} ETH")
                
                if operator == "gt" and inflow_increase > threshold:
                    current_in_txn = current_metrics.get("in_txn", 0)
                    previous_in_txn = previous_metrics.get("in_txn", 0)
                    txn_increase = current_in_txn - previous_in_txn
                    
                    return {
                        "type": "wallet_inflow_increase",
                        "message": f"Wallet {wallet_address} inflow increased by {inflow_increase:.6f} ETH (threshold: {threshold} ETH)",
                        "severity": "medium",
                        "details": {
                            "wallet_address": wallet_address,
                            "inflow_increase": inflow_increase,
                            "threshold": threshold,
                            "current_inflow": current_inflow,
                            "previous_inflow": previous_inflow,
                            "transaction_count_increase": txn_increase,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
        
        return None
    
    # Utility method for testing
    async def test_api_connection(self, wallet_address: str = "0xaC025131C19dB776b3B288b853AF70C7f91B9796") -> Dict[str, Any]:
        """Test the bitsCrunch v2 API connection"""
        try:
            metrics = await self._fetch_wallet_metrics(wallet_address, "ethereum")
            return {
                "success": True,
                "message": "API connection successful",
                "data": metrics
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"API connection failed: {str(e)}"
            }

# Test function for development
async def test_new_tool_executor():
    """Test the updated tool executor with real wallet monitoring"""
    executor = ToolExecutor()
    
    # Test API connection first
    print("🧪 Testing bitsCrunch v2 API connection...")
    api_test = await executor.test_api_connection()
    
    if api_test["success"]:
        print("✅ API Connection successful!")
        print(f"Sample data: {api_test['data']}")
        
        # Test wallet monitoring
        print("\n🧪 Testing wallet monitoring...")
        structured_plan = {
            "action_type": "wallet_monitor",
            "target": {
                "type": "wallet",
                "address": "0xaC025131C19dB776b3B288b853AF70C7f91B9796"
            },
            "conditions": [{
                "type": "threshold",
                "parameter": "outgoing_transfer",
                "operator": "gt",
                "value": "0.0001",
                "timeframe": "24h"
            }],
            "blockchain": "ethereum",
            "parameters": {
                "currency": "eth",
                "alert_frequency": "immediate"
            }
        }
        
        result = await executor.execute_plan(structured_plan)
        
        if result["success"]:
            print("✅ Wallet monitoring test successful!")
            print(f"Alerts triggered: {len(result['alerts'])}")
            for alert in result["alerts"]:
                print(f"🚨 Alert: {alert['message']}")
        else:
            print(f"❌ Wallet monitoring test failed: {result['error']}")
    else:
        print(f"❌ API Connection failed: {api_test['message']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_new_tool_executor())