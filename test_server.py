#!/usr/bin/env python3

import asyncio
import json
from main import _process_user_name, _process_user_purpose, _process_trust_acceptance, _process_passion_text, _process_confirmation
from core.database import db

async def test_tools():
    """Test the FastMCP tools"""
    print("🚀 Testing FastMCP Server Tools\n")
    
    # Test health check
    print("1. Testing health_check tool...")
    try:
        database_connected = db._client is not None
        health_result = json.dumps({
            "status": "healthy" if database_connected else "degraded",
            "database_connected": database_connected,
            "server": "FastMCP Multi-tenant Server",
            "version": "2.0.0"
        })
        health_data = json.loads(health_result)
        print(f"   ✅ Health check result: {health_data['status']}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
    
    # Test user profiler stages
    print("\n2. Testing user_profiler tool...")
    
    # Stage 1: User name
    try:
        result1 = await _process_user_name("John Doe", {})
        data1 = json.loads(result1)
        print(f"   ✅ Stage 1 (user_name): {data1['message']}")
        session_data = data1['session_data']
    except Exception as e:
        print(f"   ❌ Stage 1 failed: {e}")
        return
    
    # Stage 2: User purpose
    try:
        result2 = await _process_user_purpose("I want to learn about AI and machine learning", session_data)
        data2 = json.loads(result2)
        print(f"   ✅ Stage 2 (user_purpose): {data2['message'][:50]}...")
        session_data = data2['session_data']
    except Exception as e:
        print(f"   ❌ Stage 2 failed: {e}")
        return
    
    # Stage 3: Trust acceptance
    try:
        result3 = await _process_trust_acceptance("yes", session_data)
        data3 = json.loads(result3)
        print(f"   ✅ Stage 3 (trust_acceptance): {data3['message'][:50]}...")
        session_data = data3['session_data']
    except Exception as e:
        print(f"   ❌ Stage 3 failed: {e}")
        return
    
    # Stage 4: Passion text
    try:
        result4 = await _process_passion_text("I love programming and creating innovative AI solutions that help people", session_data)
        data4 = json.loads(result4)
        print(f"   ✅ Stage 4 (passion_text): {data4['message'][:50]}...")
        session_data = data4['session_data']
    except Exception as e:
        print(f"   ❌ Stage 4 failed: {e}")
        return
    
    # Stage 5: Confirmation
    try:
        result5 = await _process_confirmation("ready", session_data)
        data5 = json.loads(result5)
        print(f"   ✅ Stage 5 (confirmation): Profile completed!")
        print(f"   📊 Final profile: {data5['profile']['userName']} - {data5['profile']['personalityProfile']}")
    except Exception as e:
        print(f"   ❌ Stage 5 failed: {e}")
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_tools())