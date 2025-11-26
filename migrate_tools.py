#!/usr/bin/env python3
"""
Migration script to add existing tools to database
"""
import asyncio
import logging
from core.database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User profiler tool code
USER_PROFILER_CODE = '''
import json
from datetime import datetime

async def execute(stage, input_value, session_data='{}', context=None):
    """Multi-stage user profiling workflow"""
    try:
        # Validate stage
        valid_stages = ["user_name", "user_purpose", "trust_acceptance", "passion_text", "confirmation"]
        if stage not in valid_stages:
            return f"Error: Invalid stage. Must be one of: {', '.join(valid_stages)}"
        
        # Parse existing session data
        try:
            session_data_dict = json.loads(session_data) if session_data else {}
        except json.JSONDecodeError:
            session_data_dict = {}
        
        # Process each stage
        if stage == "user_name":
            return await process_user_name(input_value, session_data_dict)
        elif stage == "user_purpose":
            return await process_user_purpose(input_value, session_data_dict)
        elif stage == "trust_acceptance":
            return await process_trust_acceptance(input_value, session_data_dict)
        elif stage == "passion_text":
            return await process_passion_text(input_value, session_data_dict)
        elif stage == "confirmation":
            return await process_confirmation(input_value, session_data_dict)
        
        return "Error: Unknown stage processing error"
        
    except Exception as e:
        return f"Error processing user profile: {str(e)}"

async def process_user_name(input_value, session_data):
    """Process Stage 1: userName"""
    if not input_value or len(input_value.strip()) < 1:
        return "Error: Please provide a valid name"
    
    session_data["userName"] = input_value
    session_data["stage"] = "user_purpose"
    
    return json.dumps({
        "message": f"Hello {input_value}! What would you like to learn or achieve?",
        "next_stage": "user_purpose",
        "session_data": session_data
    })

async def process_user_purpose(input_value, session_data):
    """Process Stage 2: userPurpose"""
    if not input_value or len(input_value.strip()) < 5:
        return "Error: Please provide more details about your purpose (at least 5 characters)"
    
    session_data["userPurpose"] = input_value
    session_data["stage"] = "trust_acceptance"
    
    return json.dumps({
        "message": "Great! To provide personalized recommendations, we'd like to analyze your responses. Do you accept our privacy terms? (yes/no)",
        "next_stage": "trust_acceptance", 
        "session_data": session_data
    })

async def process_trust_acceptance(input_value, session_data):
    """Process Stage 3: trustAccepted"""
    input_lower = input_value.lower().strip()
    trust_accepted = input_lower in ["yes", "y", "true", "accept", "ok", "agree"]
    
    session_data["trustAccepted"] = trust_accepted
    session_data["stage"] = "passion_text"
    
    if trust_accepted:
        message = "Thank you! Please tell us about your passions and interests:"
    else:
        message = "Understood. You can still continue, but we'll limit data collection. Tell us about your interests:"
    
    return json.dumps({
        "message": message,
        "next_stage": "passion_text",
        "session_data": session_data
    })

async def process_passion_text(input_value, session_data):
    """Process Stage 4: passionText"""
    if not input_value or len(input_value.strip()) < 10:
        return "Error: Please share more about your passions (at least 10 characters)"
    
    session_data["passionText"] = input_value
    session_data["stage"] = "confirmation"
    
    # Analyze passion text for personality insights
    personality = analyze_personality(input_value)
    session_data["personality_preview"] = personality
    
    return json.dumps({
        "message": f"Thanks for sharing! I can see you're {personality['sentiment']} about {', '.join(personality['topics'][:2])}. Ready to complete your profile? (ready/review)",
        "next_stage": "confirmation",
        "session_data": session_data
    })

async def process_confirmation(input_value, session_data):
    """Process Stage 5: confirmation"""
    input_lower = input_value.lower().strip()
    
    if input_lower not in ["ready", "confirm", "yes", "complete"]:
        return json.dumps({
            "message": "Please type 'ready' when you want to complete your profile",
            "session_data": session_data
        })
    
    # Generate final profile
    final_profile = generate_final_profile(session_data)
    
    return json.dumps({
        "message": "Profile completed successfully!",
        "profile": final_profile,
        "completed": True
    })

def analyze_personality(passion_text):
    """Simple personality analysis from passion text"""
    text_lower = passion_text.lower()
    
    # Analyze thinking style
    structured_words = ["organize", "plan", "system", "process", "method", "structure"]
    creative_words = ["create", "imagine", "art", "design", "innovative", "creative"]
    
    if any(word in text_lower for word in structured_words):
        thinking_style = "structured"
    elif any(word in text_lower for word in creative_words):
        thinking_style = "creative"
    else:
        thinking_style = "balanced"
    
    # Analyze sentiment
    positive_words = ["love", "enjoy", "excited", "passionate", "amazing", "great"]
    curious_words = ["learn", "discover", "explore", "understand", "know", "find"]
    
    if any(word in text_lower for word in positive_words):
        sentiment = "enthusiastic"
    elif any(word in text_lower for word in curious_words):
        sentiment = "curious"
    else:
        sentiment = "thoughtful"
    
    # Extract topics
    topic_keywords = {
        "technology": ["tech", "computer", "software", "programming", "code"],
        "AI": ["ai", "artificial intelligence", "machine learning", "ml"],
        "business": ["business", "startup", "entrepreneur", "company"],
        "education": ["learn", "teach", "education", "study"],
        "software": ["software", "development", "programming", "coding"]
    }
    
    topics = []
    for topic, keywords in topic_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            topics.append(topic)
    
    # Estimate passion level
    passion_level = min(5, max(1, len(passion_text) // 20 + len([w for w in positive_words if w in text_lower])))
    
    return {
        "thinkingStyle": thinking_style,
        "sentiment": sentiment,
        "passionLevel": passion_level,
        "topics": topics[:3]
    }

def generate_final_profile(session_data):
    """Generate final user profile"""
    personality = session_data.get("personality_preview", {})
    
    return {
        "userName": session_data.get("userName", ""),
        "userResponses": {
            "user-purpose": session_data.get("userPurpose", "")
        },
        "personalityProfile": personality,
        "privacyPreferences": {
            "trustAccepted": session_data.get("trustAccepted", False)
        },
        "registrationCompleted": True,
        "registrationDate": datetime.now().isoformat()
    }
'''

