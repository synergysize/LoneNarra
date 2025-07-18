#!/usr/bin/env python3
"""
Test script for the automatic discovery reporting functionality.
"""

import os
import sys
import time
from datetime import datetime

# Set up base directory
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Import the integrated controller
from integrated_main import IntegratedController

def main():
    """Run a test of the automatic discovery reporting."""
    print("=" * 80)
    print("Testing Automatic Discovery Reporting")
    print("=" * 80)
    
    # Initialize controller
    controller = IntegratedController()
    
    # Run with a specific objective
    objective = "Find name artifacts around Vitalik Buterin"
    
    print(f"Running research with objective: {objective}")
    print("This will generate an automatic discovery summary when complete.")
    print("The summary will be saved to the session_summaries directory and discovery_log.txt")
    
    # Run with a short time limit for testing
    results = controller.run_with_objective(objective, max_time_minutes=2)
    
    # Check if summary was generated
    if "summary" in results:
        print("\nSummary was successfully generated and saved.")
        
        # Check if files were created
        session_summaries_dir = os.path.join(base_dir, 'results', 'session_summaries')
        discovery_log_path = os.path.join(base_dir, 'results', 'discovery_log.txt')
        
        summary_files = os.listdir(session_summaries_dir) if os.path.exists(session_summaries_dir) else []
        has_log = os.path.exists(discovery_log_path)
        
        print(f"Session summary files: {len(summary_files)}")
        print(f"Discovery log exists: {has_log}")
    else:
        print("\nError: Summary was not generated.")
    
    print("\nTest complete.")

if __name__ == "__main__":
    main()