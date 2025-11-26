#!/usr/bin/env python3

import asyncio
import logging
from main import mcp, db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def startup():
    """Initialize database before starting server"""
    try:
        await db.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

async def main():
    """Main server runner"""
    await startup()
    
    # Start FastMCP server with streamable HTTP transport
    logger.info("Starting FastMCP server on http://0.0.0.0:8002/mcp")
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8002,
        path="/mcp"
    )

if __name__ == "__main__":
    asyncio.run(main())