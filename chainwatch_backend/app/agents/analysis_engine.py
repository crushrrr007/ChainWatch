# app/agents/analysis_engine.py - AI-Powered Analysis Engine
import json
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

class AnalysisEngine:
    """Generates intelligent analysis and alerts using Google Gemini"""
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
    
    async def generate_analysis(
        self, 
        agent_plan: Dict[str, Any], 
        execution_result: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate analysis and alerts based on execution results
        
        Args:
            agent_plan: The original structured plan
            execution_result: Results from tool_executor
            context: Additional context (historical data, user preferences)
        
        Returns:
            Dict containing analysis, alerts, and recommendations
        """
        try:
            # Check if there are any alerts to analyze
            alerts = execution_result.get("alerts", [])
            
            if not alerts:
                return {
                    "success": True,
                    "has_alerts": False,
                    "summary": "No alerts triggered during this monitoring cycle",
                    "analysis": None
                }
            
            # Generate detailed analysis for alerts
            analysis = await self._analyze_alerts(agent_plan, execution_result, alerts, context)
            
            return {
                "success": True,
                "has_alerts": True,
                "alert_count": len(alerts),
                "analysis": analysis,
                "summary": analysis.get("summary", "Analysis completed")
            }
            
        except Exception as e:
            logger.error(f"Analysis generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "has_alerts": False
            }
    
    async def _analyze_alerts(
        self, 
        agent_plan: Dict[str, Any], 
        execution_result: Dict[str, Any], 
        alerts: List[Dict[str, Any]], 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comprehensive analysis of triggered alerts"""
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(agent_plan, execution_result, alerts, context)
        
        # Generate analysis using Gemini
        response = self.model.generate_content(prompt)
        
        # Parse the response
        analysis_result = self._parse_analysis_response(response.text)
        
        return analysis_result
    
    def _build_analysis_prompt(
        self, 
        agent_plan: Dict[str, Any], 
        execution_result: Dict[str, Any], 
        alerts: List[Dict[str, Any]], 
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build the analysis prompt for Gemini"""
        
        # Format the data for the prompt
        plan_summary = {
            "action_type": agent_plan.get("action_type"),
            "target": agent_plan.get("target"),
            "blockchain": agent_plan.get("blockchain")
        }
        
        prompt = f"""
You are an expert blockchain analyst. Analyze the following monitoring results and provide actionable insights.

MONITORING CONFIGURATION:
{json.dumps(plan_summary, indent=2)}

ALERTS TRIGGERED:
{json.dumps(alerts, indent=2)}

RAW DATA:
{json.dumps(execution_result.get("data", {}), indent=2)}

Please provide a comprehensive analysis in the following JSON format:

{{
    "summary": "Brief 1-2 sentence summary of what happened",
    "severity": "low|medium|high|critical",
    "analysis": {{
        "what_happened": "Detailed explanation of the events that triggered the alert",
        "significance": "Why this is important and what it might indicate",
        "context": "How this fits into broader market patterns or behaviors",
        "risk_assessment": "Potential risks or opportunities identified"
    }},
    "recommendations": [
        "Specific actionable recommendation 1",
        "Specific actionable recommendation 2"
    ],
    "alerts": [
        {{
            "title": "Alert title",
            "message": "User-friendly alert message",
            "details": "Additional technical details",
            "action_suggested": "What the user should consider doing"
        }}
    ],
    "technical_details": {{
        "data_quality": "Assessment of data reliability",
        "confidence_level": "0.0-1.0 confidence in the analysis",
        "next_monitoring_focus": "What to watch for next"
    }}
}}

Focus on:
1. Clear, actionable insights
2. Risk assessment and potential implications
3. Specific recommendations for the user
4. Context about market conditions or patterns

Respond with ONLY valid JSON, no other text:
"""
        return prompt
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate the analysis response"""
        try:
            # Clean the response (remove markdown if present)
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            analysis = json.loads(cleaned)
            
            # Validate required fields
            required_fields = ["summary", "severity", "analysis", "recommendations", "alerts"]
            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"Missing field in analysis: {field}")
                    analysis[field] = f"Error: {field} not provided"
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis JSON: {e}")
            logger.error(f"Response text: {response_text}")
            
            # Return fallback analysis
            return {
                "summary": "Analysis parsing failed, but alerts were triggered",
                "severity": "medium",
                "analysis": {
                    "what_happened": "Alert conditions were met but detailed analysis failed",
                    "significance": "Manual review recommended",
                    "context": "Analysis engine encountered parsing error",
                    "risk_assessment": "Unknown - requires manual assessment"
                },
                "recommendations": [
                    "Review the raw alert data manually",
                    "Check system logs for analysis errors"
                ],
                "alerts": [
                    {
                        "title": "Analysis Error",
                        "message": "Alert triggered but detailed analysis failed",
                        "details": "The monitoring system detected trigger conditions but could not generate detailed analysis",
                        "action_suggested": "Review raw data and investigate manually"
                    }
                ],
                "technical_details": {
                    "data_quality": "Unknown",
                    "confidence_level": 0.0,
                    "next_monitoring_focus": "Fix analysis engine issues"
                }
            }
    
    async def generate_telegram_message(self, analysis: Dict[str, Any], agent_name: str = None) -> str:
        """Generate a user-friendly Telegram message from analysis"""
        try:
            if not analysis.get("alerts"):
                return "🤖 ChainWatch: No alerts to report"
            
            # Build message
            agent_prefix = f"🤖 **{agent_name}**\n" if agent_name else "🤖 **ChainWatch Alert**\n"
            
            severity_emoji = {
                "low": "🟢",
                "medium": "🟡", 
                "high": "🟠",
                "critical": "🔴"
            }
            
            emoji = severity_emoji.get(analysis.get("severity", "medium"), "🟡")
            
            message_parts = [
                f"{agent_prefix}",
                f"{emoji} **{analysis.get('severity', 'Medium').upper()} ALERT**",
                f"",
                f"📋 **Summary:** {analysis.get('summary', 'Alert triggered')}",
                f""
            ]
            
            # Add main alerts
            alerts = analysis.get("alerts", [])
            for i, alert in enumerate(alerts[:3]):  # Limit to 3 alerts for Telegram
                message_parts.extend([
                    f"🔔 **Alert {i+1}:** {alert.get('title', 'Alert')}",
                    f"📝 {alert.get('message', 'No message')}",
                    f""
                ])
            
            # Add recommendations
            recommendations = analysis.get("recommendations", [])
            if recommendations:
                message_parts.extend([
                    f"💡 **Recommended Actions:**"
                ])
                for rec in recommendations[:2]:  # Limit to 2 recommendations
                    message_parts.append(f"• {rec}")
                message_parts.append("")
            
            # Add timestamp
            from datetime import datetime
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            message_parts.append(f"⏰ {timestamp}")
            
            return "\n".join(message_parts)
            
        except Exception as e:
            logger.error(f"Failed to generate Telegram message: {e}")
            return f"🤖 ChainWatch Alert: Analysis completed but message formatting failed. Please check the dashboard for details."
    
    async def generate_alert_title(self, alert_data: Dict[str, Any], agent_plan: Dict[str, Any]) -> str:
        """Generate a concise alert title"""
        try:
            action_type = agent_plan.get("action_type", "monitor")
            target = agent_plan.get("target", {})
            alert_type = alert_data.get("type", "unknown")
            
            if action_type == "wallet_monitor":
                wallet = target.get("address", "Unknown")[:10] + "..."
                if alert_type == "wallet_threshold_exceeded":
                    return f"Wallet {wallet} - Large Transfer Detected"
                else:
                    return f"Wallet {wallet} - Activity Alert"
            
            elif action_type == "collection_monitor":
                collection = target.get("collection_name", target.get("address", "Unknown"))
                if alert_type == "wash_trade_detected":
                    return f"{collection} - Wash Trading Detected"
                elif alert_type == "price_alert":
                    return f"{collection} - Price Alert"
                else:
                    return f"{collection} - Collection Alert"
            
            elif action_type == "nft_monitor":
                collection = target.get("collection_name", "NFT")
                token_id = target.get("token_id", "")
                if token_id:
                    return f"{collection} #{token_id} - Alert"
                else:
                    return f"{collection} - NFT Alert"
            
            return "ChainWatch Alert"
            
        except Exception:
            return "ChainWatch Alert"

# Demo analysis examples for testing
DEMO_ANALYSIS_SCENARIOS = [
    {
        "name": "Large Wallet Transfer",
        "agent_plan": {
            "action_type": "wallet_monitor",
            "target": {"address": "0x742d35Cc6bf8e1d6D8aEc8967c96e5e5E2DbDcf5"},
            "blockchain": "ethereum"
        },
        "alerts": [
            {
                "type": "wallet_threshold_exceeded",
                "message": "Wallet sent 7.5 ETH (threshold: 5 ETH)",
                "severity": "high",
                "details": {
                    "amount": 7.5,
                    "threshold": 5.0,
                    "currency": "ETH"
                }
            }
        ]
    },
    {
        "name": "Wash Trading Detection",
        "agent_plan": {
            "action_type": "collection_monitor",
            "target": {"collection_name": "Bored Ape Yacht Club"},
            "blockchain": "ethereum"
        },
        "alerts": [
            {
                "type": "wash_trade_detected",
                "message": "Wash trading detected (ratio: 15%)",
                "severity": "high",
                "details": {
                    "washtrade_ratio": 0.15,
                    "threshold": 0.1
                }
            }
        ]
    }
]

# Helper function for testing
async def test_analysis_engine():
    """Test function for analysis engine"""
    engine = AnalysisEngine()
    
    for scenario in DEMO_ANALYSIS_SCENARIOS:
        print(f"\n{'='*60}")
        print(f"Testing: {scenario['name']}")
        print(f"{'='*60}")
        
        execution_result = {
            "success": True,
            "alerts": scenario["alerts"],
            "data": {}
        }
        
        result = await engine.generate_analysis(
            scenario["agent_plan"], 
            execution_result
        )
        
        if result["success"]:
            print("✅ Analysis Generated")
            print(f"Summary: {result['analysis']['summary']}")
            print(f"Severity: {result['analysis']['severity']}")
            
            # Test Telegram message generation
            telegram_msg = await engine.generate_telegram_message(
                result["analysis"], 
                f"Agent-{scenario['name']}"
            )
            print(f"\nTelegram Message:\n{telegram_msg}")
        else:
            print("❌ Analysis Failed")
            print(f"Error: {result['error']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analysis_engine())