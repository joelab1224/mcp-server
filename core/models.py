from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

class ToolExecution(BaseModel):
    arguments: Dict[str, Any]

class ToolResponse(BaseModel):
    content: List[Dict[str, str]]

class TenantConfig(BaseModel):
    tenant_id: int
    mcp_server_url: Optional[str] = None
    mcp_api_key: Optional[str] = None
    enabled_tools: List[str] = []
    api_keys: Dict[str, str] = {}
    system_prompt: Optional[str] = None
    avatar_url: Optional[str] = None
    
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database_connected: bool = False

class ToolsResponse(BaseModel):
    tools: List[Tool]
    tenant_id: Optional[str] = None