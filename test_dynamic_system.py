#!/usr/bin/env python3
"""
Test script for dynamic tools system
"""
import asyncio
import logging
from dotenv import load_dotenv

from core.database import db
from core.dynamic_registry import DynamicToolRegistry
from fastmcp import FastMCP

# Load environment
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_dynamic_system():
    """Test the complete dynamic tools system"""
    try:
        # Initialize FastMCP
        mcp = FastMCP("Test MCP Server")
        
        # Connect to database
        await db.connect()
        logger.info("Database connected")
        
        # Initialize dynamic registry
        registry = DynamicToolRegistry(mcp, db)
        
        # Load tools from database
        await registry.load_and_register_tools()
        logger.info("Tools loaded and registered")
        
        # Test tool compilation by checking cache
        user_profiler_tool = registry.compiler.get_compiled_tool("user_profiler")
        health_check_tool = registry.compiler.get_compiled_tool("health_check")
        
        if user_profiler_tool:
            logger.info(f"✅ user_profiler compiled: {user_profiler_tool.tool_id}")
        else:
            logger.error("❌ user_profiler not compiled")
            
        if health_check_tool:
            logger.info(f"✅ health_check compiled: {health_check_tool.tool_id}")
        else:
            logger.error("❌ health_check not compiled")
        
        # Test tool execution
        logger.info("Testing tool execution...")
        
        # Test health_check tool
        try:
            health_result = await registry.compiler.execute_tool("health_check", {})
            logger.info(f"✅ health_check result: {health_result}")
        except Exception as e:
            logger.error(f"❌ health_check failed: {e}")
        
        # Test user_profiler tool
        try:
            profiler_result = await registry.compiler.execute_tool(
                "user_profiler", 
                {"stage": "user_name", "input_value": "John Test"}
            )
            logger.info(f"✅ user_profiler result: {profiler_result[:100]}...")
        except Exception as e:
            logger.error(f"❌ user_profiler failed: {e}")
        
        logger.info("🎉 Dynamic tools system test completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(test_dynamic_system())