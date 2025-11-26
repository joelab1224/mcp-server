from typing import Dict, List, Any
from .base import BaseMCPTool
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Auto-registration system for MCP tools"""
    
    def __init__(self):
        self._tools: Dict[str, BaseMCPTool] = {}
    
    def auto_register(self, tool_class):
        """Auto-register tool when imported"""
        try:
            tool = tool_class()
            self._tools[tool.name] = tool
            logger.info(f"Registered tool: {tool.name}")
        except Exception as e:
            logger.error(f"Failed to register tool {tool_class.__name__}: {e}")
    
    def get_tool(self, name: str) -> BaseMCPTool:
        """Get tool by name"""
        return self._tools.get(name)
    
    def get_available_tools(self, enabled_tool_names: List[str]) -> Dict[str, BaseMCPTool]:
        """Return only enabled tools for tenant"""
        return {name: tool for name, tool in self._tools.items() 
                if name in enabled_tool_names}
    
    def list_all_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with MCP schema"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.get_input_schema()
            }
            for tool in self._tools.values()
        ]
    
    def list_tools_for_tenant(self, enabled_tool_names: List[str]) -> List[Dict[str, Any]]:
        """List enabled tools for tenant with MCP schema"""
        available_tools = self.get_available_tools(enabled_tool_names)
        return [
            {
                "name": tool.name,
                "description": tool.description,  
                "inputSchema": tool.get_input_schema()
            }
            for tool in available_tools.values()
        ]

    def reload_tools(self):
        """Clear and reload all tools from builtin modules"""
        self._tools.clear()
        
        # Re-import builtin tools to trigger auto-registration
        import importlib
        import tools.builtin
        importlib.reload(tools.builtin)
        
        logger.info(f"Registry reloaded: {len(self._tools)} tools available")
        return len(self._tools)

# Global registry instance
registry = ToolRegistry()
