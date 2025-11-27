#!/usr/bin/env python3
"""
Update the input_schema for user_profiler to match the text analyzer code
"""
import asyncio
from dotenv import load_dotenv
from core.database import db

load_dotenv()

async def update_user_profiler_schema():
    try:
        await db.connect()
        print("Connected to database successfully")
        
        collection = db.get_collection("tools")
        
        # New schema to match the text analyzer code
        new_schema = {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text content to analyze"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["basic", "sentiment", "full"],
                    "default": "full",
                    "description": "Type of analysis to perform: basic (word/char count), sentiment (includes sentiment analysis), or full (comprehensive analysis)"
                }
            },
            "required": ["text"]
        }
        
        # Update the user_profiler tool
        result = await collection.update_one(
            {"tool_id": "user_profiler"},
            {"$set": {"input_schema": new_schema}}
        )
        
        if result.matched_count > 0:
            print("✅ Successfully updated user_profiler input_schema!")
            print(f"   Matched: {result.matched_count} document(s)")
            print(f"   Modified: {result.modified_count} document(s)")
        else:
            print("❌ No user_profiler tool found to update")
            
        # Verify the update
        print("\n=== Verifying update ===")
        updated_tool = await collection.find_one({"tool_id": "user_profiler"})
        if updated_tool:
            print("New input_schema:")
            import json
            print(json.dumps(updated_tool['input_schema'], indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(update_user_profiler_schema())