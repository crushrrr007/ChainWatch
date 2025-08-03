# app/agents/mission_parser.py - AI Mission Parser
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
                confidence=0.85
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
SUPPORTED ACTION TYPES: wallet_monitor, nft_monitor, collection_monitor

IMPORTANT: You can ONLY use these 3 action types.

RESPONSE FORMAT (JSON only, no other text):
{{
    "action_type": "wallet_monitor|nft_monitor|collection_monitor",
    "target": {{
        "type": "wallet|nft|collection",
        "address": "wallet_address_or_contract_address",
        "token_id": "token_id_if_specific_nft",
        "collection_name": "human_readable_collection_name"
    }},
    "conditions": [
        {{
            "type": "threshold|change|pattern|detection",
            "parameter": "volume|price|outgoing_transfer|incoming_transfer|washtrade_activity",
            "operator": "gt|lt|eq|contains",
            "value": "threshold_value",
            "timeframe": "1h|24h|7d|30d"
        }}
    ],
    "blockchain": "ethereum|polygon|avalanche|bsc|linea|solana",
    "parameters": {{
        "currency": "usd|eth|usdt",
        "include_washtrade": false,
        "min_value_usd": 0,
        "alert_frequency": "immediate|daily|weekly"
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
            valid_action_types = ["wallet_monitor", "nft_monitor", "collection_monitor"]
            if plan["action_type"] not in valid_action_types:
                return {"valid": False, "error": f"Invalid action_type: {plan['action_type']}. Must be one of: {valid_action_types}"}
            
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