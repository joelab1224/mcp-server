import json
import re
from datetime import datetime
from typing import Dict, Any
from ..base import BaseMCPTool

class UserProfiler(BaseMCPTool):
    """User onboarding and profiling tool - collects user information in stages"""
    
    @property
    def name(self) -> str:
        return "user_profiler"
    
    @property
    def description(self) -> str:
        return "Multi-stage user profiling tool that collects user information and generates personality profile"
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
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
                    "description": "JSON string of previously collected data (optional)",
                    "default": "{}"
                }
            },
            "required": ["stage", "input_value"]
        }
    
    async def execute(self, arguments: Dict[str, Any], tenant_id: str) -> str:
        """Execute user profiling workflow"""
        try:
            stage = arguments.get("stage")
            input_value = arguments.get("input_value", "").strip()
            session_data_str = arguments.get("session_data", "{}")
            
            # Parse existing session data
            try:
                session_data = json.loads(session_data_str) if session_data_str else {}
            except json.JSONDecodeError:
                session_data = {}
            
            # Validate stage
            if stage not in ["user_name", "user_purpose", "trust_acceptance", "passion_text", "confirmation"]:
                return "Error: Invalid stage. Must be one of: user_name, user_purpose, trust_acceptance, passion_text, confirmation"
            
            # Process each stage
            if stage == "user_name":
                return await self._process_user_name(input_value, session_data)
                
            elif stage == "user_purpose":
                return await self._process_user_purpose(input_value, session_data)
                
            elif stage == "trust_acceptance":
                return await self._process_trust_acceptance(input_value, session_data)
                
            elif stage == "passion_text":
                return await self._process_passion_text(input_value, session_data)
                
            elif stage == "confirmation":
                return await self._process_confirmation(input_value, session_data)
            
            return "Error: Unknown stage processing error"
            
        except Exception as e:
            return f"Error processing user profile: {str(e)}"
    
    async def _process_user_name(self, input_value: str, session_data: Dict) -> str:
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
    
    async def _process_user_purpose(self, input_value: str, session_data: Dict) -> str:
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
    
    async def _process_trust_acceptance(self, input_value: str, session_data: Dict) -> str:
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
    
    async def _process_passion_text(self, input_value: str, session_data: Dict) -> str:
        """Process Stage 4: passionText"""
        if not input_value or len(input_value.strip()) < 10:
            return "Error: Please share more about your passions (at least 10 characters)"
        
        session_data["passionText"] = input_value
        session_data["stage"] = "confirmation"
        
        # Analyze passion text for personality insights
        personality = self._analyze_personality(input_value)
        session_data["personality_preview"] = personality
        
        return json.dumps({
            "message": f"Thanks for sharing! I can see you're {personality['sentiment']} about {', '.join(personality['topics'][:2])}. Ready to complete your profile? (ready/review)",
            "next_stage": "confirmation",
            "session_data": session_data
        })
    
    async def _process_confirmation(self, input_value: str, session_data: Dict) -> str:
        """Process Stage 5: confirmation"""
        input_lower = input_value.lower().strip()
        
        if input_lower not in ["ready", "confirm", "yes", "complete"]:
            return json.dumps({
                "message": "Please type 'ready' when you want to complete your profile",
                "session_data": session_data
            })
        
        # Generate final profile
        final_profile = self._generate_final_profile(session_data)
        
        return json.dumps({
            "message": "Profile completed successfully!",
            "profile": final_profile,
            "completed": True
        })
    
    def _analyze_personality(self, passion_text: str) -> Dict[str, Any]:
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
        
        # Extract topics (simple keyword matching)
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
        
        # Estimate passion level (1-5 based on text length and enthusiasm)
        passion_level = min(5, max(1, len(passion_text) // 20 + len([w for w in positive_words if w in text_lower])))
        
        return {
            "thinkingStyle": thinking_style,
            "sentiment": sentiment,
            "passionLevel": passion_level,
            "topics": topics[:3]  # Limit to top 3 topics
        }
    
    def _generate_final_profile(self, session_data: Dict) -> Dict[str, Any]:
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