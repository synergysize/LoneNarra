#!/usr/bin/env python3
"""
LLM Integration Module for Narrahunt Phase 2.

Provides integration with LLM services (Anthropic Claude and OpenAI) for 
analyzing and enhancing discoveries.
"""

import os
import json
import logging
import requests
import time
from typing import Dict, Any, List, Optional, Union

# Configure logging
base_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(base_dir, 'logs'), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(base_dir, 'logs', 'llm_integration.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('llm_integration')

# LLM API Keys
CLAUDE_API_KEY = "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"
OPENAI_API_KEY = "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"

class LLMIntegration:
    """
    Provides integration with LLM services for content analysis and enhancement.
    """
    
    def __init__(self, use_claude: bool = True, use_openai: bool = False):
        """
        Initialize the LLM integration module.
        
        Args:
            use_claude: Whether to use Claude as the LLM
            use_openai: Whether to use OpenAI as the LLM
        """
        self.use_claude = use_claude
        self.use_openai = use_openai
        
        if not use_claude and not use_openai:
            logger.warning("No LLM service selected. Defaulting to Claude.")
            self.use_claude = True
        
        # Initialize API keys
        self.claude_api_key = CLAUDE_API_KEY
        self.openai_api_key = OPENAI_API_KEY
        
        # Cache for API responses
        self.response_cache = {}
        
        logger.info(f"LLM Integration initialized. Using Claude: {use_claude}, Using OpenAI: {use_openai}")
    
    def analyze(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze text content using the selected LLM.
        
        Args:
            text: The text to analyze
            context: Optional context for the analysis
            
        Returns:
            Dictionary with analysis results
        """
        if not text:
            return {
                "entities": [],
                "sentiment": "neutral",
                "relevance_score": 0.0,
                "narrative_score": 0.0,
                "summary": ""
            }
        
        # Prepare prompt
        if context:
            prompt = f"Context: {context}\n\nText to analyze: {text}\n\n"
        else:
            prompt = f"Text to analyze: {text}\n\n"
        
        prompt += """Please analyze this text and return the following:
1. Entities: List any people, organizations, projects, or other named entities
2. Sentiment: Overall sentiment (positive, negative, neutral)
3. Relevance Score: How relevant is this text to the context (0.0 to 1.0)
4. Narrative Value: How valuable is this for a narrative (0.0 to 1.0)
5. Summary: A brief 1-2 sentence summary

Format your response as JSON with these fields.
"""
        
        # Calculate cache key
        cache_key = f"{hash(prompt)}"
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]
        
        # Get response from LLM
        if self.use_claude:
            result = self._call_claude(prompt)
        elif self.use_openai:
            result = self._call_openai(prompt)
        else:
            logger.error("No LLM service available")
            return {
                "entities": [],
                "sentiment": "neutral",
                "relevance_score": 0.5,
                "narrative_score": 0.5,
                "summary": "No LLM service available for analysis."
            }
        
        # Parse the response
        try:
            # Try to extract JSON from the response
            json_str = self._extract_json(result)
            data = json.loads(json_str)
            
            # Ensure all fields are present
            analysis = {
                "entities": data.get("entities", []),
                "sentiment": data.get("sentiment", "neutral"),
                "relevance_score": float(data.get("relevance_score", 0.5)),
                "narrative_score": float(data.get("narrative_score", 0.5)),
                "summary": data.get("summary", "")
            }
            
            # Cache the result
            self.response_cache[cache_key] = analysis
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.debug(f"Raw response: {result}")
            
            # Return a fallback analysis
            return {
                "entities": [],
                "sentiment": "neutral",
                "relevance_score": 0.5,
                "narrative_score": 0.5,
                "summary": "Failed to analyze text."
            }
    
    def _call_claude(self, prompt: str) -> str:
        """
        Call the Claude API.
        
        Args:
            prompt: The prompt to send to Claude
            
        Returns:
            Claude's response text
        """
        try:
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.claude_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            data = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 1000,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result['content'][0]['text']
                logger.info("Successfully received response from Claude")
                return content
            else:
                logger.error(f"Claude API error: {response.status_code} - {response.text}")
                return "{}"
                
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return "{}"
    
    def _call_openai(self, prompt: str) -> str:
        """
        Call the OpenAI API.
        
        Args:
            prompt: The prompt to send to OpenAI
            
        Returns:
            OpenAI's response text
        """
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                logger.info("Successfully received response from OpenAI")
                return content
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return "{}"
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return "{}"
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from a text response.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            The extracted JSON string
        """
        # Look for JSON block
        if "```json" in text and "```" in text.split("```json", 1)[1]:
            return text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text and "```" in text.split("```", 1)[1]:
            json_text = text.split("```", 1)[1].split("```", 1)[0].strip()
            try:
                json.loads(json_text)  # Test if it's valid JSON
                return json_text
            except:
                pass
        
        # If no JSON block, look for the first { and last }
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            json_text = text[start:end].strip()
            try:
                json.loads(json_text)  # Test if it's valid JSON
                return json_text
            except:
                pass
        
        # If all else fails, return an empty JSON object
        return '{}'
    
    def generate_research_strategy(self, objective: str, entity: str) -> Dict[str, List[str]]:
        """
        Generate a research strategy for a given objective and entity.
        
        Args:
            objective: The research objective
            entity: The target entity
            
        Returns:
            Dictionary with research strategy
        """
        prompt = f"""
Generate a detailed research strategy for the following objective:

Objective: {objective}
Entity: {entity}

Please identify:
1. Key sources to check (websites, forums, archives)
2. Specific search queries to use
3. Types of information to look for
4. Historical periods or events to focus on

Format your response as a JSON object with these sections.
"""
        
        if self.use_claude:
            result = self._call_claude(prompt)
        elif self.use_openai:
            result = self._call_openai(prompt)
        else:
            logger.error("No LLM service available")
            return {
                "sources": [],
                "search_queries": [],
                "information_types": [],
                "time_periods": []
            }
        
        try:
            json_str = self._extract_json(result)
            data = json.loads(json_str)
            
            strategy = {
                "sources": data.get("sources", []),
                "search_queries": data.get("search_queries", []),
                "information_types": data.get("information_types", []),
                "time_periods": data.get("time_periods", [])
            }
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error parsing research strategy: {e}")
            return {
                "sources": [],
                "search_queries": [],
                "information_types": [],
                "time_periods": []
            }
    
    def evaluate_discovery(self, discovery: Dict[str, Any], objective: str) -> float:
        """
        Evaluate a discovery for its narrative value.
        
        Args:
            discovery: The discovery to evaluate
            objective: The research objective
            
        Returns:
            Narrative value score (0.0 to 1.0)
        """
        prompt = f"""
Evaluate this discovery for its narrative value:

Objective: {objective}
Content: {discovery.get('content', '')}
Source: {discovery.get('url', 'Unknown')}

On a scale of 0.0 to 1.0, how valuable is this discovery for building a narrative?
Consider factors like:
- Uniqueness
- Historical significance
- Emotional impact
- Connection to the objective
- Potential for storytelling

Return only a number between 0.0 and 1.0.
"""
        
        if self.use_claude:
            result = self._call_claude(prompt)
        elif self.use_openai:
            result = self._call_openai(prompt)
        else:
            logger.error("No LLM service available")
            return 0.5
        
        try:
            # Extract the number from the response
            import re
            number_match = re.search(r'(\d+\.\d+|\d+)', result)
            if number_match:
                score = float(number_match.group(1))
                # Ensure score is between 0.0 and 1.0
                score = max(0.0, min(1.0, score))
                return score
            else:
                return 0.5
        except Exception as e:
            logger.error(f"Error parsing evaluation score: {e}")
            return 0.5

# Test the LLM integration
if __name__ == "__main__":
    print("Testing LLM Integration")
    
    llm = LLMIntegration(use_claude=True, use_openai=False)
    
    # Test text analysis
    test_text = """
    Vitalik Buterin created Ethereum in 2015 after being involved in the Bitcoin community.
    He published the Ethereum whitepaper in 2013 and launched the network with co-founders
    including Gavin Wood and Joseph Lubin. The project has since become one of the most
    important blockchain platforms for smart contracts and decentralized applications.
    """
    
    analysis = llm.analyze(test_text, context="Looking for information about Ethereum founders")
    print("\nText Analysis:")
    print(json.dumps(analysis, indent=2))
    
    # Test research strategy generation
    strategy = llm.generate_research_strategy(
        "Find name artifacts around Vitalik Buterin",
        "Vitalik Buterin"
    )
    print("\nResearch Strategy:")
    print(json.dumps(strategy, indent=2))
    
    # Test discovery evaluation
    discovery = {
        "content": "Vitalik Buterin used the username 'vitalik_btc' on the Bitcoin forum before creating Ethereum.",
        "url": "https://bitcointalk.org/index.php?action=profile;u=11772"
    }
    
    score = llm.evaluate_discovery(discovery, "Find name artifacts around Vitalik Buterin")
    print(f"\nDiscovery Evaluation Score: {score}")
    
    print("\nLLM Integration test complete.")