#!/usr/bin/env python3
"""
Quick script to check what tools are in the database and preview their code
"""
import asyncio
import os
from dotenv import load_dotenv
from core.database import db

load_dotenv()

async def check_tools():
    try:
        await db.connect()
        print("Connected to database successfully")
        
        collection = db.get_collection("tools")
        
        # Get all active tools
        tools = []
        async for tool in collection.find({"active": True}):
            tools.append(tool)
        
        print(f"\nFound {len(tools)} active tools:")
        print("=" * 60)
        
        for tool in tools:
            print(f"\nTool ID: {tool['tool_id']}")
            print(f"Name: {tool['name']}")
            print(f"Active: {tool['active']}")
            if 'tenants' in tool:
                print(f"Tenants: {tool['tenants']}")
            
            # Show first 300 characters of code
            code = tool.get('code', 'No code found')
            print(f"Code preview (first 300 chars):")
            print("-" * 40)
            print(code[:300] + ("..." if len(code) > 300 else ""))
            print("-" * 40)
            
            # Check for specific method names
            if 'process_user_name' in code:
                print("⚠️  Contains 'process_user_name' - this might be the problem!")
            if 'def execute(' in code:
                print("✅ Contains 'def execute(' - good!")
            
            print("=" * 60)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_tools())