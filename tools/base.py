from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseMCPTool(ABC):
    """Base class for MCP-compliant tools"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name in snake_case"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass
    
    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """JSON schema for tool inputs"""
        pass
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any], tenant_id: str) -> str:
        """Execute tool with tenant context - return result string or error string"""
        pass