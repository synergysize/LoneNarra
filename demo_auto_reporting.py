#!/usr/bin/env python3
"""
Demo script for the automatic discovery reporting functionality.
This simulates a full research cycle and generates a discovery summary.
"""

import os
import sys
import json
import time
from datetime import datetime
from collections import Counter

# Set up base directory
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Import components
from narrative_matrix import NarrativeMatrix
from integrated_main import IntegratedController

def create_sample_narrative(entity, name, score, subtype, source):
    """Create a sample narrative discovery for testing."""
    timestamp = datetime.now().isoformat()
    narrative_file = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{subtype}.json"
    narrative_path = os.path.join(base_dir, 'results', 'narratives', narrative_file)
    
    narrative = {
        "objective": f"Find {subtype} artifacts around {entity}",
        "artifact_type": subtype,
        "entity": entity,
        "discovery": {
            "source": "demo",
            "url": f"https://{source}",
            "content": f"{subtype.title()} artifact: {name} ({subtype})",
            "entities": [entity],
            "related_artifacts": [subtype],
            "details": {
                "type": subtype,
                "subtype": subtype,
                "name": name,
                "content": f"This is a sample {subtype} artifact for {entity}",
                "summary": f"{subtype.title()} artifact: {name}",
                "score": score,
                "url": f"https://{source}",
                "date": timestamp
            },
            "timestamp": timestamp
        },
        "timestamp": timestamp
    }
    
    with open(narrative_path, 'w') as f:
        json.dump(narrative, f, indent=2)
    
    return narrative_path

def main():
    """Run a demonstration of the automatic discovery reporting."""
    print("=" * 80)
    print("Demo: Automatic Discovery Reporting")
    print("=" * 80)
    
    # Initialize controller and matrix
    controller = IntegratedController()
    matrix = NarrativeMatrix()
    
    # Set up a test objective
    objective = "Find name artifacts around Vitalik Buterin"
    entity = "Vitalik Buterin"
    
    print(f"Setting objective: {objective}")
    
    # Create test discoveries
    print("\nCreating sample narrative-worthy discoveries...")
    discoveries = [
        ("vitalik_btc", 0.95, "username", "bitcointalk.org"),
        ("pybitcointools", 0.9, "project_name", "github.com"),
        ("Frontier", 0.93, "project_name", "ethereum.org"),
        ("Colored Coins", 0.89, "project_name", "vitalik.ca"),
        ("Ethereum Whitepaper", 0.92, "document_name", "web.archive.org")
    ]
    
    narrative_files = []
    for name, score, subtype, source in discoveries:
        file_path = create_sample_narrative(entity, name, score, subtype, source)
        narrative_files.append(file_path)
        print(f"  Created: {os.path.basename(file_path)}")
        time.sleep(0.1)  # Small delay to ensure different timestamps
    
    # Set up test results and stats
    results = {
        "objective": objective,
        "artifact_type": "name",
        "entity": "Vitalik Buterin",
        "urls_processed": 47,
        "artifacts_found": 12,
        "high_scoring_artifacts": 8
    }
    
    # Set up test stats to simulate a real research cycle
    controller.stats = {
        "objectives_processed": 1,
        "urls_processed": 47,
        "artifacts_found": 12,
        "high_scoring_artifacts": 8,
        "narrative_worthy_discoveries": len(discoveries),
        "start_time": datetime.now(),
        "end_time": datetime.now(),
        "elapsed_minutes": 15.7,
        "sources_accessed": Counter({
            "github.com": 18,
            "web.archive.org": 12,
            "bitcointalk.org": 7,
            "vitalik.ca": 5,
            "ethereum.org": 3,
            "ethresear.ch": 2
        }),
        "wayback_snapshots_accessed": 12
    }
    
    # Generate next objectives
    related_objectives = [
        "Find wallet artifacts around Vitalik Buterin",
        "Find code artifacts around Ethereum Foundation",
        "Find name artifacts around Gavin Wood"
    ]
    
    # Add related objectives to the queue
    for obj in related_objectives:
        matrix.add_entity(obj.split("around ")[-1].strip(), "specific")
    
    print("\nGenerating automatic discovery summary...")
    print("(This will be saved to results/session_summaries/ and results/discovery_log.txt)")
    
    # Add a short delay for dramatic effect
    time.sleep(2)
    
    # Generate and display summary
    summary = controller.generate_discovery_summary(objective, results)
    
    print("\nSummary generation complete.")
    print(f"Summary saved to session_summaries/{datetime.now().strftime('%Y-%m-%d-%H-%M')}.txt")
    print("Discovery log updated.")
    
    print("\nDemo complete.")

if __name__ == "__main__":
    main()