"""
Text Analyzer Tool - Example for Database Upload
This tool analyzes text and provides insights like word count, sentiment, and key topics.
"""

# This is the execute function that will be stored in the database
async def execute(text, analysis_type="full", context=None):
    """
    Analyze text and return insights
    
    Args:
        text (str): Text to analyze
        analysis_type (str): Type of analysis - "basic", "sentiment", or "full"
        context: Tool execution context (injected automatically)
    
    Returns:
        str: JSON string with analysis results
    """
    import json
    import re
    from datetime import datetime
    
    if not text or not isinstance(text, str):
        return json.dumps({"error": "Text parameter is required and must be a string"})
    
    text = text.strip()
    if len(text) == 0:
        return json.dumps({"error": "Text cannot be empty"})
    
    # Basic analysis
    word_count = len(text.split())
    char_count = len(text)
    sentence_count = len([s for s in re.split(r'[.!?]+', text) if s.strip()])
    
    result = {
        "text_length": char_count,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_words_per_sentence": round(word_count / max(sentence_count, 1), 2),
        "analysis_type": analysis_type,
        "timestamp": datetime.now().isoformat()
    }
    
    if analysis_type in ["sentiment", "full"]:
        # Simple sentiment analysis
        positive_words = [
            "good", "great", "excellent", "amazing", "wonderful", "fantastic", 
            "love", "like", "enjoy", "happy", "pleased", "satisfied", "awesome"
        ]
        negative_words = [
            "bad", "terrible", "awful", "hate", "dislike", "angry", "sad", 
            "disappointed", "frustrated", "annoyed", "horrible", "worst"
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        result["sentiment"] = {
            "overall": sentiment,
            "positive_indicators": positive_count,
            "negative_indicators": negative_count,
            "confidence": abs(positive_count - negative_count) / max(word_count, 1)
        }
    
    if analysis_type == "full":
        # Additional analysis for full mode
        words = text.lower().split()
        
        # Most common words (excluding very short ones)
        word_freq = {}
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if len(clean_word) > 2:  # Ignore very short words
                word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
        
        # Top 5 most frequent words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Reading time estimate (average reading speed: 200 words per minute)
        reading_time_minutes = max(1, round(word_count / 200))
        
        result["detailed_analysis"] = {
            "top_words": [{"word": word, "frequency": count} for word, count in top_words],
            "estimated_reading_time_minutes": reading_time_minutes,
            "complexity_score": round(char_count / max(word_count, 1), 2)  # avg chars per word
        }
    
    return json.dumps(result, indent=2)

# Database document structure for this tool
DATABASE_DOCUMENT = {
    "tool_id": "text_analyzer",
    "name": "text_analyzer",
    "description": "Analyzes text content and provides insights including word count, sentiment analysis, and key metrics",
    "code": """async def execute(text, analysis_type="full", context=None):
    import json
    import re
    from datetime import datetime
    
    if not text or not isinstance(text, str):
        return json.dumps({"error": "Text parameter is required and must be a string"})
    
    text = text.strip()
    if len(text) == 0:
        return json.dumps({"error": "Text cannot be empty"})
    
    # Basic analysis
    word_count = len(text.split())
    char_count = len(text)
    sentence_count = len([s for s in re.split(r'[.!?]+', text) if s.strip()])
    
    result = {
        "text_length": char_count,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_words_per_sentence": round(word_count / max(sentence_count, 1), 2),
        "analysis_type": analysis_type,
        "timestamp": datetime.now().isoformat()
    }
    
    if analysis_type in ["sentiment", "full"]:
        # Simple sentiment analysis
        positive_words = [
            "good", "great", "excellent", "amazing", "wonderful", "fantastic", 
            "love", "like", "enjoy", "happy", "pleased", "satisfied", "awesome"
        ]
        negative_words = [
            "bad", "terrible", "awful", "hate", "dislike", "angry", "sad", 
            "disappointed", "frustrated", "annoyed", "horrible", "worst"
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > negative_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        result["sentiment"] = {
            "overall": sentiment,
            "positive_indicators": positive_count,
            "negative_indicators": negative_count,
            "confidence": abs(positive_count - negative_count) / max(word_count, 1)
        }
    
    if analysis_type == "full":
        # Additional analysis for full mode
        words = text.lower().split()
        
        # Most common words (excluding very short ones)
        word_freq = {}
        for word in words:
            clean_word = re.sub(r'[^\\w]', '', word)
            if len(clean_word) > 2:
                word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
        
        # Top 5 most frequent words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Reading time estimate (average 200 words per minute)
        reading_time_minutes = max(1, round(word_count / 200))
        
        result["detailed_analysis"] = {
            "top_words": [{"word": word, "frequency": count} for word, count in top_words],
            "estimated_reading_time_minutes": reading_time_minutes,
            "complexity_score": round(char_count / max(word_count, 1), 2)
        }
    
    return json.dumps(result, indent=2)""",
    "input_schema": {
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
    },
    "tenants": ["1"],  # Available to tenant 1
    "active": True
}

print("Tool created! Here's the database document to upload:")
print("=" * 50)
print(json.dumps(DATABASE_DOCUMENT, indent=2))