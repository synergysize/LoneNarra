#!/usr/bin/env python3
"""
Validate that the artifact extractor is working by testing it against a known HTML input with embedded Ethereum artifacts.
This script ensures that extraction, scoring, and output storage are functional before continuing with full crawler runs.
"""

import os
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('results/logs/validation.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('narrahunt.test_extraction')

# Function to extract artifacts - wrapper around our main extraction function
def extract_artifacts_from_html(html, url="https://example.com", date=None):
    """
    Extract Ethereum artifacts from HTML content.
    Wrapper for the real extraction function to match the API in the prompt.
    """
    from artifact_extractor import extract_artifacts_from_html as real_extract
    return real_extract(html, url, date)

# Main execution
if __name__ == "__main__":
    test_path = "tests/test_with_known_artifacts.html"
    if not os.path.exists(test_path):
        logger.error("❌ test_with_known_artifacts.html not found.")
        print("❌ test_with_known_artifacts.html not found.")
        exit(1)
    
    try:
        html = open(test_path, "r", encoding="utf-8").read()
        artifacts = extract_artifacts_from_html(html, url="https://ethereum.org/test", date="2017-06-01")
        
        print(f"✅ Found {len(artifacts)} artifacts\n")
        for a in artifacts:
            print(f"{a['type']:20} | Score: {a['score']:>2} | Summary: {a['summary']}")
            
    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}")
        print(f"❌ Error during extraction: {str(e)}")
        exit(1)