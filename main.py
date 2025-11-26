from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
import os
import logging
from dotenv import load_dotenv
from datetime import datetime

from core.database import db
from core.models import Tool, ToolExecution, ToolResponse, HealthResponse, ToolsResponse
from tools.registry import registry
import tools.builtin  # This will auto-register all builtin tools
from api.admin import router as admin_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await db.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    
    yield
    
    # Shutdown
    await db.close()
    logger.info("Database connection closed")

app = FastAPI(
    title="MCP Server", 
    description="Multi-tenant MCP Server for Cody", 
    version="1.0.0",
    lifespan=lifespan
)

# Register routers
app.include_router(admin_router)

# Simple API key validation
API_KEY = os.getenv("API_KEY", "dev-key-123")

def verify_api_key(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token



@app.get("/")
async def root():
    return {"message": "MCP Server is running", "version": "1.0.0"}

@app.get("/health", response_model=HealthResponse)
async def health():
    database_connected = db._client is not None
    return HealthResponse(
        status="healthy" if database_connected else "degraded",
        timestamp=datetime.now().isoformat(),
        database_connected=database_connected
    )

@app.get("/tools", response_model=ToolsResponse)
async def get_tools(api_key: str = Depends(verify_api_key)):
    """Discover available tools for tenant"""
    # TODO: Extract tenant_id from API key or request headers
    tenant_id = "1"  # Placeholder - will be replaced with proper tenant extraction
    
    # Get enabled tools for this tenant from database
    enabled_tools = await db.get_tenant_tools(tenant_id)
    
    if not enabled_tools:
        # Fallback: return all available tools if no tenant config
        tools_schema = registry.list_all_tools()
    else:
        # Return only enabled tools for tenant
        tools_schema = registry.list_tools_for_tenant(enabled_tools)
    
    return ToolsResponse(tools=tools_schema, tenant_id=tenant_id)

@app.post("/tools/{tool_name}/execute")
async def execute_tool(
    tool_name: str, 
    request: ToolExecution,
    api_key: str = Depends(verify_api_key)
) -> ToolResponse:
    """Execute a specific tool"""
    
    # TODO: Extract tenant_id from API key or request headers
    tenant_id = "1"  # Placeholder
    
    # Get tool from registry
    tool = registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    # Check if tool is enabled for this tenant
    enabled_tools = await db.get_tenant_tools(tenant_id)
    if enabled_tools and tool_name not in enabled_tools:
        raise HTTPException(status_code=403, detail=f"Tool '{tool_name}' not enabled for tenant")
    
    # Execute tool with tenant context
    try:
        result = await tool.execute(request.arguments, tenant_id)
        return ToolResponse(content=[{"text": result}])
    except Exception as e:
        logger.error(f"Tool execution error for {tool_name}: {e}")
        return ToolResponse(content=[{"text": f"Error executing tool: {str(e)}"}])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)