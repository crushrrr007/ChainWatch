# app/api/endpoints/alerts.py - Alerts Management API
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db, AsyncSession, Alert, Agent, User, get_user_by_telegram_id
from app.models.schemas import (
    Alert as AlertSchema, AlertWithAgent, APIResponse, PaginatedResponse
)

router = APIRouter()

@router.get("/", response_model=PaginatedResponse)
async def list_alerts(
    telegram_user_id: Optional[str] = Query(None, description="Filter by Telegram user ID"),
    agent_id: Optional[int] = Query(None, description="Filter by agent ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List alerts with pagination and filtering"""
    try:
        # Build query
        query = select(Alert).options(
            selectinload(Alert.agent).selectinload(Agent.user)
        )
        
        # Apply filters
        if telegram_user_id:
            user = await get_user_by_telegram_id(db, telegram_user_id)
            if user:
                # Filter by user's agents
                user_agent_ids = select(Agent.id).where(Agent.user_id == user.id)
                query = query.where(Alert.agent_id.in_(user_agent_ids))
            else:
                # Return empty result if user not found
                return PaginatedResponse(
                    items=[],
                    total=0,
                    page=page,
                    per_page=per_page,
                    pages=0
                )
        
        if agent_id:
            query = query.where(Alert.agent_id == agent_id)
        
        if severity:
            query = query.where(Alert.severity == severity)
        
        if alert_type:
            query = query.where(Alert.alert_type == alert_type)
        
        # Order by triggered time (newest first)
        query = query.order_by(desc(Alert.triggered_at))
        
        # Count total
        count_result = await db.execute(select(Alert.id).select_from(query.subquery()))
        total = len(count_result.fetchall())
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Execute query
        result = await db.execute(query)
        alerts = result.scalars().all()
        
        # Calculate pages
        pages = (total + per_page - 1) // per_page
        
        return PaginatedResponse(
            items=[AlertWithAgent.from_orm(alert) for alert in alerts],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list alerts: {str(e)}")

@router.get("/{alert_id}", response_model=AlertWithAgent)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific alert by ID"""
    try:
        query = select(Alert).options(
            selectinload(Alert.agent).selectinload(Agent.user)
        ).where(Alert.id == alert_id)
        
        result = await db.execute(query)
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return AlertWithAgent.from_orm(alert)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert: {str(e)}")

@router.delete("/{alert_id}", response_model=APIResponse)
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an alert"""
    try:
        # Get alert
        query = select(Alert).where(Alert.id == alert_id)
        result = await db.execute(query)
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Delete alert
        await db.delete(alert)
        await db.commit()
        
        return APIResponse(
            success=True,
            message="Alert deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete alert: {str(e)}")

@router.get("/agent/{agent_id}", response_model=PaginatedResponse)
async def get_alerts_for_agent(
    agent_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """Get all alerts for a specific agent"""
    try:
        # Check if agent exists
        agent_query = select(Agent).where(Agent.id == agent_id)
        agent_result = await db.execute(agent_query)
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Build query for alerts
        query = select(Alert).options(
            selectinload(Alert.agent).selectinload(Agent.user)
        ).where(Alert.agent_id == agent_id).order_by(desc(Alert.triggered_at))
        
        # Count total
        count_result = await db.execute(select(Alert.id).select_from(query.subquery()))
        total = len(count_result.fetchall())
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Execute query
        result = await db.execute(query)
        alerts = result.scalars().all()
        
        # Calculate pages
        pages = (total + per_page - 1) // per_page
        
        return PaginatedResponse(
            items=[AlertWithAgent.from_orm(alert) for alert in alerts],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts for agent: {str(e)}")

@router.get("/summary/stats", response_model=APIResponse)
async def get_alert_summary_stats(
    telegram_user_id: Optional[str] = Query(None, description="Filter by Telegram user ID"),
    days: int = Query(7, ge=1, le=365, description="Number of days to include in stats"),
    db: AsyncSession = Depends(get_db)
):
    """Get summary statistics for alerts"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build base query
        query = select(Alert)
        
        # Apply user filter if provided
        if telegram_user_id:
            user = await get_user_by_telegram_id(db, telegram_user_id)
            if user:
                user_agent_ids = select(Agent.id).where(Agent.user_id == user.id)
                query = query.where(Alert.agent_id.in_(user_agent_ids))
            else:
                # Return empty stats if user not found
                return APIResponse(
                    success=True,
                    message="Alert statistics (user not found)",
                    data={
                        "total_alerts": 0,
                        "alerts_by_severity": {},
                        "alerts_by_type": {},
                        "alerts_by_day": {},
                        "date_range": {
                            "start": start_date.isoformat(),
                            "end": end_date.isoformat(),
                            "days": days
                        }
                    }
                )
        
        # Filter by date range
        query = query.where(Alert.triggered_at >= start_date)
        
        # Get all alerts in range
        result = await db.execute(query)
        alerts = result.scalars().all()
        
        # Calculate statistics
        total_alerts = len(alerts)
        
        # Group by severity
        alerts_by_severity = {}
        for alert in alerts:
            severity = alert.severity
            alerts_by_severity[severity] = alerts_by_severity.get(severity, 0) + 1
        
        # Group by type
        alerts_by_type = {}
        for alert in alerts:
            alert_type = alert.alert_type
            alerts_by_type[alert_type] = alerts_by_type.get(alert_type, 0) + 1
        
        # Group by day
        alerts_by_day = {}
        for alert in alerts:
            day = alert.triggered_at.date().isoformat()
            alerts_by_day[day] = alerts_by_day.get(day, 0) + 1
        
        return APIResponse(
            success=True,
            message="Alert statistics retrieved",
            data={
                "total_alerts": total_alerts,
                "alerts_by_severity": alerts_by_severity,
                "alerts_by_type": alerts_by_type,
                "alerts_by_day": alerts_by_day,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert statistics: {str(e)}")