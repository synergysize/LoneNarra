#!/usr/bin/env python3
"""
Simple test script for the discovery summary generation.
"""

import os
import sys
from datetime import datetime
from collections import Counter

# Set up base directory
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Import the integrated controller
from integrated_main import IntegratedController

def main():
    """Test the discovery summary generation directly."""
    print("Testing Discovery Summary Generation")
    
    # Initialize controller
    controller = IntegratedController()
    
    # Set up a test objective
    objective = "Find name artifacts around Vitalik Buterin"
    
    # Create test results and stats
    results = {
        "objective": objective,
        "artifact_type": "name",
        "entity": "Vitalik Buterin",
        "urls_processed": 25,
        "artifacts_found": 10,
        "high_scoring_artifacts": 5
    }
    
    # Set up test stats
    controller.stats = {
        "objectives_processed": 1,
        "urls_processed": 25,
        "artifacts_found": 10,
        "high_scoring_artifacts": 5,
        "narrative_worthy_discoveries": 3,
        "start_time": datetime.now(),
        "end_time": datetime.now(),
        "elapsed_minutes": 2.5,
        "sources_accessed": Counter({
            "github.com": 12,
            "web.archive.org": 8,
            "ethresear.ch": 3,
            "bitcointalk.org": 2
        }),
        "wayback_snapshots_accessed": 8
    }
    
    # Generate summary
    summary = controller.generate_discovery_summary(objective, results)
    
    print("Summary generation completed.")
    print("Check the session_summaries directory and discovery_log.txt for results.")

if __name__ == "__main__":
    main()