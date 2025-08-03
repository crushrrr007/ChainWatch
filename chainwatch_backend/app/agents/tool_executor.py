# app/agents/tool_executor.py - bitsCrunch API Integration
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import aiohttp
from app.core.config import settings, SUPPORTED_BLOCKCHAINS
from app.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class ToolExecutor:
    """Executes monitoring tasks using bitsCrunch API"""
    
    def __init__(self):
        self.base_url = settings.BITSCRUNCH_BASE_URL
        self.api_key = settings.BITSCRUNCH_API_KEY
        self.rate_limiter = RateLimiter()
        
    async def execute_plan(self, structured_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a structured monitoring plan
        
        Args:
            structured_plan: The parsed plan from mission_parser
            
        Returns:
            Dict containing the fetched data and analysis
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
        """Monitor wallet activity"""
        wallet_address = target["address"]
        chain_id = SUPPORTED_BLOCKCHAINS[blockchain]
        
        results = {
            "success": True,
            "action_type": "wallet_monitor",
            "target": target,
            "data": {},
            "alerts": []
        }
        
        # Get wallet balance and recent transactions
        try:
            # Fetch wallet token balance
            balance_data = await self._fetch_wallet_balance(wallet_address, chain_id)
            results["data"]["balance"] = balance_data
            
            # For demo purposes, we'll focus on ETH transactions
            # In production, you might want to track all token transfers
            
            # Check conditions
            for condition in conditions:
                alert = await self._check_wallet_condition(
                    condition, wallet_address, chain_id, balance_data, parameters
                )
                if alert:
                    results["alerts"].append(alert)
            
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
        """Monitor NFT collection activity"""
        contract_address = target["address"]
        chain_id = SUPPORTED_BLOCKCHAINS[blockchain]
        
        results = {
            "success": True,
            "action_type": "collection_monitor",
            "target": target,
            "data": {},
            "alerts": []
        }
        
        try:
            # Fetch collection transactions
            transactions_data = await self._fetch_collection_transactions(contract_address, chain_id)
            results["data"]["transactions"] = transactions_data
            
            # Fetch collection wash trade metrics if needed
            include_washtrade = parameters.get("include_washtrade", False)
            if include_washtrade:
                washtrade_data = await self._fetch_collection_washtrade_metrics(contract_address, chain_id)
                results["data"]["washtrade"] = washtrade_data
            
            # Check conditions
            for condition in conditions:
                alert = await self._check_collection_condition(
                    condition, contract_address, chain_id, results["data"], parameters
                )
                if alert:
                    results["alerts"].append(alert)
            
            return results
            
        except Exception as e:
            logger.error(f"Collection monitoring failed: {str(e)}")
            results["success"] = False
            results["error"] = str(e)
            return results
    
    async def _execute_nft_monitoring(
        self, 
        target: Dict[str, Any], 
        conditions: List[Dict[str, Any]], 
        blockchain: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monitor specific NFT activity"""
        contract_address = target["address"]
        token_id = target.get("token_id")
        chain_id = SUPPORTED_BLOCKCHAINS[blockchain]
        
        results = {
            "success": True,
            "action_type": "nft_monitor",
            "target": target,
            "data": {},
            "alerts": []
        }
        
        try:
            if token_id:
                # Monitor specific NFT
                nft_data = await self._fetch_nft_transactions(contract_address, token_id, chain_id)
                price_data = await self._fetch_nft_price_estimate(contract_address, token_id, chain_id)
                
                results["data"]["transactions"] = nft_data
                results["data"]["price_estimate"] = price_data
            else:
                # Monitor all NFTs in collection (same as collection monitoring)
                return await self._execute_collection_monitoring(target, conditions, blockchain, parameters)
            
            # Check conditions
            for condition in conditions:
                alert = await self._check_nft_condition(
                    condition, contract_address, token_id, chain_id, results["data"], parameters
                )
                if alert:
                    results["alerts"].append(alert)
            
            return results
            
        except Exception as e:
            logger.error(f"NFT monitoring failed: {str(e)}")
            results["success"] = False
            results["error"] = str(e)
            return results
    
    # API Methods
    async def _fetch_wallet_balance(self, wallet_address: str, chain_id: int) -> Dict[str, Any]:
        """Fetch wallet token balance from bitsCrunch API"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/wallet/{wallet_address}/balance/token"
        params = {"blockchain": chain_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"x-api-key": self.api_key, "accept": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
    
    async def _fetch_collection_transactions(self, contract_address: str, chain_id: int) -> Dict[str, Any]:
        """Fetch collection transactions from bitsCrunch API"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/collection/{chain_id}/{contract_address}/transactions"
        params = {
            "sort_by": "timestamp",
            "sort_order": "desc",
            "limit": 50,
            "include_washtrade": "true"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"x-api-key": self.api_key, "accept": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
    
    async def _fetch_collection_washtrade_metrics(self, contract_address: str, chain_id: int) -> Dict[str, Any]:
        """Fetch wash trade metrics for collection"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/collection/{chain_id}/{contract_address}/trend"
        params = {
            "currency": "usd",
            "metrics": "washtrade_wallets,washtrade_assets,washtrade_suspect_sales,washtrade_volume",
            "time_range": "24h",
            "include_washtrade": "true"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"x-api-key": self.api_key, "accept": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
    
    async def _fetch_nft_transactions(self, contract_address: str, token_id: str, chain_id: int) -> Dict[str, Any]:
        """Fetch specific NFT transactions"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/nft/{chain_id}/{contract_address}/{token_id}/transactions"
        params = {
            "sort_by": "timestamp",
            "sort_order": "desc",
            "limit": 20
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"x-api-key": self.api_key, "accept": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
    
    async def _fetch_nft_price_estimate(self, contract_address: str, token_id: str, chain_id: int) -> Dict[str, Any]:
        """Fetch NFT price estimate"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/nft/{chain_id}/{contract_address}/{token_id}/price-estimate"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"x-api-key": self.api_key, "accept": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
    
    # Condition Checking Methods
    async def _check_wallet_condition(
        self, 
        condition: Dict[str, Any], 
        wallet_address: str, 
        chain_id: int, 
        balance_data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if wallet condition is triggered"""
        
        condition_type = condition["type"]
        parameter = condition["parameter"]
        operator = condition["operator"]
        value = condition["value"]
        
        # For demo, we'll implement a simple balance threshold check
        if parameter == "outgoing_transfer" and condition_type == "threshold":
            # This is a simplified demo implementation
            # In production, you'd track transaction history and detect new transfers
            
            # Mock alert for demo purposes (replace with real logic)
            if operator == "gt":
                # Simulate detecting a large transfer
                mock_detected_transfer = 7.5  # ETH
                threshold = float(value)
                
                if mock_detected_transfer > threshold:
                    return {
                        "type": "wallet_threshold_exceeded",
                        "message": f"Wallet {wallet_address} sent {mock_detected_transfer} ETH (threshold: {threshold} ETH)",
                        "severity": "high",
                        "details": {
                            "wallet_address": wallet_address,
                            "amount": mock_detected_transfer,
                            "threshold": threshold,
                            "currency": "ETH"
                        }
                    }
        
        return None
    
    async def _check_collection_condition(
        self, 
        condition: Dict[str, Any], 
        contract_address: str, 
        chain_id: int, 
        data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if collection condition is triggered"""
        
        condition_type = condition["type"]
        parameter = condition["parameter"]
        operator = condition["operator"]
        value = condition["value"]
        
        # Check wash trade detection
        if parameter == "washtrade_activity" and condition_type == "detection":
            washtrade_data = data.get("washtrade")
            if washtrade_data and "data_points" in washtrade_data:
                # Check recent wash trade volume
                recent_points = washtrade_data["data_points"][:5]  # Last 5 data points
                
                for point in recent_points:
                    washtrade_volume = point.get("values", {}).get("washtrade_volume", 0)
                    total_volume = point.get("values", {}).get("volume", 1)
                    
                    if total_volume > 0:
                        washtrade_ratio = washtrade_volume / total_volume
                        threshold = float(value)
                        
                        if washtrade_ratio > threshold:
                            return {
                                "type": "wash_trade_detected",
                                "message": f"Wash trading detected in collection (ratio: {washtrade_ratio:.2%})",
                                "severity": "high",
                                "details": {
                                    "contract_address": contract_address,
                                    "washtrade_ratio": washtrade_ratio,
                                    "threshold": threshold,
                                    "washtrade_volume": washtrade_volume,
                                    "total_volume": total_volume
                                }
                            }
        
        # Check sale price threshold
        elif parameter == "sale_price" and condition_type == "threshold":
            transactions = data.get("transactions", {}).get("transactions", [])
            threshold = float(value)
            
            for tx in transactions[:10]:  # Check recent transactions
                if tx.get("transaction_type") == "sale":
                    price_eth = tx.get("price_eth", 0)
                    
                    if operator == "lt" and price_eth > 0 and price_eth < threshold:
                        return {
                            "type": "price_alert",
                            "message": f"Sale below threshold: {price_eth} ETH (threshold: {threshold} ETH)",
                            "severity": "medium",
                            "details": {
                                "contract_address": contract_address,
                                "token_id": tx.get("token_id"),
                                "sale_price": price_eth,
                                "threshold": threshold,
                                "transaction_hash": tx.get("transaction_hash")
                            }
                        }
        
        return None
    
    async def _check_nft_condition(
        self, 
        condition: Dict[str, Any], 
        contract_address: str, 
        token_id: str, 
        chain_id: int, 
        data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if NFT condition is triggered"""
        
        # Similar logic to collection monitoring but for specific NFT
        # Implementation would be similar to _check_collection_condition
        # but focused on the specific token_id
        
        return None