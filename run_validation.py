#!/usr/bin/env python3
"""
Validation script for the artifact extractor.
Tests the extractor against a file with known artifacts.
"""

import os
import sys
import logging
from datetime import datetime

from artifact_extractor import extract_artifacts_from_html

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('results/logs/validation.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('narrahunt.validation')

def main():
    """Run validation on test HTML file with known artifacts."""
    test_path = "tests/test_with_known_artifacts.html"
    if not os.path.exists(test_path):
        logger.error("❌ test_with_known_artifacts.html not found.")
        print("❌ test_with_known_artifacts.html not found.")
        return 1
    
    logger.info(f"Loading test file: {test_path}")
    
    try:
        with open(test_path, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        logger.error(f"Error reading test file: {str(e)}")
        print(f"❌ Error reading test file: {str(e)}")
        return 1
    
    logger.info("Extracting artifacts from test HTML")
    
    # Extract artifacts
    artifacts = extract_artifacts_from_html(
        html, 
        url="https://ethereum.org/test", 
        date="2017-06-01"
    )
    
    # Log results
    logger.info(f"Found {len(artifacts)} artifacts")
    
    # Group by type
    artifact_types = {}
    for artifact in artifacts:
        artifact_type = artifact['type']
        if artifact_type not in artifact_types:
            artifact_types[artifact_type] = []
        artifact_types[artifact_type].append(artifact)
    
    # Print summary
    print(f"✅ Found {len(artifacts)} artifacts\n")
    for artifact_type, type_artifacts in artifact_types.items():
        print(f"- {artifact_type}: {len(type_artifacts)} found")
    
    print("\nDetailed artifacts:")
    for a in artifacts:
        print(f"{a['type']:20} | Score: {a['score']:>2} | Summary: {a['summary']}")
    
    # Check if any high-scoring artifacts were found
    high_scoring = [a for a in artifacts if a['score'] > 0]
    logger.info(f"Found {len(high_scoring)} high-scoring artifacts")
    
    if len(high_scoring) > 0:
        print(f"\nHigh-scoring artifacts: {len(high_scoring)}")
        print("Check results/found.txt for details")
    else:
        print("\nNo high-scoring artifacts found.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())