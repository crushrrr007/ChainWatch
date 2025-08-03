# app/api/endpoints/agents.py - Agent Management API (Production Clean)
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db, AsyncSession, Agent, User, get_user_by_telegram_id, create_user
from app.models.schemas import (
    AgentCreate, Agent as AgentSchema, AgentWithUser, AgentUpdate,
    APIResponse, PaginatedResponse, MissionParseRequest, MissionParseResponse
)
from app.agents.mission_parser import MissionParser
from app.core.scheduler import AgentScheduler

router = APIRouter()

# Dependency to get scheduler
def get_scheduler():
    from main import scheduler
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    return scheduler

@router.post("/deploy", response_model=APIResponse)
async def deploy_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    scheduler: AgentScheduler = Depends(get_scheduler)
):
    """Deploy a new monitoring agent"""
    try:
        # Get or create user
        user = await get_user_by_telegram_id(db, agent_data.telegram_user_id)
        if not user:
            user = await create_user(
                db, 
                agent_data.telegram_user_id, 
                agent_data.telegram_username
            )
        
        # Parse mission using AI
        parser = MissionParser()
        parse_result = await parser.parse_mission(agent_data.mission_prompt)
        
        if not parse_result.success:
            return APIResponse(
                success=False,
                message=f"Mission parsing failed: {parse_result.error}"
            )
        
        # Create agent
        agent = Agent(
            user_id=user.id,
            mission_prompt=agent_data.mission_prompt,
            structured_plan=parse_result.structured_plan.dict(),
            agent_name=agent_data.agent_name,
            schedule_interval=agent_data.schedule_interval,
            status="active"
        )
        
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        return APIResponse(
            success=True,
            message=f"Agent deployed successfully with ID {agent.id}",
            data={
                "agent_id": agent.id,
                "structured_plan": parse_result.structured_plan.dict(),
                "confidence": parse_result.confidence
            }
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Agent deployment failed: {str(e)}")

@router.get("/", response_model=PaginatedResponse)
async def list_agents(
    telegram_user_id: Optional[str] = Query(None, description="Filter by Telegram user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List agents with pagination and filtering"""
    try:
        # Build query
        query = select(Agent).options(selectinload(Agent.user))
        
        # Apply filters
        if telegram_user_id:
            user = await get_user_by_telegram_id(db, telegram_user_id)
            if user:
                query = query.where(Agent.user_id == user.id)
            else:
                # Return empty result if user not found
                return PaginatedResponse(
                    items=[],
                    total=0,
                    page=page,
                    per_page=per_page,
                    pages=0
                )
        
        if status:
            query = query.where(Agent.status == status)
        
        # Order by creation date (newest first)
        query = query.order_by(desc(Agent.created_at))
        
        # Count total
        count_result = await db.execute(select(Agent.id).select_from(query.subquery()))
        total = len(count_result.fetchall())
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Execute query
        result = await db.execute(query)
        agents = result.scalars().all()
        
        # Calculate pages
        pages = (total + per_page - 1) // per_page
        
        return PaginatedResponse(
            items=[AgentWithUser.from_orm(agent) for agent in agents],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")

@router.get("/{agent_id}", response_model=AgentWithUser)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific agent by ID"""
    try:
        query = select(Agent).options(selectinload(Agent.user)).where(Agent.id == agent_id)
        result = await db.execute(query)
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return AgentWithUser.from_orm(agent)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")

@router.patch("/{agent_id}", response_model=APIResponse)
async def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an agent"""
    try:
        # Get agent
        query = select(Agent).where(Agent.id == agent_id)
        result = await db.execute(query)
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Update fields
        update_data = agent_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(agent, field, value)
        
        await db.commit()
        
        return APIResponse(
            success=True,
            message="Agent updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")

@router.delete("/{agent_id}", response_model=APIResponse)
async def delete_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an agent"""
    try:
        # Get agent
        query = select(Agent).where(Agent.id == agent_id)
        result = await db.execute(query)
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Delete agent (cascades to alerts)
        await db.delete(agent)
        await db.commit()
        
        return APIResponse(
            success=True,
            message="Agent deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")

@router.post("/{agent_id}/run", response_model=APIResponse)
async def run_agent_manually(
    agent_id: int,
    scheduler: AgentScheduler = Depends(get_scheduler)
):
    """Manually trigger an agent to run once"""
    try:
        result = await scheduler.run_agent_once(agent_id)
        
        if result["success"]:
            return APIResponse(
                success=True,
                message="Agent executed successfully",
                data=result
            )
        else:
            return APIResponse(
                success=False,
                message=f"Agent execution failed: {result.get('error')}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run agent: {str(e)}")

@router.post("/{agent_id}/pause", response_model=APIResponse)
async def pause_agent(
    agent_id: int,
    scheduler: AgentScheduler = Depends(get_scheduler)
):
    """Pause an agent"""
    try:
        result = await scheduler.pause_agent(agent_id)
        return APIResponse(
            success=True,
            message="Agent paused successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pause agent: {str(e)}")

@router.post("/{agent_id}/resume", response_model=APIResponse)
async def resume_agent(
    agent_id: int,
    scheduler: AgentScheduler = Depends(get_scheduler)
):
    """Resume a paused agent"""
    try:
        result = await scheduler.resume_agent(agent_id)
        return APIResponse(
            success=True,
            message="Agent resumed successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume agent: {str(e)}")

@router.post("/parse-mission", response_model=MissionParseResponse)
async def parse_mission(request: MissionParseRequest):
    """Parse a mission prompt to preview the structured plan"""
    try:
        parser = MissionParser()
        result = await parser.parse_mission(request.mission_prompt, request.context)
        return result
        
    except Exception as e:
        return MissionParseResponse(
            success=False,
            error=f"Mission parsing failed: {str(e)}"
        )

@router.get("/stats", response_model=APIResponse)
async def get_scheduler_stats(scheduler: AgentScheduler = Depends(get_scheduler)):
    """Get scheduler statistics"""
    try:
        stats = scheduler.get_stats()
        return APIResponse(
            success=True,
            message="Scheduler stats retrieved",
            data=stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")