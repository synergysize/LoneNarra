#!/usr/bin/env python3
"""
Test script to verify the system fixes with API integration.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Set up base directory
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Configure logging to see detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logging.getLogger('artifact_extractor').setLevel(logging.DEBUG)
logging.getLogger('crawler').setLevel(logging.DEBUG)
logging.getLogger('llm_integration').setLevel(logging.DEBUG)

# Import components
from narrative_matrix import NarrativeMatrix
from objectives_manager import ObjectivesManager
from crawler import Crawler
from llm_integration import LLMIntegration
from llm_research_strategy import LLMResearchStrategy

def test_llm_integration():
    """Test the LLM integration."""
    print("\n=== Testing LLM Integration ===")
    
    try:
        llm = LLMIntegration(use_claude=True)
        
        # Test with a simple query
        test_text = "Vitalik Buterin is the creator of Ethereum, a blockchain platform for decentralized applications."
        
        print("Analyzing text with Claude...")
        result = llm.analyze(test_text)
        
        print("Analysis result:")
        print(json.dumps(result, indent=2))
        
        if "entities" in result and "sentiment" in result:
            print("✅ LLM Integration is working!")
            return True
        else:
            print("❌ LLM Integration returned incomplete results")
            return False
    except Exception as e:
        print(f"❌ LLM Integration test failed: {e}")
        return False

def test_crawler():
    """Test the crawler module."""
    print("\n=== Testing Crawler Module ===")
    
    try:
        crawler = Crawler()
        
        # Test with a known URL
        test_urls = ["https://ethereum.org/en/"]
        
        print(f"Adding URLs: {test_urls}")
        crawler.add_urls(test_urls)
        
        print("Processing a single URL...")
        html_content, artifacts = crawler.process_url(test_urls[0], depth=0, extract_links_flag=False)
        
        if html_content:
            print(f"✅ Successfully fetched content ({len(html_content)} bytes)")
            
            if artifacts:
                print(f"✅ Found {len(artifacts)} artifacts")
                for i, artifact in enumerate(artifacts[:3]):  # Show first 3
                    print(f"  - Artifact {i+1}: {artifact.get('type')}, Score: {artifact.get('score')}")
            else:
                print("ℹ️ No artifacts found in this page")
            
            return True
        else:
            print("❌ Failed to fetch content")
            return False
    except Exception as e:
        print(f"❌ Crawler test failed: {e}")
        return False

def test_matrix_with_real_entities():
    """Test the narrative matrix with real entities."""
    print("\n=== Testing Narrative Matrix ===")
    
    try:
        matrix = NarrativeMatrix()
        
        print("Matrix configuration:")
        print(f"- Artifact types: {len(matrix.config['artifact_types'])}")
        print(f"- Target entities: {len(matrix.config['target_entities'])}")
        print(f"- Specific targets: {len(matrix.config['specific_targets'])}")
        
        # Check if real entities exist
        real_entities = ["Vitalik Buterin", "Matt Furie", "Gavin Wood", "Ethereum Foundation"]
        missing_entities = [entity for entity in real_entities if entity not in matrix.config["specific_targets"]]
        
        if missing_entities:
            print(f"❌ Missing entities: {missing_entities}")
            return False
        
        # Generate some objectives
        print("Generating sample objectives:")
        for _ in range(3):
            objective = matrix.generate_objective()
            print(f"- {objective}")
        
        return True
    except Exception as e:
        print(f"❌ Matrix test failed: {e}")
        return False

def test_llm_research_strategy():
    """Test the LLM research strategy generator."""
    print("\n=== Testing LLM Research Strategy ===")
    
    try:
        strategy_generator = LLMResearchStrategy()
        
        objective = "Find name artifacts around Vitalik Buterin"
        entity = "Vitalik Buterin"
        
        print(f"Generating research strategy for: {objective}")
        strategy = strategy_generator.generate_research_strategy(objective, entity)
        
        if "crawlable_urls" in strategy and strategy["crawlable_urls"]:
            print(f"✅ Generated {len(strategy['crawlable_urls'])} crawlable URLs")
            print("Sample URLs:")
            for url in strategy["crawlable_urls"][:3]:
                print(f"- {url}")
            return True
        else:
            print("❌ Failed to generate crawlable URLs")
            return False
    except Exception as e:
        print(f"❌ LLM research strategy test failed: {e}")
        return False

def test_full_objective():
    """Test a full objective execution."""
    print("\n=== Testing Full Objective Execution ===")
    
    try:
        matrix = NarrativeMatrix()
        crawler = Crawler()
        
        # Set specific objective
        objective = "Find name artifacts around Vitalik Buterin"
        print(f"Setting objective: {objective}")
        
        # Get artifact type and entity
        words = objective.split()
        artifact_type = None
        entity = None
        
        for i, word in enumerate(words):
            if word.lower() in ["find", "discover"] and i+1 < len(words):
                artifact_type = words[i+1]
            if word.lower() in ["around", "related", "associated", "connected"] and i+1 < len(words):
                entity = " ".join(words[i+1:])
                entity = entity.rstrip(".,:;")
        
        print(f"Parsed objective - Artifact type: {artifact_type}, Entity: {entity}")
        
        # Generate URLs from research strategy
        strategy_generator = LLMResearchStrategy()
        strategy = strategy_generator.generate_research_strategy(objective, entity)
        
        # Limit to 5 URLs for testing
        test_urls = strategy["crawlable_urls"][:5]
        print(f"Testing with {len(test_urls)} URLs:")
        for url in test_urls:
            print(f"- {url}")
        
        # Add URLs to crawler
        crawler.add_urls(test_urls)
        
        # Process URLs
        all_artifacts = []
        total_html_bytes = 0
        
        for url in test_urls:
            html_content, artifacts = crawler.process_url(url, depth=0, extract_links_flag=False)
            
            if html_content:
                total_html_bytes += len(html_content)
                all_artifacts.extend(artifacts)
                
                print(f"Processed {url}: {len(html_content)} bytes, {len(artifacts)} artifacts")
            else:
                print(f"Failed to process {url}")
        
        print(f"\nProcessed {len(test_urls)} URLs")
        print(f"Total HTML content: {total_html_bytes} bytes")
        print(f"Total artifacts found: {len(all_artifacts)}")
        
        if all_artifacts:
            print("\nSample artifacts:")
            for i, artifact in enumerate(all_artifacts[:3]):
                print(f"- Artifact {i+1}: {artifact.get('type')}, Score: {artifact.get('score')}")
                print(f"  Summary: {artifact.get('summary', '')}")
            return True
        elif total_html_bytes > 0:
            print("\n⚠️ HTML content was fetched but no artifacts were found")
            print("This might be due to content not matching extraction patterns")
            return False
        else:
            print("\n❌ No content could be fetched from URLs")
            return False
    except Exception as e:
        print(f"❌ Full objective test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 80)
    print("SYSTEM FIXES VERIFICATION")
    print("=" * 80)
    
    results = {
        "llm_integration": test_llm_integration(),
        "crawler": test_crawler(),
        "matrix": test_matrix_with_real_entities(),
        "research_strategy": test_llm_research_strategy(),
        "full_objective": test_full_objective()
    }
    
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! The system is working correctly.")
    else:
        print("\n⚠️ Some tests failed. See above for details.")

if __name__ == "__main__":
    main()