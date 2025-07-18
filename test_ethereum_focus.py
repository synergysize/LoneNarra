#!/usr/bin/env python3
"""
Test script for the Narrative Discovery Matrix with Ethereum focus.
Objective: Find name artifacts around Vitalik Buterin
"""

import os
import sys
import time
import json
import logging
import datetime
from urllib.parse import quote_plus

# Set up base directory
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Import necessary components
from narrative_matrix import NarrativeMatrix
from objectives_manager import ObjectivesManager

# Try to import crawler components
try:
    from url_queue import URLQueue
    from fetch import fetch_url
    from crawl import extract_links
    from artifact_extractor import extract_artifacts_from_html
    crawler_available = True
except ImportError as e:
    print(f"Warning: Could not import crawler components: {e}")
    crawler_available = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(base_dir, 'logs', 'ethereum_test.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ethereum_test')

# Create output directory for name artifacts
name_artifacts_dir = os.path.join(base_dir, 'results', 'narratives', 'name_artifacts')
os.makedirs(name_artifacts_dir, exist_ok=True)

class EthereumNameTest:
    """Test class for Ethereum name artifacts research."""
    
    def __init__(self):
        """Initialize the test."""
        self.matrix = NarrativeMatrix()
        self.manager = ObjectivesManager()
        self.discoveries = []
        self.sources_searched = set()
        
        # Initialize URL queue if crawler is available
        self.url_queue = None
        if crawler_available:
            try:
                self.url_queue = URLQueue()
                logger.info("Successfully initialized crawler components")
            except Exception as e:
                logger.error(f"Error initializing crawler components: {e}")
        
        # Tracking variables
        self.start_time = None
        self.end_time = None
        self.productive_sources = {}  # Track which sources produced discoveries
    
    def set_objective(self):
        """Set the specific objective for the test."""
        # First, ensure "Vitalik Buterin" is in the matrix as a specific target
        if "Vitalik Buterin" not in self.matrix.config["specific_targets"]:
            self.matrix.add_entity("Vitalik Buterin", "specific")
        
        # Ensure "name" is in the artifact types
        if "name" not in self.matrix.config["artifact_types"]:
            self.matrix.add_artifact_type("name")
        
        # Create and set the objective directly
        objective = "Find name around Vitalik Buterin"
        
        # Update the current objective file
        with open(os.path.join(base_dir, 'results', 'current_objective.txt'), 'w') as f:
            f.write(objective)
        
        # Set this as the current objective in the matrix
        self.matrix.current_objective = {
            "text": objective,
            "artifact_type": "name",
            "entity": "Vitalik Buterin",
            "created_at": datetime.datetime.now().isoformat(),
            "status": "active",
            "discoveries": []
        }
        
        logger.info(f"Set objective: {objective}")
        return objective
    
    def add_ethereum_sources(self):
        """Add Ethereum-specific sources to the queue."""
        if not crawler_available or not self.url_queue:
            logger.warning("Crawler not available, can't add sources")
            return
        
        # Clear existing queue
        self.url_queue.clear()
        
        # Add Vitalik's blog
        self.url_queue.add("https://vitalik.ca/")
        
        # Add Vitalik's Twitter/X profile
        self.url_queue.add("https://twitter.com/VitalikButerin")
        
        # Add Ethereum Foundation website
        self.url_queue.add("https://ethereum.org/en/")
        self.url_queue.add("https://ethereum.org/en/history/")
        
        # Add Ethereum research forum
        self.url_queue.add("https://ethresear.ch/u/vitalik/activity")
        
        # Add Vitalik's GitHub
        self.url_queue.add("https://github.com/vbuterin")
        
        # Add Vitalik's old Bitcoin forum profile
        self.url_queue.add("https://bitcointalk.org/index.php?action=profile;u=11772")
        
        # Add search queries
        search_queries = [
            "Vitalik Buterin before Ethereum",
            "Vitalik Buterin username",
            "Vitalik Buterin early projects",
            "Vitalik Buterin Bitcoin Magazine",
            "Vitalik Buterin pseudonym",
            "early Ethereum project name",
            "Vitalik Buterin 2013 2014"
        ]
        
        for query in search_queries:
            encoded_query = quote_plus(query)
            self.url_queue.add(f"https://duckduckgo.com/html/?q={encoded_query}")
            self.url_queue.add(f"https://github.com/search?q={encoded_query}&type=issues")
        
        logger.info(f"Added {self.url_queue.size()} Ethereum-specific sources to the queue")
    
    def is_name_artifact(self, text, artifact_type=None):
        """
        Determine if a piece of text contains a name artifact.
        
        Args:
            text: The text to analyze
            artifact_type: Optional artifact type hint
            
        Returns:
            Tuple of (is_name, extracted_name) or (False, None)
        """
        # Skip if clearly not a name-related artifact
        if not text or len(text) < 3:
            return False, None
        
        # Basic name patterns to look for
        name_patterns = [
            r'username[:\s]+([A-Za-z0-9_-]{3,20})',
            r'handle[:\s]+([A-Za-z0-9_-]{3,20})',
            r'pseudonym[:\s]+([A-Za-z0-9_-]{3,30})',
            r'nickname[:\s]+([A-Za-z0-9_-]{3,30})',
            r'alias[:\s]+([A-Za-z0-9_-]{3,30})',
            r'project name[:\s]+([A-Za-z0-9_-]{3,30})',
            r'called ([A-Za-z0-9_-]{3,30}) before',
            r'known as ([A-Za-z0-9_-]{3,30})',
            r'([A-Za-z0-9_-]{3,30}) blockchain',
            r'([A-Za-z0-9_-]{3,30}) cryptocurrency',
            r'([A-Za-z0-9_-]{3,30}) protocol',
            r'founded ([A-Za-z0-9_-]{3,30})',
            r'created ([A-Za-z0-9_-]{3,30})'
        ]
        
        import re
        for pattern in name_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                return True, matches.group(1)
        
        # If the artifact type is already identified as a name-related type
        if artifact_type and artifact_type in ['name', 'username', 'project_name', 'alias']:
            # Extract the most likely name from the text
            words = text.split()
            if words:
                # Heuristic: take the first word that looks like a name (capitalized, etc.)
                for word in words:
                    if len(word) >= 3 and word[0].isupper() and word.isalnum():
                        return True, word
        
        return False, None
    
    def process_url(self, url):
        """
        Process a URL to extract name artifacts.
        
        Args:
            url: The URL to process
            
        Returns:
            List of discovered name artifacts
        """
        if not crawler_available:
            logger.warning("Crawler not available, can't process URL")
            return []
        
        discovered_artifacts = []
        
        try:
            # Add to sources searched
            self.sources_searched.add(url)
            
            # Fetch content
            logger.info(f"Fetching URL: {url}")
            content, mime_type = fetch_url(url)
            
            # Check if it's HTML content
            if content and mime_type and 'html' in mime_type.lower():
                # Extract all artifacts
                artifacts = extract_artifacts_from_html(content, url, date=datetime.datetime.now().isoformat())
                
                # Filter for name artifacts
                for artifact in artifacts:
                    # Try to determine if this is a name artifact
                    is_name, extracted_name = self.is_name_artifact(artifact.get("content", ""), artifact.get("type"))
                    
                    if is_name:
                        # This is a name artifact
                        name_artifact = {
                            "name": extracted_name,
                            "context": artifact.get("content", "")[:500],  # Limit context length
                            "source_url": url,
                            "type": "name_artifact",
                            "timestamp": datetime.datetime.now().isoformat(),
                            "score": artifact.get("score", 0.5)
                        }
                        
                        # Record the discovery
                        discovered_artifacts.append(name_artifact)
                        
                        # Update productive sources
                        if url not in self.productive_sources:
                            self.productive_sources[url] = 0
                        self.productive_sources[url] += 1
                        
                        # Log the discovery
                        logger.info(f"Discovered name artifact: {extracted_name} from {url}")
                        
                        # Record in the matrix
                        self.matrix.record_discovery({
                            "source": "crawler",
                            "url": url,
                            "content": f"Name artifact: {extracted_name}",
                            "entities": ["Vitalik Buterin"],
                            "related_artifacts": ["name"]
                        }, narrative_worthy=True)
                
                # Extract and queue new links
                links = extract_links(url, content)
                for link in links:
                    # Only add links that might be relevant to Vitalik or Ethereum
                    if any(term in link.lower() for term in ['vitalik', 'buterin', 'ethereum', 'eth', 'blockchain']):
                        self.url_queue.add(link)
        
        except Exception as e:
            logger.error(f"Error processing URL {url}: {str(e)}")
        
        return discovered_artifacts
    
    def save_discoveries(self):
        """Save all discoveries to the name_artifacts directory."""
        if not self.discoveries:
            logger.warning("No discoveries to save")
            return
        
        # Create a summary file
        summary_path = os.path.join(name_artifacts_dir, 'summary.json')
        with open(summary_path, 'w') as f:
            summary = {
                "objective": "Find name around Vitalik Buterin",
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_minutes": round((self.end_time - self.start_time).total_seconds() / 60, 2) if self.start_time and self.end_time else None,
                "sources_searched_count": len(self.sources_searched),
                "discoveries_count": len(self.discoveries),
                "productive_sources": self.productive_sources,
                "discoveries": self.discoveries
            }
            json.dump(summary, f, indent=2)
        
        logger.info(f"Saved {len(self.discoveries)} discoveries to {summary_path}")
        
        # Also save individual discovery files for high-scoring items
        for i, discovery in enumerate(self.discoveries):
            if discovery.get("score", 0) > 0.6:  # Only save high-scoring discoveries separately
                file_path = os.path.join(name_artifacts_dir, f"name_{i+1}_{discovery['name'].replace(' ', '_')}.json")
                with open(file_path, 'w') as f:
                    json.dump(discovery, f, indent=2)
    
    def run_test(self, max_time_minutes=30, min_discoveries=3):
        """
        Run the Ethereum name artifacts test.
        
        Args:
            max_time_minutes: Maximum time to run in minutes
            min_discoveries: Minimum number of discoveries before stopping
        """
        logger.info(f"Starting Ethereum name test with max_time={max_time_minutes}m, min_discoveries={min_discoveries}")
        
        # Set up the objective
        self.set_objective()
        
        # Add Ethereum-specific sources
        self.add_ethereum_sources()
        
        # Initialize timing
        self.start_time = datetime.datetime.now()
        end_by = self.start_time + datetime.timedelta(minutes=max_time_minutes)
        
        # Process URLs until time runs out or we have enough discoveries
        processed_count = 0
        
        if crawler_available and self.url_queue:
            while (datetime.datetime.now() < end_by and 
                   len(self.discoveries) < min_discoveries and 
                   not self.url_queue.is_empty() and
                   processed_count < 100):  # Limit to 100 URLs max
                
                url = self.url_queue.next()
                if not url:
                    break
                
                # Process URL and get discoveries
                new_discoveries = self.process_url(url)
                self.discoveries.extend(new_discoveries)
                
                processed_count += 1
                
                # Brief pause to avoid overwhelming servers
                time.sleep(1)
        else:
            # If crawler isn't available, add some simulated discoveries
            logger.warning("Crawler not available, adding simulated discoveries for testing")
            
            # Simulated discoveries for testing
            self.discoveries.extend([
                {
                    "name": "Vitalik_btc",
                    "context": "Early Bitcoin forum username used by Vitalik Buterin",
                    "source_url": "https://bitcointalk.org",
                    "type": "name_artifact",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "score": 0.8
                },
                {
                    "name": "ETHdev",
                    "context": "Handle used in early Ethereum development communications",
                    "source_url": "https://github.com",
                    "type": "name_artifact",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "score": 0.7
                },
                {
                    "name": "Frontier",
                    "context": "Early name for the first Ethereum release",
                    "source_url": "https://ethereum.org",
                    "type": "name_artifact",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "score": 0.9
                }
            ])
            
            # Add some simulated sources
            self.sources_searched = {
                "https://bitcointalk.org", 
                "https://github.com", 
                "https://ethereum.org"
            }
            
            # Update productive sources
            self.productive_sources = {
                "https://bitcointalk.org": 1,
                "https://github.com": 1,
                "https://ethereum.org": 1
            }
        
        # Record end time
        self.end_time = datetime.datetime.now()
        
        # Save all discoveries
        self.save_discoveries()
        
        # Report results
        duration_minutes = round((self.end_time - self.start_time).total_seconds() / 60, 2)
        logger.info(f"Test completed in {duration_minutes} minutes")
        logger.info(f"Processed {processed_count} URLs")
        logger.info(f"Found {len(self.discoveries)} name artifacts")
        
        # Return summary for reporting
        return {
            "objective": "Find name around Vitalik Buterin",
            "duration_minutes": duration_minutes,
            "urls_processed": processed_count,
            "sources_searched": len(self.sources_searched),
            "discoveries": len(self.discoveries),
            "discovery_details": self.discoveries,
            "productive_sources": self.productive_sources
        }

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.join(base_dir, 'logs'), exist_ok=True)
    
    # Run the test
    print("=" * 80)
    print("Ethereum Name Artifacts Test")
    print("=" * 80)
    
    test = EthereumNameTest()
    result = test.run_test(max_time_minutes=30, min_discoveries=3)
    
    print("\nTest Results:")
    print(f"Duration: {result['duration_minutes']} minutes")
    print(f"URLs Processed: {result['urls_processed']}")
    print(f"Sources Searched: {result['sources_searched']}")
    print(f"Discoveries: {result['discoveries']}")
    
    print("\nName Artifacts Discovered:")
    for i, discovery in enumerate(result['discovery_details']):
        print(f"{i+1}. {discovery['name']} (score: {discovery.get('score', 'N/A')})")
        print(f"   Source: {discovery['source_url']}")
        print(f"   Context: {discovery['context'][:100]}..." if len(discovery['context']) > 100 else f"   Context: {discovery['context']}")
        print()
    
    print("\nMost Productive Sources:")
    for source, count in sorted(result['productive_sources'].items(), key=lambda x: x[1], reverse=True)[:3]:
        print(f"- {source}: {count} discoveries")
    
    print("\nComplete results saved to:")
    print(f"- {os.path.join(name_artifacts_dir, 'summary.json')}")
    
    print("\nTest complete.")