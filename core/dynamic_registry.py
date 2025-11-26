"""
Dynamic Registry - Integrates database-loaded tools with FastMCP
"""
import logging
from typing import Dict, Any, List
from fastmcp import FastMCP

from .tool_loader import ToolLoader
from .tool_compiler import ToolCompiler

logger = logging.getLogger(__name__)

class DynamicToolRegistry:
    """Dynamic tool registry that loads tools from database and registers with FastMCP"""
    
    def __init__(self, mcp_server: FastMCP, db):
        self.mcp = mcp_server
        self.loader = ToolLoader(db)
        self.compiler = ToolCompiler()
        self.registered_tools = {}  # tool_id -> bool
    
    async def load_and_register_tools(self, tenant_id: str = None):
        """Load tools from database and register with FastMCP"""
        try:
            if tenant_id:
                tools = await self.loader.load_tenant_tools(tenant_id)
                logger.info(f"Loading tools for tenant: {tenant_id}")
            else:
                tools = await self.loader.load_all_tools()
                logger.info("Loading all active tools")
            
            for tool_doc in tools:
                await self._register_tool(tool_doc)
            
            logger.info(f"Successfully registered {len(tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to load and register tools: {e}")
            raise
    
    async def _register_tool(self, tool_doc: Dict[str, Any]):
        """Register a single tool with FastMCP"""
        tool_id = tool_doc['tool_id']
        
        try:
            # Compile the tool
            compiled_tool = await self.compiler.compile_tool(tool_doc)
            
            # Create wrapper function for FastMCP based on input schema
            input_schema = compiled_tool.input_schema
            required_params = input_schema.get('properties', {})
            
            # Build function signature dynamically
            import inspect
            params = []
            for param_name, param_def in required_params.items():
                params.append(inspect.Parameter(param_name, inspect.Parameter.POSITIONAL_OR_KEYWORD))
            
            async def tool_wrapper(*args, **kwargs):
                # Convert args and kwargs to dict
                tool_params = dict(kwargs)
                
                # Execute the compiled tool
                result = await self.compiler.execute_tool(
                    tool_id, tool_params, None  # No tenant for now
                )
                
                return result
            
            # Update function signature to match expected parameters
            tool_wrapper.__signature__ = inspect.Signature(params)
            
            # Register with FastMCP using dynamic decorator
            self._register_with_fastmcp(compiled_tool, tool_wrapper)
            
            self.registered_tools[tool_id] = True
            logger.info(f"Registered tool: {tool_id}")
            
        except Exception as e:
            logger.error(f"Failed to register tool {tool_id}: {e}")
            raise
    
    def _register_with_fastmcp(self, compiled_tool, wrapper_func):
        """Register tool with FastMCP server"""
        # Use the tool decorator approach
        decorated_tool = self.mcp.tool(
            name=compiled_tool.name,
            description=f"Dynamic tool: {compiled_tool.name}"
        )(wrapper_func)
        
        return decorated_tool
    
    def _convert_schema_format(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database schema format to FastMCP format if needed"""
        # This is a simple pass-through for now
        # Add conversion logic here if database schema differs from FastMCP schema
        return input_schema
    
    async def reload_tool(self, tool_id: str, tenant_id: str = None):
        """Reload a specific tool from database"""
        try:
            tool_doc = await self.loader.load_tool(tool_id, tenant_id)
            if tool_doc:
                await self._register_tool(tool_doc)
                logger.info(f"Reloaded tool: {tool_id}")
            else:
                logger.warning(f"Tool not found for reload: {tool_id}")
                
        except Exception as e:
            logger.error(f"Failed to reload tool {tool_id}: {e}")
            raise
    
    async def get_available_tools(self, tenant_id: str = None) -> List[Dict[str, Any]]:
        """Get list of available tools for discovery"""
        try:
            tools = []
            if tenant_id:
                tool_docs = await self.loader.load_tenant_tools(tenant_id)
            else:
                tool_docs = await self.loader.load_all_tools()
            
            for tool_doc in tool_docs:
                schema = await self.loader.get_tool_schema(tool_doc['tool_id'], tenant_id)
                if schema:
                    tools.append(schema)
            
            return tools
            
        except Exception as e:
            logger.error(f"Failed to get available tools: {e}")
            return []
    
    def is_tool_registered(self, tool_id: str) -> bool:
        """Check if a tool is registered"""
        return self.registered_tools.get(tool_id, False)
    
    def clear_registry(self):
        """Clear the tool registry (for testing)"""
        self.registered_tools.clear()
        self.compiler.clear_cache()
        logger.info("Tool registry cleared")