#!/usr/bin/env python3
"""
Test script for the Narrative Discovery Matrix System
"""

import os
import time
from narrative_matrix import NarrativeMatrix
from objectives_manager import ObjectivesManager

def main():
    """Test the Narrative Discovery Matrix system."""
    print("Testing Narrative Discovery Matrix System")
    print("========================================")
    
    # Make sure logs directory exists
    os.makedirs(os.path.join(os.path.dirname(__file__), 'logs'), exist_ok=True)
    
    # Test the Narrative Matrix
    print("\n1. Testing Narrative Matrix...")
    matrix = NarrativeMatrix()
    objective = matrix.generate_objective()
    print(f"Generated objective: {objective}")
    
    # Simulate a discovery
    print("\n2. Recording a test discovery...")
    matrix.record_discovery({
        "source": "test_script",
        "content": "Found GitHub repository with personal information",
        "entities": ["John Doe", "CryptoProject X"],
        "related_artifacts": ["repository", "social_media"],
        "timestamp": "2023-07-12T10:00:00"
    }, narrative_worthy=True)
    print("Discovery recorded successfully")
    
    # Generate follow-up objectives
    print("\n3. Generating follow-up objectives...")
    followups = matrix.generate_followup_objectives()
    for i, followup in enumerate(followups):
        print(f"   {i+1}. {followup}")
    
    # Test Objectives Manager
    print("\n4. Testing Objectives Manager...")
    manager = ObjectivesManager()
    print(f"Crawler available: {manager.crawler_available}")
    print(f"LLM integration available: {manager.llm_available}")
    
    # Load current objective
    current = manager.load_current_objective()
    print(f"Current objective: {current}")
    
    # Mark the objective as complete and move to next
    print("\n5. Testing objective completion and rotation...")
    next_objective = manager.move_to_next_objective()
    print(f"Next objective: {next_objective}")
    
    print("\n6. Testing autonomous cycle (limited to 1 cycle)...")
    manager.run_autonomous_cycle(max_cycles=1, cycle_delay=5)
    
    print("\nTest completed. The Narrative Discovery Matrix system is ready for use.")
    print("Check the results/narratives/ directory for narrative-worthy findings.")

if __name__ == "__main__":
    main()