import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from fastmcp import FastMCP

from core.database import db
from core.dynamic_registry import DynamicToolRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Multi-tenant MCP Server")

# Initialize dynamic tool registry
dynamic_registry = DynamicToolRegistry(mcp, db)

# API key for authentication
API_KEY = os.getenv("API_KEY", "dev-key-123")

def authenticate(headers: Dict[str, str]) -> Dict[str, Any]:
    """Simple API key authentication"""
    auth_header = headers.get("authorization", "")
    if not auth_header or not auth_header.startswith("Bearer "):
        return {"error": "Missing or invalid authorization header", "authenticated": False}
    
    token = auth_header.split(" ")[1]
    if token != API_KEY:
        return {"error": "Invalid API key", "authenticated": False}
    
    # Return tenant context (simplified - in production, extract from token)
    return {
        "authenticated": True,
        "tenant_id": "1",  # TODO: Extract from token
        "api_key": token
    }

# All tools are now loaded dynamically from database
# The user_profiler, health_check and other tools will be registered automatically
# when the dynamic registry loads them from the database

if __name__ == "__main__":
    # Initialize database and load tools
    import asyncio
    
    async def init_server():
        try:
            # Connect to database
            await db.connect()
            logger.info("Database connected successfully")
            
            # Load and register dynamic tools
            await dynamic_registry.load_and_register_tools()
            logger.info("Dynamic tools loaded and registered")
            
        except Exception as e:
            logger.error(f"Server initialization failed: {e}")
            raise
    
    # Initialize server before starting
    asyncio.run(init_server())
    
    # Start FastMCP server with streamable HTTP transport
    mcp.run(
        transport="http",
        host="0.0.0.0", 
        port=8002,
        path="/mcp"
    )