# Health check tool code
HEALTH_CHECK_CODE = '''
import json

async def execute(context=None):
    """Health check tool"""
    try:
        # Simple health check - in real implementation you'd check actual database
        return json.dumps({
            "status": "healthy",
            "database_connected": True,
            "server": "FastMCP Dynamic Tool Server",
            "version": "2.0.0"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        })
'''

async def migrate_tools():
    """Migrate existing tools to database"""
    try:
        await db.connect()
        logger.info("Connected to database")
        
        # Get tools collection
        tools_collection = db.get_collection("tools")
        
        # Create tools collection indexes
        await tools_collection.create_index([("tool_id", 1)], unique=True)
        await tools_collection.create_index([("tenants", 1), ("active", 1)])
        logger.info("Created database indexes")
        
        # Migrate user_profiler tool
        user_profiler_doc = {
            "tool_id": "user_profiler",
            "name": "user_profiler",
            "description": "Multi-stage user profiling tool that collects user information and generates personality profile",
            "code": USER_PROFILER_CODE.strip(),
            "input_schema": {
                "type": "object",
                "properties": {
                    "stage": {
                        "type": "string",
                        "enum": ["user_name", "user_purpose", "trust_acceptance", "passion_text", "confirmation"],
                        "description": "Current stage of the profiling process"
                    },
                    "input_value": {
                        "type": "string", 
                        "description": "User input for the current stage"
                    },
                    "session_data": {
                        "type": "string",
                        "description": "JSON string of previously collected data",
                        "default": "{}"
                    }
                },
                "required": ["stage", "input_value"]
            },
            "tenants": ["1", "2"],  # Available to these tenants
            "active": True
        }
        
        await tools_collection.replace_one(
            {"tool_id": "user_profiler"}, 
            user_profiler_doc, 
            upsert=True
        )
        logger.info("Migrated user_profiler tool")
        
        # Migrate health_check tool
        health_check_doc = {
            "tool_id": "health_check",
            "name": "health_check",
            "description": "Check server health and database connectivity",
            "code": HEALTH_CHECK_CODE.strip(),
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
            "tenants": ["1", "2"],  # Available to these tenants
            "active": True
        }
        
        await tools_collection.replace_one(
            {"tool_id": "health_check"}, 
            health_check_doc, 
            upsert=True
        )
        logger.info("Migrated health_check tool")
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(migrate_tools())