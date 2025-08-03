# app/agents/mission_parser.py - AI-Powered Mission Parser
import json
import logging
import re
from typing import Dict, Any, Optional
import google.generativeai as genai
from app.core.config import settings, SUPPORTED_BLOCKCHAINS
from app.models.schemas import AgentStructuredPlan, MissionParseResponse

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

class MissionParser:
    """Converts natural language missions into structured monitoring plans"""
    
    def __init__(self):
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
    async def parse_mission(self, mission_prompt: str, context: Optional[Dict[str, Any]] = None) -> MissionParseResponse:
        """
        Parse natural language mission into structured plan
        
        Args:
            mission_prompt: User's natural language mission
            context: Optional context (user preferences, etc.)
        
        Returns:
            MissionParseResponse with structured plan or error
        """
        try:
            logger.info(f"Parsing mission: {mission_prompt[:100]}...")
            
            # Create the prompt
            prompt = self._build_parsing_prompt(mission_prompt, context)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            # Extract and validate JSON
            structured_plan = self._extract_json_from_response(response.text)
            
            if not structured_plan:
                return MissionParseResponse(
                    success=False,
                    error="Failed to generate valid structured plan"
                )
            
            # Validate the plan
            validation_result = self._validate_plan(structured_plan)
            if not validation_result["valid"]:
                return MissionParseResponse(
                    success=False,
                    error=f"Invalid plan: {validation_result['error']}"
                )
            
            # Convert to Pydantic model
            plan_model = AgentStructuredPlan(**structured_plan)
            
            return MissionParseResponse(
                success=True,
                structured_plan=plan_model,
                confidence=0.85  # Could be improved with confidence scoring
            )
            
        except Exception as e:
            logger.error(f"Mission parsing failed: {str(e)}")
            return MissionParseResponse(
                success=False,
                error=f"Parsing error: {str(e)}"
            )
    
    def _build_parsing_prompt(self, mission_prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the prompt for Gemini to parse the mission"""
        
        prompt = f"""
You are an expert blockchain monitoring system. Convert the user's natural language mission into a structured JSON plan.

SUPPORTED BLOCKCHAINS: {list(SUPPORTED_BLOCKCHAINS.keys())}
SUPPORTED ACTION TYPES: wallet_monitor, nft_monitor, collection_monitor, transaction_monitor

RESPONSE FORMAT (JSON only, no other text):
{{
    "action_type": "wallet_monitor|nft_monitor|collection_monitor|transaction_monitor",
    "target": {{
        "type": "wallet|nft|collection|transaction",
        "address": "wallet_address_or_contract_address",
        "token_id": "token_id_if_specific_nft",
        "collection_name": "human_readable_collection_name"
    }},
    "conditions": [
        {{
            "type": "threshold|change|pattern|detection",
            "parameter": "volume|price|transfer|activity",
            "operator": "gt|lt|eq|contains",
            "value": "threshold_value",
            "timeframe": "1h|24h|7d|30d"
        }}
    ],
    "blockchain": "ethereum|polygon|avalanche|bsc|linea|solana",
    "parameters": {{
        "currency": "usd|eth",
        "include_washtrade": false,
        "min_value_usd": 0,
        "alert_frequency": "immediate|daily|weekly"
    }}
}}

EXAMPLES:

Mission: "Alert me if wallet 0x742d35Cc6bf8e1d6D8aEc8967c96e5e5E2DbDcf5 sends more than 5 ETH to any new address"
Response:
{{
    "action_type": "wallet_monitor",
    "target": {{
        "type": "wallet",
        "address": "0x742d35Cc6bf8e1d6D8aEc8967c96e5e5E2DbDcf5"
    }},
    "conditions": [
        {{
            "type": "threshold",
            "parameter": "outgoing_transfer",
            "operator": "gt",
            "value": "5",
            "timeframe": "24h"
        }}
    ],
    "blockchain": "ethereum",
    "parameters": {{
        "currency": "eth",
        "min_value_usd": 0,
        "alert_frequency": "immediate",
        "filter_new_addresses": true
    }}
}}

Mission: "Monitor Bored Ape Yacht Club for wash trading and alert if detected"
Response:
{{
    "action_type": "collection_monitor",
    "target": {{
        "type": "collection",
        "address": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
        "collection_name": "Bored Ape Yacht Club"
    }},
    "conditions": [
        {{
            "type": "detection",
            "parameter": "washtrade_activity",
            "operator": "gt",
            "value": "0.1",
            "timeframe": "24h"
        }}
    ],
    "blockchain": "ethereum",
    "parameters": {{
        "currency": "usd",
        "include_washtrade": true,
        "alert_frequency": "daily"
    }}
}}

Mission: "Alert me if any CryptoPunk is sold for less than 10 ETH"
Response:
{{
    "action_type": "collection_monitor",
    "target": {{
        "type": "collection",
        "address": "0xb47e3cd837dDF8e4c57F05d70Ab865de6e193BBB",
        "collection_name": "CryptoPunks"
    }},
    "conditions": [
        {{
            "type": "threshold",
            "parameter": "sale_price",
            "operator": "lt",
            "value": "10",
            "timeframe": "24h"
        }}
    ],
    "blockchain": "ethereum",
    "parameters": {{
        "currency": "eth",
        "min_value_usd": 0,
        "alert_frequency": "immediate"
    }}
}}

Now parse this mission:
Mission: "{mission_prompt}"

Respond with ONLY the JSON structure, no additional text:
"""
        return prompt
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from Gemini response, handling markdown formatting"""
        try:
            # Remove markdown code blocks
            cleaned = re.sub(r'```(?:json)?\s*', '', response_text)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            cleaned = cleaned.strip()
            
            # Try to parse JSON
            return json.loads(cleaned)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Response text: {response_text}")
            
            # Try to extract JSON from text more aggressively
            json_pattern = r'\{.*\}'
            matches = re.findall(json_pattern, cleaned, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches[0])
                except:
                    pass
            
            return None
    
    def _validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the structured plan"""
        try:
            # Required fields
            required_fields = ["action_type", "target", "conditions", "blockchain", "parameters"]
            for field in required_fields:
                if field not in plan:
                    return {"valid": False, "error": f"Missing required field: {field}"}
            
            # Validate action_type
            valid_action_types = ["wallet_monitor", "nft_monitor", "collection_monitor", "transaction_monitor"]
            if plan["action_type"] not in valid_action_types:
                return {"valid": False, "error": f"Invalid action_type: {plan['action_type']}"}
            
            # Validate blockchain
            if plan["blockchain"] not in SUPPORTED_BLOCKCHAINS:
                return {"valid": False, "error": f"Unsupported blockchain: {plan['blockchain']}"}
            
            # Validate target structure
            target = plan["target"]
            if "type" not in target:
                return {"valid": False, "error": "Target missing 'type' field"}
            
            # Validate conditions
            conditions = plan["conditions"]
            if not isinstance(conditions, list) or len(conditions) == 0:
                return {"valid": False, "error": "Conditions must be a non-empty list"}
            
            # Validate each condition
            for i, condition in enumerate(conditions):
                required_condition_fields = ["type", "parameter", "operator", "value"]
                for field in required_condition_fields:
                    if field not in condition:
                        return {"valid": False, "error": f"Condition {i} missing field: {field}"}
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

# Demo mission examples for testing
DEMO_MISSIONS = [
    "Alert me if wallet 0x742d35Cc6bf8e1d6D8aEc8967c96e5e5E2DbDcf5 sends more than 5 ETH to any new address",
    "Monitor Bored Ape Yacht Club for wash trading and alert if detected",
    "Alert me if any CryptoPunk is sold for less than 10 ETH",
    "Watch wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 for any NFT purchases over $1000",
    "Monitor Pudgy Penguins collection for unusual trading volume spikes",
    "Alert me if Azuki collection shows price manipulation patterns",
    "Track wallet 0x50de6856358cc35f3a9a57eaaa34bd4cb707d2cd for suspicious activity",
    "Monitor Art Blocks Curated for any pieces being flipped within 24 hours"
]

# Helper function for testing
async def test_mission_parser():
    """Test function for mission parser"""
    parser = MissionParser()
    
    for mission in DEMO_MISSIONS[:3]:  # Test first 3 missions
        print(f"\n{'='*60}")
        print(f"Testing: {mission}")
        print(f"{'='*60}")
        
        result = await parser.parse_mission(mission)
        
        if result.success:
            print("✅ SUCCESS")
            print(f"Action Type: {result.structured_plan.action_type}")
            print(f"Target: {result.structured_plan.target}")
            print(f"Conditions: {result.structured_plan.conditions}")
            print(f"Blockchain: {result.structured_plan.blockchain}")
        else:
            print("❌ FAILED")
            print(f"Error: {result.error}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_mission_parser())