"""
Tool Loader - Read-only database operations for loading tool definitions
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ToolLoader:
    """Read-only loader for tool definitions from database"""
    
    def __init__(self, db):
        self.db = db
    
    @property
    def tools_collection(self):
        """Lazy-load tools collection"""
        return self.db.get_collection("tools")
    
    async def load_tool(self, tool_id: str, tenant_id: str = None) -> Optional[Dict[str, Any]]:
        """Load a single tool definition from database"""
        query = {
            'tool_id': tool_id,
            'active': True
        }
        
        # Add tenant filtering if provided
        if tenant_id:
            query['tenants'] = tenant_id
        
        try:
            tool_doc = await self.tools_collection.find_one(query)
            if tool_doc:
                logger.debug(f"Loaded tool: {tool_id}")
                return tool_doc
            else:
                logger.warning(f"Tool not found: {tool_id} for tenant: {tenant_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load tool {tool_id}: {e}")
            return None
    
    async def load_tenant_tools(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Load all active tools for a tenant"""
        query = {
            'tenants': tenant_id,
            'active': True
        }
        
        try:
            tools = []
            async for tool_doc in self.tools_collection.find(query):
                tools.append(tool_doc)
            
            logger.info(f"Loaded {len(tools)} tools for tenant: {tenant_id}")
            return tools
            
        except Exception as e:
            logger.error(f"Failed to load tools for tenant {tenant_id}: {e}")
            return []
    
    async def load_all_tools(self) -> List[Dict[str, Any]]:
        """Load all active tools"""
        query = {'active': True}
        
        try:
            tools = []
            async for tool_doc in self.tools_collection.find(query):
                tools.append(tool_doc)
            
            logger.info(f"Loaded {len(tools)} total active tools")
            return tools
            
        except Exception as e:
            logger.error(f"Failed to load all tools: {e}")
            return []
    
    async def get_tool_schema(self, tool_id: str, tenant_id: str = None) -> Optional[Dict[str, Any]]:
        """Get just the schema information for a tool (for tool discovery)"""
        query = {
            'tool_id': tool_id,
            'active': True
        }
        
        if tenant_id:
            query['tenants'] = tenant_id
        
        try:
            # Only project the fields needed for schema
            projection = {
                'tool_id': 1,
                'name': 1,
                'input_schema': 1,
                'description': 1
            }
            
            tool_doc = await self.tools_collection.find_one(query, projection)
            if tool_doc:
                return {
                    'name': tool_doc['name'],
                    'description': tool_doc.get('description', f"{tool_doc['name']} tool"),
                    'inputSchema': tool_doc['input_schema']
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get schema for tool {tool_id}: {e}")
            return None