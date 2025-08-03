# app/agents/tool_executor.py - Updated with Correct API Integration
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
        """Execute a structured monitoring plan"""
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
        """Monitor wallet activity using Token APIs"""
        wallet_address = target["address"]
        
        results = {
            "success": True,
            "action_type": "wallet_monitor",
            "target": target,
            "data": {},
            "alerts": []
        }
        
        try:
            # Monitor common tokens (ETH, USDT, USDC)
            common_tokens = {
                "ETH": "0x0000000000000000000000000000000000000000",  # ETH
                "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7", # USDT
                "USDC": "0xA0b86a33E6417C97Ed7e91b88b7c05Ef85b6CD7b"  # USDC
            }
            
            # Get transfers for each token
            for token_name, token_address in common_tokens.items():
                try:
                    transfers_data = await self._fetch_token_transfers(
                        token_address, blockchain, wallet_address
                    )
                    results["data"][f"{token_name}_transfers"] = transfers_data
                except Exception as e:
                    logger.warning(f"Failed to fetch {token_name} transfers: {e}")
                    results["data"][f"{token_name}_transfers"] = {"data": [], "error": str(e)}
            
            # Get wallet token balance
            try:
                balance_data = await self._fetch_token_balance(wallet_address, blockchain)
                results["data"]["balance"] = balance_data
            except Exception as e:
                logger.warning(f"Failed to fetch wallet balance: {e}")
                results["data"]["balance"] = {"error": str(e)}
            
            # Check conditions
            for condition in conditions:
                alert = await self._check_wallet_condition(
                    condition, wallet_address, blockchain, results["data"], parameters
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
        
        results = {
            "success": True,
            "action_type": "collection_monitor",
            "target": target,
            "data": {},
            "alerts": []
        }
        
        try:
            # Fetch collection analytics (volume, sales, transactions)
            analytics_data = await self._fetch_collection_analytics(contract_address, blockchain)
            results["data"]["analytics"] = analytics_data
            
            # Fetch wash trade metrics if needed
            include_washtrade = parameters.get("include_washtrade", False)
            if include_washtrade:
                washtrade_data = await self._fetch_collection_washtrade(contract_address, blockchain)
                results["data"]["washtrade"] = washtrade_data
            
            # Fetch whale activity if needed
            include_whales = parameters.get("include_whales", False)
            if include_whales:
                whale_data = await self._fetch_collection_whales(contract_address, blockchain)
                results["data"]["whales"] = whale_data
            
            # Check conditions
            for condition in conditions:
                alert = await self._check_collection_condition(
                    condition, contract_address, blockchain, results["data"], parameters
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
                nft_data = await self._fetch_nft_transactions(contract_address, token_id, blockchain)
                price_data = await self._fetch_nft_price_estimate(contract_address, token_id, blockchain)
                
                results["data"]["transactions"] = nft_data
                results["data"]["price_estimate"] = price_data
            else:
                # Monitor all NFTs in collection (same as collection monitoring)
                return await self._execute_collection_monitoring(target, conditions, blockchain, parameters)
            
            # Check conditions
            for condition in conditions:
                alert = await self._check_nft_condition(
                    condition, contract_address, token_id, blockchain, results["data"], parameters
                )
                if alert:
                    results["alerts"].append(alert)
            
            return results
            
        except Exception as e:
            logger.error(f"NFT monitoring failed: {str(e)}")
            results["success"] = False
            results["error"] = str(e)
            return results
    
    # NEW API METHODS
    async def _fetch_token_transfers(self, token_address: str, blockchain: str, wallet_filter: str = None) -> Dict[str, Any]:
        """Fetch token transfers for wallet monitoring"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/token/transfers"
        params = {
            "token_address": token_address,
            "blockchain": blockchain,
            "time_range": "1h",  # Last hour
            "limit": 100
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"x-api-key": self.api_key, "accept": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Filter transfers for specific wallet if provided
                    if wallet_filter:
                        filtered_transfers = []
                        for transfer in data.get("data", []):
                            if (transfer.get("sender", "").lower() == wallet_filter.lower() or 
                                transfer.get("receiver", "").lower() == wallet_filter.lower()):
                                filtered_transfers.append(transfer)
                        data["data"] = filtered_transfers
                        data["filtered_for_wallet"] = wallet_filter
                    
                    return data
                else:
                    error_text = await response.text()
                    raise Exception(f"Token Transfers API Error {response.status}: {error_text}")
    
    async def _fetch_token_balance(self, wallet_address: str, blockchain: str) -> Dict[str, Any]:
        """Fetch token balance for a wallet"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/token/balance"
        params = {
            "address": wallet_address,
            "blockchain": blockchain
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
                    raise Exception(f"Token Balance API Error {response.status}: {error_text}")
    
    async def _fetch_collection_analytics(self, contract_address: str, blockchain: str) -> Dict[str, Any]:
        """Fetch collection analytics (CORRECTED VERSION)"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/nft/collection/analytics"
        params = {
            "blockchain": blockchain,
            "contract_address": contract_address,
            "time_range": "24h",
            "sort_by": "volume",
            "sort_order": "desc",
            "limit": 10
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
                    raise Exception(f"Collection Analytics API Error {response.status}: {error_text}")
    
    async def _fetch_collection_washtrade(self, contract_address: str, blockchain: str) -> Dict[str, Any]:
        """Fetch collection wash trade metrics (FIXED)"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/nft/collection/washtrade"
        params = {
            "blockchain": blockchain,
            "contract_address": contract_address,
            "time_range": "24h",
            "sort_by": "washtrade_score",  # Add required sort_by parameter
            "sort_order": "desc",
            "limit": 10
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
                    raise Exception(f"Collection Washtrade API Error {response.status}: {error_text}")
    
    async def _fetch_collection_whales(self, contract_address: str, blockchain: str) -> Dict[str, Any]:
        """Fetch collection whale activity"""
        await self.rate_limiter.acquire("bitscrunch")
        
        url = f"{self.base_url}/nft/collection/whales"
        params = {
            "blockchain": blockchain,
            "contract_address": contract_address,
            "time_range": "24h"
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
                    raise Exception(f"Collection Whales API Error {response.status}: {error_text}")
    
    async def _fetch_nft_transactions(self, contract_address: str, token_id: str, blockchain: str) -> Dict[str, Any]:
        """Fetch specific NFT transactions"""
        await self.rate_limiter.acquire("bitscrunch")
        
        chain_id = SUPPORTED_BLOCKCHAINS[blockchain]
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
                    raise Exception(f"NFT Transactions API Error {response.status}: {error_text}")
    
    async def _fetch_nft_price_estimate(self, contract_address: str, token_id: str, blockchain: str) -> Dict[str, Any]:
        """Fetch NFT price estimate"""
        await self.rate_limiter.acquire("bitscrunch")
        
        chain_id = SUPPORTED_BLOCKCHAINS[blockchain]
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
                    raise Exception(f"NFT Price Estimate API Error {response.status}: {error_text}")
    
    # UPDATED CONDITION CHECKING METHODS
    async def _check_wallet_condition(
        self, 
        condition: Dict[str, Any], 
        wallet_address: str, 
        blockchain: str, 
        data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if wallet condition is triggered (UPDATED WITH CORRECT API STRUCTURE)"""
        
        condition_type = condition["type"]
        parameter = condition["parameter"]
        operator = condition["operator"]
        value = condition["value"]
        
        # Check for large outgoing transfers across all monitored tokens
        if parameter == "outgoing_transfer" and condition_type == "threshold":
            threshold = float(value)
            
            # Check transfers for each token
            token_names = ["ETH", "USDT", "USDC"]
            
            for token_name in token_names:
                transfers_data = data.get(f"{token_name}_transfers", {}).get("data", [])
                
                for transfer in transfers_data:
                    # Check if this wallet is the sender
                    if transfer.get("sender", "").lower() == wallet_address.lower():
                        amount = float(transfer.get("value_native", 0))
                        
                        # Convert threshold based on token (for demo, treat all as 1:1)
                        # In production, you'd want proper token conversion
                        if operator == "gt" and amount > threshold:
                            return {
                                "type": "wallet_threshold_exceeded",
                                "message": f"Wallet sent {amount} {token_name} (threshold: {threshold})",
                                "severity": "high" if amount > threshold * 2 else "medium",
                                "details": {
                                    "wallet_address": wallet_address,
                                    "amount": amount,
                                    "threshold": threshold,
                                    "token": token_name,
                                    "token_address": transfer.get("token_address"),
                                    "to_address": transfer.get("receiver"),
                                    "transaction_hash": transfer.get("transaction_hash"),
                                    "timestamp": transfer.get("timestamp")
                                }
                            }
        
        # Check for large incoming transfers
        elif parameter == "incoming_transfer" and condition_type == "threshold":
            threshold = float(value)
            
            token_names = ["ETH", "USDT", "USDC"]
            
            for token_name in token_names:
                transfers_data = data.get(f"{token_name}_transfers", {}).get("data", [])
                
                for transfer in transfers_data:
                    # Check if this wallet is the receiver
                    if transfer.get("receiver", "").lower() == wallet_address.lower():
                        amount = float(transfer.get("value_native", 0))
                        
                        if operator == "gt" and amount > threshold:
                            return {
                                "type": "wallet_large_incoming",
                                "message": f"Wallet received {amount} {token_name} (threshold: {threshold})",
                                "severity": "medium",
                                "details": {
                                    "wallet_address": wallet_address,
                                    "amount": amount,
                                    "threshold": threshold,
                                    "token": token_name,
                                    "token_address": transfer.get("token_address"),
                                    "from_address": transfer.get("sender"),
                                    "transaction_hash": transfer.get("transaction_hash"),
                                    "timestamp": transfer.get("timestamp")
                                }
                            }
        
        return None
    
    async def _check_collection_condition(
        self, 
        condition: Dict[str, Any], 
        contract_address: str, 
        blockchain: str, 
        data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if collection condition is triggered (FIXED VERSION)"""
        
        condition_type = condition["type"]
        parameter = condition["parameter"]
        operator = condition["operator"]
        value = condition["value"]
        
        # Check volume spike detection
        if parameter == "volume_spike" and condition_type == "threshold":
            analytics_data = data.get("analytics", {}).get("data", [])
            threshold = float(value)
            
            for collection_data in analytics_data:
                if collection_data.get("contract_address", "").lower() == contract_address.lower():
                    volume_change = collection_data.get("volume_change", 0)
                    
                    if operator == "gt" and volume_change > threshold:
                        return {
                            "type": "volume_spike_detected",
                            "message": f"Volume spike detected: {volume_change:.2f}x increase (threshold: {threshold}x)",
                            "severity": "medium",
                            "details": {
                                "contract_address": contract_address,
                                "volume_change": volume_change,
                                "threshold": threshold,
                                "current_volume": collection_data.get("volume", 0),
                                "sales_count": collection_data.get("sales", 0)
                            }
                        }
        
        # Check wash trade detection
        elif parameter == "washtrade_activity" and condition_type == "detection":
            washtrade_data = data.get("washtrade", {}).get("data", [])
            threshold = float(value)
            
            for washtrade_info in washtrade_data:
                if washtrade_info.get("contract_address", "").lower() == contract_address.lower():
                    # Calculate wash trade ratio (this depends on the actual washtrade API structure)
                    washtrade_volume = washtrade_info.get("washtrade_volume", 0)
                    total_volume = washtrade_info.get("total_volume", 1)
                    
                    if total_volume > 0:
                        washtrade_ratio = washtrade_volume / total_volume
                        
                        if washtrade_ratio > threshold:
                            return {
                                "type": "wash_trade_detected",
                                "message": f"Wash trading detected: {washtrade_ratio:.2%} of volume (threshold: {threshold:.2%})",
                                "severity": "high",
                                "details": {
                                    "contract_address": contract_address,
                                    "washtrade_ratio": washtrade_ratio,
                                    "threshold": threshold,
                                    "washtrade_volume": washtrade_volume,
                                    "total_volume": total_volume
                                }
                            }
        
        # Check sales price threshold
        elif parameter == "sale_price" and condition_type == "threshold":
            analytics_data = data.get("analytics", {}).get("data", [])
            threshold = float(value)
            
            for collection_data in analytics_data:
                if collection_data.get("contract_address", "").lower() == contract_address.lower():
                    # This would need to be combined with actual transaction data to get individual sale prices
                    # For now, we can alert on average volume per sale
                    volume = collection_data.get("volume", 0)
                    sales = collection_data.get("sales", 1)
                    avg_sale_price = volume / sales if sales > 0 else 0
                    
                    if operator == "lt" and avg_sale_price > 0 and avg_sale_price < threshold:
                        return {
                            "type": "price_alert",
                            "message": f"Average sale price below threshold: {avg_sale_price:.2f} (threshold: {threshold})",
                            "severity": "medium",
                            "details": {
                                "contract_address": contract_address,
                                "avg_sale_price": avg_sale_price,
                                "threshold": threshold,
                                "total_volume": volume,
                                "sales_count": sales
                            }
                        }
        
        return None
    
    async def _check_nft_condition(
        self, 
        condition: Dict[str, Any], 
        contract_address: str, 
        token_id: str, 
        blockchain: str, 
        data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if NFT condition is triggered"""
        
        condition_type = condition["type"]
        parameter = condition["parameter"]
        operator = condition["operator"]
        value = condition["value"]
        
        # Check NFT price changes
        if parameter == "price_change" and condition_type == "threshold":
            price_data = data.get("price_estimate", {})
            threshold = float(value)
            
            current_price = price_data.get("estimated_price", 0)
            # You would need historical price to calculate change
            # For now, we can alert if price is above/below threshold
            
            if operator == "gt" and current_price > threshold:
                return {
                    "type": "nft_price_alert",
                    "message": f"NFT price above threshold: {current_price} > {threshold}",
                    "severity": "medium",
                    "details": {
                        "contract_address": contract_address,
                        "token_id": token_id,
                        "current_price": current_price,
                        "threshold": threshold
                    }
                }
        
        return None