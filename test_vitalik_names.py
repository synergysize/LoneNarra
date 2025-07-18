#!/usr/bin/env python3
"""
Specific test for extracting name artifacts around Vitalik Buterin.
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

# Import components
from crawler import Crawler
from enhancements.name_artifact_extractor import NameArtifactExtractor

def main():
    """Run a focused test on Vitalik name artifacts."""
    print("=" * 80)
    print("TESTING NAME ARTIFACTS EXTRACTION FOR VITALIK BUTERIN")
    print("=" * 80)
    
    # Create name artifact extractor
    name_extractor = NameArtifactExtractor(entity="Vitalik Buterin")
    
    # Initialize crawler
    crawler = Crawler()
    
    # Define specific URLs that are likely to contain name artifacts
    test_urls = [
        "https://github.com/vbuterin",
        "https://web.archive.org/web/20140101/https://vitalik.ca",
        "https://ethereum.org/en/history/",
        "https://en.wikipedia.org/wiki/Vitalik_Buterin"
    ]
    
    print(f"Testing {len(test_urls)} URLs:")
    for url in test_urls:
        print(f"- {url}")
    
    # Process each URL
    all_artifacts = []
    
    for url in test_urls:
        print(f"\n--- Processing {url} ---")
        
        try:
            # Fetch content
            html_content, _ = crawler.process_url(url, depth=0, extract_links_flag=False)
            
            if html_content:
                print(f"Fetched {len(html_content)} bytes of content")
                
                # Extract name artifacts
                artifacts = name_extractor.extract_from_html(html_content, url=url)
                
                print(f"Found {len(artifacts)} name artifacts")
                
                # Display artifacts
                for i, artifact in enumerate(artifacts):
                    print(f"  {i+1}. {artifact['name']} ({artifact['subtype']}, score: {artifact['score']})")
                    print(f"     Context: {artifact['context'][:100]}..." if len(artifact['context']) > 100 else f"     Context: {artifact['context']}")
                
                all_artifacts.extend(artifacts)
            else:
                print("Failed to fetch content")
        
        except Exception as e:
            print(f"Error processing URL: {e}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Processed {len(test_urls)} URLs")
    print(f"Found {len(all_artifacts)} total name artifacts")
    
    # List high-scoring artifacts
    high_scoring = [a for a in all_artifacts if a['score'] > 0.7]
    print(f"\nHigh-scoring artifacts ({len(high_scoring)}):")
    for i, artifact in enumerate(high_scoring):
        print(f"{i+1}. {artifact['name']} ({artifact['subtype']}, score: {artifact['score']})")
        print(f"   Source: {artifact['source_url']}")
    
    # Save results
    results_dir = os.path.join(base_dir, "results", "name_test")
    os.makedirs(results_dir, exist_ok=True)
    
    results_file = os.path.join(results_dir, f"vitalik_name_artifacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "urls_tested": test_urls,
            "total_artifacts": len(all_artifacts),
            "high_scoring_artifacts": len(high_scoring),
            "artifacts": all_artifacts
        }, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    print("\nTest complete.")

if __name__ == "__main__":
    main()