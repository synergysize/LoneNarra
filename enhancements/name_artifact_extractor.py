#!/usr/bin/env python3
"""
Enhanced Name Artifact Extractor for the Narrative Discovery Matrix.

This module extends the standard artifact extraction with specialized
capabilities for detecting and analyzing name artifacts - usernames,
project names, aliases, and other naming patterns particularly relevant
for cryptocurrency figures and projects.
"""

import re
import os
import json
import logging
from datetime import datetime
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('name_artifact_extractor')

class NameArtifactExtractor:
    """
    Specialized extractor for name-related artifacts.
    """
    
    def __init__(self, entity=None):
        """
        Initialize the name artifact extractor.
        
        Args:
            entity: Optional target entity to focus extraction on
        """
        self.entity = entity
        self.name_patterns = {
            'username': [
                r'username[:\s]+([A-Za-z0-9_-]{3,30})',
                r'user[\s-]name[:\s]+([A-Za-z0-9_-]{3,30})',
                r'handle[:\s]+([A-Za-z0-9_-]{3,30})',
                r'account[\s-]name[:\s]+([A-Za-z0-9_-]{3,30})',
                r'@([A-Za-z0-9_]{3,30})',
                r'known as ([A-Za-z0-9_-]{3,30}) on',
                r'([A-Za-z0-9_-]{3,30}) on (?:twitter|github|reddit)'
            ],
            'project_name': [
                r'project[\s-]name[:\s]+([A-Za-z0-9_-]{3,30})',
                r'called[\s:]+(the\s)?([A-Za-z0-9_\s-]{3,30}) project',
                r'developed[\s:]+(the\s)?([A-Za-z0-9_\s-]{3,30})',
                r'created[\s:]+(the\s)?([A-Za-z0-9_\s-]{3,30})',
                r'founded[\s:]+(the\s)?([A-Za-z0-9_\s-]{3,30})',
                r'launched[\s:]+(the\s)?([A-Za-z0-9_\s-]{3,30})',
                r'(the\s)?([A-Za-z0-9_\s-]{3,30}) blockchain',
                r'(the\s)?([A-Za-z0-9_\s-]{3,30}) protocol',
                r'(the\s)?([A-Za-z0-9_\s-]{3,30}) platform',
                r'(the\s)?([A-Za-z0-9_\s-]{3,30}) network'
            ],
            'pseudonym': [
                r'pseudonym[:\s]+([A-Za-z0-9_-]{3,30})',
                r'alias[:\s]+([A-Za-z0-9_-]{3,30})',
                r'pen[\s-]name[:\s]+([A-Za-z0-9_-]{3,30})',
                r'nickname[:\s]+([A-Za-z0-9_-]{3,30})',
                r'known as ([A-Za-z0-9_-]{3,30})',
                r'goes by ([A-Za-z0-9_-]{3,30})',
                r'([A-Za-z0-9_-]{3,30}) \((?:a.k.a.|aka|alias)\)'
            ],
            'terminology': [
                r'coined (?:the )?term[:\s]+["\']([A-Za-z0-9_\s-]{3,30})["\']',
                r'called it[:\s]+["\']([A-Za-z0-9_\s-]{3,30})["\']',
                r'term[:\s]+["\']([A-Za-z0-9_\s-]{3,30})["\']',
                r'concept of ["\']([A-Za-z0-9_\s-]{3,30})["\']'
            ],
            'company_name': [
                r'company[:\s]+([A-Za-z0-9_\s-]{3,30})',
                r'startup[:\s]+([A-Za-z0-9_\s-]{3,30})',
                r'founded[\s:]+(the\s)?([A-Za-z0-9_\s-]{3,30})',
                r'(the\s)?([A-Za-z0-9_\s-]{3,30}) foundation',
                r'(the\s)?([A-Za-z0-9_\s-]{3,30}) lab',
                r'(the\s)?([A-Za-z0-9_\s-]{3,30}) inc',
                r'(the\s)?([A-Za-z0-9_\s-]{3,30}) llc'
            ]
        }
        
        # Name filtering - terms that are too generic to be useful
        self.filter_terms = [
            'project', 'website', 'platform', 'system', 'network', 'concept',
            'username', 'nickname', 'handle', 'alias', 'term', 'idea',
            'profile', 'account', 'user', 'protocol', 'blockchain', 'foundation',
            'the', 'and', 'or', 'but', 'however', 'therefore', 'because',
            'company', 'startup', 'organization', 'group', 'team', 'community'
        ]
        
        # Specialized context words that increase the relevance score
        self.context_relevance = {
            'cryptocurrency': 0.2,
            'blockchain': 0.2,
            'ethereum': 0.3,
            'bitcoin': 0.2,
            'crypto': 0.2,
            'token': 0.1,
            'wallet': 0.1,
            'smart contract': 0.2,
            'dapp': 0.2,
            'decentralized': 0.1,
            'web3': 0.1,
            'consensus': 0.1,
            'mining': 0.1,
            'staking': 0.1,
            'node': 0.1,
            'testnet': 0.2,
            'mainnet': 0.2,
            'fork': 0.1,
            'whitepaper': 0.2
        }
    
    def extract_from_text(self, text, url=None, date=None):
        """
        Extract name artifacts from text.
        
        Args:
            text: Text to extract from
            url: Source URL for context
            date: Date of the content for relevance scoring
            
        Returns:
            List of name artifact dictionaries
        """
        artifacts = []
        
        # Skip if no text
        if not text or len(text) < 20:
            return artifacts
        
        # Search for entity-specific context if entity is specified
        entity_context = False
        if self.entity:
            entity_pattern = re.compile(re.escape(self.entity), re.IGNORECASE)
            entity_context = bool(entity_pattern.search(text))
        
        # Extract name artifacts by type
        for name_type, patterns in self.name_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Get the name, handling patterns with multiple groups
                    if len(match.groups()) > 1 and match.group(2):
                        name = match.group(2).strip()
                    else:
                        name = match.group(1).strip()
                    
                    # Skip filtered terms
                    if name.lower() in self.filter_terms:
                        continue
                    
                    # Skip if too short
                    if len(name) < 3:
                        continue
                    
                    # Calculate base score
                    score = 0.5
                    
                    # Adjust score based on name type
                    if name_type == 'project_name':
                        score += 0.1
                    elif name_type == 'username':
                        score += 0.05
                    elif name_type == 'terminology':
                        score += 0.2  # Terminology is particularly valuable
                    
                    # Adjust score if this is in context of the target entity
                    if entity_context:
                        score += 0.2
                    
                    # Check for specialized context terms
                    context_window = text[max(0, match.start() - 100):min(len(text), match.end() + 100)]
                    for term, bonus in self.context_relevance.items():
                        if re.search(r'\b' + re.escape(term) + r'\b', context_window, re.IGNORECASE):
                            score += bonus
                    
                    # Cap score at 1.0
                    score = min(1.0, score)
                    
                    # Create artifact
                    artifact = {
                        'type': 'name_artifact',
                        'subtype': name_type,
                        'name': name,
                        'context': context_window,
                        'source_url': url,
                        'timestamp': datetime.now().isoformat(),
                        'score': round(score, 2)
                    }
                    
                    # Add to artifacts list, avoiding duplicates
                    if not any(a['name'].lower() == name.lower() for a in artifacts):
                        artifacts.append(artifact)
        
        return artifacts
    
    def extract_from_html(self, html_content, url=None, date=None):
        """
        Extract name artifacts from HTML content.
        
        Args:
            html_content: HTML content to parse
            url: Source URL for context
            date: Date of the content for relevance scoring
            
        Returns:
            List of name artifact dictionaries
        """
        artifacts = []
        
        # Parse HTML
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract from page title
            title = soup.title.string if soup.title else ""
            if title:
                artifacts.extend(self.extract_from_text(title, url, date))
            
            # Extract from main content
            content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div'])
            for tag in content_tags:
                text = tag.get_text()
                artifacts.extend(self.extract_from_text(text, url, date))
            
            # Extract from meta tags
            meta_tags = soup.find_all('meta', attrs={'name': ['description', 'keywords', 'author']})
            for tag in meta_tags:
                if 'content' in tag.attrs:
                    artifacts.extend(self.extract_from_text(tag['content'], url, date))
            
            # Extract from structured data
            script_tags = soup.find_all('script', type='application/ld+json')
            for tag in script_tags:
                try:
                    json_data = json.loads(tag.string)
                    if isinstance(json_data, dict):
                        # Extract from JSON fields
                        for key, value in json_data.items():
                            if isinstance(value, str):
                                artifacts.extend(self.extract_from_text(value, url, date))
                except:
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing HTML: {str(e)}")
        
        return artifacts
    
    def save_artifacts(self, artifacts, output_dir):
        """
        Save artifacts to files.
        
        Args:
            artifacts: List of artifact dictionaries
            output_dir: Directory to save to
        """
        if not artifacts:
            return
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save artifacts
        for i, artifact in enumerate(artifacts):
            # Create a clean filename from the name
            clean_name = re.sub(r'[^\w\-]', '_', artifact['name'])
            filename = f"name_{i+1}_{clean_name}.json"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(artifact, f, indent=2)
        
        # Create a summary file
        summary_path = os.path.join(output_dir, 'summary.json')
        with open(summary_path, 'w') as f:
            summary = {
                "entity": self.entity,
                "timestamp": datetime.now().isoformat(),
                "artifacts_count": len(artifacts),
                "artifacts": artifacts
            }
            json.dump(summary, f, indent=2)

# Example usage
if __name__ == "__main__":
    # Sample text with name artifacts
    sample_text = """
    Vitalik Buterin (username: vitalik_btc on the Bitcoin forum) is the creator of Ethereum.
    Before creating Ethereum, he worked on a project called "Colored Coins" and contributed to Bitcoin Magazine.
    His early pseudonym was "Bitcoinmeister" in some communities.
    The Ethereum project was initially called "Frontier" during its first release phase.
    He founded the Ethereum Foundation to support development of the blockchain.
    Vitalik coined the term "smart contract" to describe the programmable features of Ethereum.
    His GitHub handle is "vbuterin" where he commits code for various projects.
    """
    
    extractor = NameArtifactExtractor(entity="Vitalik Buterin")
    artifacts = extractor.extract_from_text(sample_text, url="https://example.com")
    
    print(f"Found {len(artifacts)} name artifacts:")
    for artifact in artifacts:
        print(f"- {artifact['name']} ({artifact['subtype']}, score: {artifact['score']})")
    
    # Create a test output directory
    output_dir = "test_output"
    extractor.save_artifacts(artifacts, output_dir)
    print(f"Saved artifacts to {output_dir}")