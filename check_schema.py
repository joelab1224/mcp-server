#!/usr/bin/env python3
import asyncio
from dotenv import load_dotenv
from core.database import db
import json

load_dotenv()

async def check_schemas():
    try:
        await db.connect()
        collection = db.get_collection("tools")
        
        async for tool in collection.find({"active": True}):
            print(f"\n=== {tool['tool_id']} INPUT SCHEMA ===")
            schema = tool.get('input_schema', {})
            print(json.dumps(schema, indent=2))
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_schemas())