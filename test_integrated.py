#!/usr/bin/env python3
"""
Test script for the integrated Narrative Discovery Matrix with real crawling.
This script performs a limited test with a small number of URLs to demonstrate the functionality.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Set up base directory
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_integrated')

# Import components
from narrative_matrix import NarrativeMatrix
from objectives_manager import ObjectivesManager
from llm_research_strategy import LLMResearchStrategy
from wayback_integration import WaybackMachine
from enhanced_artifact_detector import EnhancedArtifactDetector

# Import specific crawler components
try:
    from fetch import fetch_page
    from url_queue import URLQueue
    from crawl import extract_links
    crawler_components_available = True
except ImportError:
    crawler_components_available = False
    logger.warning("Crawler components not available")

def simulate_research(objective, entity=None, max_urls=3):
    """
    Simulate research using the integrated system.
    """
    print(f"Simulating research for: {objective}")
    
    # Initialize components
    matrix = NarrativeMatrix()
    llm_strategy = LLMResearchStrategy()
    detector = EnhancedArtifactDetector()
    
    # Set the objective in the matrix
    if entity:
        # Ensure entity is in the matrix
        if entity not in matrix.config["specific_targets"]:
            matrix.add_entity(entity, "specific")
    
    # Parse objective to get artifact type
    artifact_type = None
    for potential_type in ["name", "wallet", "code", "personal", "legal", "academic", "hidden", "institutional"]:
        if potential_type in objective.lower():
            artifact_type = potential_type
            break
    
    # Set up the objective in the matrix
    matrix.current_objective = {
        "text": objective,
        "artifact_type": artifact_type,
        "entity": entity,
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "discoveries": []
    }
    
    # Get research strategy from LLM
    strategy = llm_strategy.generate_research_strategy(objective, entity)
    
    # Display the research strategy
    print("\nResearch Strategy:")
    print(f"Found {len(strategy['crawlable_urls'])} URLs to crawl")
    print("\nSample URLs:")
    for url in strategy['crawlable_urls'][:5]:
        print(f"- {url}")
    
    # Simulate crawling a few URLs if crawler components are available
    if crawler_components_available:
        print("\nAttempting to crawl URLs...")
        
        artifacts_found = []
        
        # Use only the first few URLs for testing
        test_urls = strategy['crawlable_urls'][:max_urls]
        
        for url in test_urls:
            try:
                print(f"Fetching: {url}")
                html_content, fetch_info = fetch_page(url)
                
                # Extract artifacts
                artifacts = detector.extract_artifacts(
                    html_content,
                    url=url,
                    date=fetch_info.get("date", datetime.now().isoformat()),
                    objective=objective,
                    entity=entity
                )
                
                if artifacts:
                    print(f"Found {len(artifacts)} artifacts on {url}")
                    artifacts_found.extend(artifacts)
                    
                    # Record high-scoring artifacts in the matrix
                    for artifact in artifacts:
                        if artifact.get("score", 0) > 0.7:
                            discovery = {
                                "source": "crawler",
                                "url": url,
                                "content": artifact.get("summary", ""),
                                "entities": [entity] if entity else [],
                                "related_artifacts": [artifact_type] if artifact_type else [],
                                "details": artifact
                            }
                            
                            matrix.record_discovery(discovery, narrative_worthy=(artifact.get("score", 0) > 0.8))
            except Exception as e:
                print(f"Error processing {url}: {e}")
        
        # Display found artifacts
        print(f"\nFound {len(artifacts_found)} total artifacts")
        
        for i, artifact in enumerate(artifacts_found):
            print(f"\nArtifact {i+1}:")
            print(f"Type: {artifact.get('type')}")
            print(f"Score: {artifact.get('score')}")
            print(f"Summary: {artifact.get('summary')}")
    else:
        print("\nCrawler components not available. Using simulated discoveries.")
        
        # Simulate some discoveries
        simulated_discoveries = [
            {
                "source": "simulated",
                "url": "https://vitalik.ca/general/2017/09/14/prehistory.html",
                "content": "Name artifact: vitalik_btc (username)",
                "entities": [entity] if entity else [],
                "related_artifacts": [artifact_type] if artifact_type else [],
                "details": {
                    "type": "name",
                    "subtype": "username",
                    "content": "Early Bitcoin forum username used by Vitalik Buterin",
                    "summary": "Name artifact: vitalik_btc (username)",
                    "score": 0.9
                }
            },
            {
                "source": "simulated",
                "url": "https://web.archive.org/web/20140101/vitalik.ca",
                "content": "Name artifact: Frontier (project_name)",
                "entities": [entity] if entity else [],
                "related_artifacts": [artifact_type] if artifact_type else [],
                "details": {
                    "type": "name",
                    "subtype": "project_name",
                    "content": "Early name for the first Ethereum release",
                    "summary": "Name artifact: Frontier (project_name)",
                    "score": 0.95
                }
            },
            {
                "source": "simulated",
                "url": "https://github.com/vbuterin/pybitcointools",
                "content": "Name artifact: pybitcointools (project_name)",
                "entities": [entity] if entity else [],
                "related_artifacts": [artifact_type] if artifact_type else [],
                "details": {
                    "type": "name",
                    "subtype": "project_name",
                    "content": "Early Bitcoin-related Python library created by Vitalik",
                    "summary": "Name artifact: pybitcointools (project_name)",
                    "score": 0.85
                }
            }
        ]
        
        # Record simulated discoveries in the matrix
        for discovery in simulated_discoveries:
            matrix.record_discovery(discovery, narrative_worthy=True)
            
        # Display simulated discoveries
        print("\nSimulated Discoveries:")
        for i, discovery in enumerate(simulated_discoveries):
            print(f"\nDiscovery {i+1}:")
            print(f"Source: {discovery.get('source')}")
            print(f"URL: {discovery.get('url')}")
            print(f"Content: {discovery.get('content')}")
            print(f"Score: {discovery.get('details', {}).get('score')}")
    
    # Mark the objective as complete
    matrix.mark_objective_complete("completed")
    
    # Check narratives directory
    narratives_dir = os.path.join(base_dir, 'results', 'narratives')
    if os.path.exists(narratives_dir):
        narrative_files = [f for f in os.listdir(narratives_dir) if f.endswith('.json')]
        
        if narrative_files:
            print("\nNarrative-worthy discoveries saved to:")
            for file in sorted(narrative_files)[-5:]:  # Show last 5 files
                print(f"- {os.path.join('results', 'narratives', file)}")
    
    print("\nSimulation complete.")

if __name__ == "__main__":
    print("=" * 80)
    print("Testing Integrated Narrative Discovery Matrix")
    print("=" * 80)
    
    # Test with a specific objective
    objective = "Find name artifacts around Vitalik Buterin"
    entity = "Vitalik Buterin"
    
    simulate_research(objective, entity, max_urls=3)