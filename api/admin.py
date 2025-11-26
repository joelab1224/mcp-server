from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, Any
from datetime import datetime
import os
import logging

from ..core.models import HealthResponse
from ..tools.registry import registry

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/admin',
    tags=['admin']
)

# Simple admin authentication (can be enhanced later)
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "admin-key-123")

def verify_admin_key(authorization: str = Header(None)):
    """Verify admin API key"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = authorization.split(" ")[1]
    if token != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return token

@router.post("/reload-tools")
async def reload_tools(admin_key: str = Depends(verify_admin_key)) -> Dict[str, Any]:
    """Reload all tools from builtin modules"""
    try:
        tool_count = registry.reload_tools()
        
        return {
            "status": "success",
            "message": f"Tools reloaded successfully",
            "tool_count": tool_count,
            "reloaded_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error reloading tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload tools: {str(e)}")

@router.get("/tools")
async def list_all_tools(admin_key: str = Depends(verify_admin_key)) -> Dict[str, Any]:
    """List all registered tools (admin view)"""
    try:
        all_tools = registry.list_all_tools()
        
        return {
            "total_tools": len(all_tools),
            "tools": all_tools,
            "registry_status": "active"
        }
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")

@router.get("/status")
async def admin_status(admin_key: str = Depends(verify_admin_key)) -> Dict[str, Any]:
    """Get admin status information"""
    return {
        "server_status": "running",
        "tools_loaded": len(registry._tools),
        "available_tools": list(registry._tools.keys()),
        "timestamp": datetime.now().isoformat()
    }