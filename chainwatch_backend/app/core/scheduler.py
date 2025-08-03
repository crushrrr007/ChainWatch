# app/core/scheduler.py - Agent Scheduler and Orchestrator
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal, get_active_agents, get_agent_with_user
from app.core.database import Agent, Alert, User
from app.agents.mission_parser import MissionParser
from app.agents.tool_executor import ToolExecutor
from app.agents.analysis_engine import AnalysisEngine
from app.agents.action_dispatcher import ActionDispatcher
from app.core.config import settings

logger = logging.getLogger(__name__)

class AgentScheduler:
    """Schedules and runs monitoring agents"""
    
    def __init__(self):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        
        # Initialize components
        self.mission_parser = MissionParser()
        self.tool_executor = ToolExecutor()
        self.analysis_engine = AnalysisEngine()
        self.action_dispatcher = ActionDispatcher()
        
        # Concurrency control
        self.max_concurrent_agents = settings.MAX_CONCURRENT_AGENTS
        self.semaphore = asyncio.Semaphore(self.max_concurrent_agents)
        
        # Stats
        self.stats = {
            "agents_processed": 0,
            "alerts_generated": 0,
            "errors": 0,
            "last_run": None
        }
    
    async def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting ChainWatch Agent Scheduler...")
        self.is_running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logger.info("✅ Agent Scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return
        
        logger.info("Stopping Agent Scheduler...")
        self.is_running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ Agent Scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                cycle_start = datetime.utcnow()
                logger.info("🔄 Starting scheduler cycle...")
                
                # Get agents that need to run
                agents_to_run = await self._get_agents_to_run()
                
                if agents_to_run:
                    logger.info(f"Processing {len(agents_to_run)} agents...")
                    
                    # Process agents concurrently with semaphore
                    tasks = [
                        self._process_agent_with_semaphore(agent)
                        for agent in agents_to_run
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Log results
                    successful = sum(1 for r in results if not isinstance(r, Exception))
                    failed = len(results) - successful
                    
                    logger.info(f"✅ Cycle completed: {successful} successful, {failed} failed")
                    self.stats["last_run"] = cycle_start
                else:
                    logger.info("No agents to process in this cycle")
                
                # Wait for next cycle
                await asyncio.sleep(settings.AGENT_CHECK_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {str(e)}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _get_agents_to_run(self) -> List[Agent]:
        """Get agents that are ready to run"""
        async with AsyncSessionLocal() as db:
            current_time = datetime.utcnow()
            
            # Query for active agents that are ready to run
            query = select(Agent).options(selectinload(Agent.user)).where(
                Agent.status == "active"
            ).where(
                # Agent has never run OR it's time for next run
                (Agent.last_run_at.is_(None)) |
                (Agent.next_run_at <= current_time)
            ).where(
                # Don't run agents with too many errors
                Agent.error_count < Agent.max_retries
            )
            
            result = await db.execute(query)
            return result.scalars().all()
    
    async def _process_agent_with_semaphore(self, agent: Agent):
        """Process agent with concurrency control"""
        async with self.semaphore:
            return await self._process_agent(agent)
    
    async def _process_agent(self, agent: Agent) -> Dict[str, Any]:
        """Process a single agent"""
        start_time = datetime.utcnow()
        agent_id = agent.id
        
        logger.info(f"🤖 Processing agent {agent_id}: {agent.mission_prompt[:50]}...")
        
        try:
            # Update agent run timestamps
            await self._update_agent_run_time(agent_id, start_time)
            
            # Execute the agent's plan
            execution_result = await self.tool_executor.execute_plan(agent.structured_plan)
            
            if not execution_result.get("success"):
                raise Exception(f"Tool execution failed: {execution_result.get('error')}")
            
            # Check if alerts were triggered
            alerts = execution_result.get("alerts", [])
            
            if alerts:
                logger.info(f"🚨 Agent {agent_id} triggered {len(alerts)} alerts")
                
                # Generate analysis
                analysis_result = await self.analysis_engine.generate_analysis(
                    agent.structured_plan,
                    execution_result
                )
                
                if analysis_result.get("success") and analysis_result.get("has_alerts"):
                    # Create and dispatch alerts
                    await self._handle_alerts(agent, alerts, analysis_result["analysis"])
                    
                    # Update agent status to triggered
                    await self._update_agent_status(agent_id, "triggered")
                else:
                    logger.warning(f"Analysis failed for agent {agent_id}")
            
            # Reset error count on success
            await self._reset_agent_error_count(agent_id)
            
            self.stats["agents_processed"] += 1
            
            return {
                "success": True,
                "agent_id": agent_id,
                "alerts_count": len(alerts)
            }
            
        except Exception as e:
            logger.error(f"❌ Agent {agent_id} failed: {str(e)}")
            
            # Update error count
            await self._increment_agent_error_count(agent_id, str(e))
            self.stats["errors"] += 1
            
            return {
                "success": False,
                "agent_id": agent_id,
                "error": str(e)
            }
    
    async def _handle_alerts(
        self, 
        agent: Agent, 
        alerts: List[Dict[str, Any]], 
        analysis: Dict[str, Any]
    ):
        """Handle triggered alerts"""
        async with AsyncSessionLocal() as db:
            try:
                for alert_data in alerts:
                    # Create alert record
                    from app.agents.analysis_engine import AnalysisEngine
                    engine = AnalysisEngine()
                    
                    title = await engine.generate_alert_title(alert_data, agent.structured_plan)
                    
                    alert = Alert(
                        agent_id=agent.id,
                        title=title,
                        report_content=analysis.get("summary", "Alert triggered"),
                        raw_data=alert_data,
                        alert_type=alert_data.get("type", "unknown"),
                        severity=alert_data.get("severity", "medium")
                    )
                    
                    db.add(alert)
                    await db.flush()  # Get alert ID
                    
                    # Dispatch alert
                    dispatch_result = await self.action_dispatcher.dispatch_alert(
                        alert, agent, agent.user, analysis
                    )
                    
                    if dispatch_result.get("success"):
                        logger.info(f"✅ Alert {alert.id} dispatched successfully")
                    else:
                        logger.error(f"❌ Alert {alert.id} dispatch failed: {dispatch_result.get('errors')}")
                    
                    self.stats["alerts_generated"] += 1
                
                await db.commit()
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Alert handling failed: {str(e)}")
                raise
    
    # Database helper methods
    async def _update_agent_run_time(self, agent_id: int, run_time: datetime):
        """Update agent run timestamps"""
        async with AsyncSessionLocal() as db:
            # Calculate next run time
            agent_query = select(Agent).where(Agent.id == agent_id)
            result = await db.execute(agent_query)
            agent = result.scalar_one()
            
            next_run = run_time + timedelta(seconds=agent.schedule_interval)
            
            # Update timestamps
            update_query = update(Agent).where(Agent.id == agent_id).values(
                last_run_at=run_time,
                next_run_at=next_run,
                updated_at=run_time
            )
            
            await db.execute(update_query)
            await db.commit()
    
    async def _update_agent_status(self, agent_id: int, status: str):
        """Update agent status"""
        async with AsyncSessionLocal() as db:
            update_query = update(Agent).where(Agent.id == agent_id).values(
                status=status,
                updated_at=datetime.utcnow()
            )
            
            await db.execute(update_query)
            await db.commit()
    
    async def _increment_agent_error_count(self, agent_id: int, error_message: str):
        """Increment agent error count"""
        async with AsyncSessionLocal() as db:
            # Get current error count
            agent_query = select(Agent).where(Agent.id == agent_id)
            result = await db.execute(agent_query)
            agent = result.scalar_one()
            
            new_error_count = agent.error_count + 1
            new_status = "error" if new_error_count >= agent.max_retries else agent.status
            
            update_query = update(Agent).where(Agent.id == agent_id).values(
                error_count=new_error_count,
                last_error=error_message,
                status=new_status,
                updated_at=datetime.utcnow()
            )
            
            await db.execute(update_query)
            await db.commit()
    
    async def _reset_agent_error_count(self, agent_id: int):
        """Reset agent error count on successful run"""
        async with AsyncSessionLocal() as db:
            update_query = update(Agent).where(Agent.id == agent_id).values(
                error_count=0,
                last_error=None,
                retry_count=0,
                updated_at=datetime.utcnow()
            )
            
            await db.execute(update_query)
            await db.commit()
    
    # Public methods for manual control
    async def run_agent_once(self, agent_id: int) -> Dict[str, Any]:
        """Manually run a specific agent once"""
        async with AsyncSessionLocal() as db:
            # Get agent with user
            agent = await get_agent_with_user(db, agent_id)
            if not agent:
                return {"success": False, "error": "Agent not found"}
            
            return await self._process_agent(agent)
    
    async def pause_agent(self, agent_id: int) -> Dict[str, Any]:
        """Pause an agent"""
        await self._update_agent_status(agent_id, "paused")
        return {"success": True, "message": "Agent paused"}
    
    async def resume_agent(self, agent_id: int) -> Dict[str, Any]:
        """Resume a paused agent"""
        await self._update_agent_status(agent_id, "active")
        return {"success": True, "message": "Agent resumed"}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        return {
            **self.stats,
            "is_running": self.is_running,
            "max_concurrent_agents": self.max_concurrent_agents,
            "check_interval": settings.AGENT_CHECK_INTERVAL
        }