#!/usr/bin/env python3
"""
Artifact extraction module for Narrahunt Phase 2.

This module extracts Ethereum-related artifacts from HTML content,
scores them based on various factors, and provides safe outputs.
"""

import re
import os
import json
import hashlib
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Base directory
base_dir = '/home/computeruse/.anthropic/narrahunt_phase2'

# Ensure output directories exist
os.makedirs(f'{base_dir}/results/artifacts', exist_ok=True)
os.makedirs(f'{base_dir}/results/logs', exist_ok=True)

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{base_dir}/results/logs/validation.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('narrahunt.artifact_extractor')

# Whitelist of trusted domains
TRUSTED_DOMAINS = [
    'ethereum.org',
    'ethereum.foundation',
    'eips.ethereum.org',
    'blog.ethereum.org',
    'vitalik.ca'
]

# Community domains (lower score)
COMMUNITY_DOMAINS = [
    'medium.com',
    'hackernoon.com',
    'reddit.com',
    'github.com',
    'steemit.com',
    'mirror.xyz'
]

# Warning phrases that reduce artifact score
WARNING_PHRASES = [
    'do not use in production',
    'example only',
    'not for production',
    'test key',
    'sample key',
    'dummy key',
    'do not use',
    'for testing'
]

# BIP39 word list (abbreviated for testing)
BIP39_WORDS = {
    'abandon', 'ability', 'able', 'about', 'above', 'absent', 'absorb', 'abstract', 
    'absurd', 'abuse', 'access', 'accident', 'account', 'accuse', 'achieve', 'acid', 
    'acoustic', 'acquire', 'across', 'act', 'action', 'actor', 'actress', 'actual', 
    'adapt', 'add', 'addict', 'address', 'adjust', 'admit', 'adult', 'advance', 
    'advice', 'aerobic', 'affair', 'afford', 'afraid', 'again', 'age', 'agent', 
    'agree', 'ahead', 'aim', 'air', 'airport', 'aisle', 'alarm', 'album', 
    'alcohol', 'alert', 'alien', 'all', 'alley', 'allow', 'almost', 'alone', 
    'alpha', 'already', 'also', 'alter', 'always', 'amateur', 'amazing', 'among', 
    'amount', 'amused', 'analyst', 'anchor', 'ancient', 'anger', 'angle', 'angry', 
    'animal', 'ankle', 'announce', 'annual', 'another', 'answer', 'antenna', 'antique', 
    'anxiety', 'any', 'apart', 'apology', 'appear', 'apple', 'approve', 'april', 
    'arch', 'arctic', 'area', 'arena', 'argue', 'arm', 'armed', 'armor', 
    'army', 'around', 'arrange', 'arrest', 'arrive', 'arrow', 'art', 'artefact', 
    'artist', 'artwork', 'ask', 'aspect', 'assault', 'asset', 'assist', 'assume', 
    'asthma', 'athlete', 'atom', 'attack', 'attend', 'attitude', 'attract', 'auction', 
    'audit', 'august', 'aunt', 'author', 'auto', 'autumn', 'average', 'avocado', 
    'avoid', 'awake', 'aware', 'away', 'awesome', 'awful', 'awkward', 'axis',
    'wrong', 'yellow', 'zebra', 'zoo'
}

def extract_artifacts_from_html(html_content, url="https://example.com", date=None):
    """
    Extract Ethereum artifacts from HTML content.
    
    Args:
        html_content: HTML content to parse
        url: Source URL for scoring
        date: Date of the content for scoring
        
    Returns:
        List of artifact dictionaries
    """
    logger.info(f"Extracting artifacts from URL: {url}")
    
    # Check if html_content is None (non-HTML content)
    if html_content is None:
        logger.warning(f"No HTML content to parse for URL: {url}")
        return []
    
    # Add content length to debug log
    content_length = len(html_content) if html_content else 0
    logger.debug(f"Content length: {content_length} bytes for URL: {url}")
    
    # Check for extremely small content
    if content_length < 100:
        logger.warning(f"Content too small ({content_length} bytes) for URL: {url}")
        if content_length > 0:
            logger.debug(f"Content preview: {html_content}")
        return []
    
    # Log content preview for debugging
    if content_length > 0:
        preview = html_content[:500] + "..." if content_length > 500 else html_content
        logger.debug(f"Content preview: {preview}")
    
    # Parse HTML
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        logger.debug(f"Successfully parsed HTML for URL: {url}")
    except Exception as e:
        logger.error(f"Error parsing HTML from {url}: {str(e)}")
        return []
    
    # Initialize artifacts list
    artifacts = []
    
    # Track artifact hashes to avoid duplicates
    artifact_hashes = set()
    
    # Process different artifact types with debugging
    solidity_artifacts = extract_solidity_contracts(soup, url, date, artifact_hashes)
    logger.debug(f"Found {len(solidity_artifacts)} Solidity contracts")
    artifacts.extend(solidity_artifacts)
    
    wallet_artifacts = extract_wallet_addresses(soup, url, date, artifact_hashes)
    logger.debug(f"Found {len(wallet_artifacts)} wallet addresses")
    artifacts.extend(wallet_artifacts)
    
    private_key_artifacts = extract_private_keys(soup, url, date, artifact_hashes)
    logger.debug(f"Found {len(private_key_artifacts)} private keys")
    artifacts.extend(private_key_artifacts)
    
    keystore_artifacts = extract_json_keystores(soup, url, date, artifact_hashes)
    logger.debug(f"Found {len(keystore_artifacts)} JSON keystores")
    artifacts.extend(keystore_artifacts)
    
    seed_artifacts = extract_seed_phrases(soup, url, date, artifact_hashes)
    logger.debug(f"Found {len(seed_artifacts)} seed phrases")
    artifacts.extend(seed_artifacts)
    
    api_artifacts = extract_api_keys(soup, url, date, artifact_hashes)
    logger.debug(f"Found {len(api_artifacts)} API keys")
    artifacts.extend(api_artifacts)
    
    # Store high-scoring artifacts
    store_artifacts(artifacts)
    
    # Log detailed results
    if artifacts:
        logger.info(f"Extracted {len(artifacts)} artifacts from {url}")
        for i, artifact in enumerate(artifacts):
            logger.debug(f"Artifact {i+1}: Type={artifact.get('type', 'unknown')}, Score={artifact.get('score', 0)}")
    else:
        logger.warning(f"No artifacts found in {url}")
    
    return artifacts

def extract_solidity_contracts(soup, url, date, artifact_hashes):
    """Extract Solidity smart contracts from HTML."""
    artifacts = []
    
    # Find code blocks
    code_blocks = soup.find_all(['pre', 'code'])
    for i, code_block in enumerate(code_blocks):
        code_text = code_block.get_text()
        
        # Look for Solidity contract definitions
        contract_matches = re.finditer(r'contract\s+(\w+)\s*{', code_text)
        for match in contract_matches:
            contract_name = match.group(1)
            
            # Get contract code
            start_pos = match.start()
            # Simple bracket matching to find contract end
            open_braces = 0
            end_pos = start_pos
            
            for j in range(start_pos, len(code_text)):
                if code_text[j] == '{':
                    open_braces += 1
                elif code_text[j] == '}':
                    open_braces -= 1
                    if open_braces == 0:
                        end_pos = j + 1
                        break
            
            if end_pos > start_pos:
                contract_code = code_text[start_pos:end_pos]
                
                # Check for duplicates
                artifact_hash = generate_hash(contract_code)
                if artifact_hash in artifact_hashes:
                    continue
                
                artifact_hashes.add(artifact_hash)
                
                # Score and create artifact
                score = score_artifact(url, contract_code, date)
                
                # Truncate for summary if needed
                summary = contract_code
                if len(summary) > 100:
                    summary = summary[:97] + "..."
                
                artifacts.append({
                    'type': 'solidity_contract',
                    'content': contract_code,
                    'summary': f"Contract {contract_name}: {summary}",
                    'location': f"Code block #{i+1}",
                    'hash': artifact_hash,
                    'score': score,
                    'url': url,
                    'date': date
                })
    
    return artifacts

def extract_wallet_addresses(soup, url, date, artifact_hashes):
    """Extract Ethereum wallet addresses from HTML."""
    artifacts = []
    
    # Search for Ethereum addresses
    text = soup.get_text()
    address_matches = re.finditer(r'0x[0-9a-fA-F]{40}', text)
    
    for match in address_matches:
        address = match.group(0)
        
        # Check for duplicates
        artifact_hash = generate_hash(address)
        if artifact_hash in artifact_hashes:
            continue
        
        artifact_hashes.add(artifact_hash)
        
        # Score and create artifact
        score = score_artifact(url, address, date)
        
        # For addresses, we can show the full content
        artifacts.append({
            'type': 'wallet_address',
            'content': address,
            'summary': address,
            'location': find_location(soup, address),
            'hash': artifact_hash,
            'score': score,
            'url': url,
            'date': date
        })
    
    return artifacts

def extract_private_keys(soup, url, date, artifact_hashes):
    """Extract Ethereum private keys from HTML."""
    artifacts = []
    
    # Search for private keys (64-character hex strings)
    text = soup.get_text()
    private_key_matches = re.finditer(r'(?:private\s*key|secret\s*key|key)(?:\s*[:=])?\s*(?:\'|")?([0-9a-fA-F]{64})(?:\'|")?', text, re.IGNORECASE)
    
    for match in private_key_matches:
        private_key = match.group(1)
        
        # Check for duplicates
        artifact_hash = generate_hash(private_key)
        if artifact_hash in artifact_hashes:
            continue
        
        artifact_hashes.add(artifact_hash)
        
        # Score and create artifact
        score = score_artifact(url, private_key, date)
        
        # For private keys, we must redact the content in the summary
        artifacts.append({
            'type': 'private_key',
            'content': private_key,  # Full content stored for processing
            'summary': f"[private key redacted - {len(private_key)} chars]",
            'location': find_location(soup, private_key),
            'hash': artifact_hash,
            'score': score,
            'url': url,
            'date': date
        })
    
    # Also look for standalone 64-char hex strings
    hex_matches = re.finditer(r'0x[0-9a-fA-F]{64}', text)
    for match in hex_matches:
        hex_string = match.group(0)
        
        # Check for duplicates
        artifact_hash = generate_hash(hex_string)
        if artifact_hash in artifact_hashes:
            continue
        
        artifact_hashes.add(artifact_hash)
        
        # Score and create artifact
        score = score_artifact(url, hex_string, date)
        
        # Redact for summary
        artifacts.append({
            'type': 'private_key',
            'content': hex_string,  # Full content stored for processing
            'summary': f"[private key redacted - {len(hex_string)} chars]",
            'location': find_location(soup, hex_string),
            'hash': artifact_hash,
            'score': score,
            'url': url,
            'date': date
        })
    
    return artifacts

def extract_json_keystores(soup, url, date, artifact_hashes):
    """Extract Ethereum JSON keystores from HTML."""
    artifacts = []
    
    # Find code blocks that might contain JSON
    code_blocks = soup.find_all(['pre', 'code'])
    for i, code_block in enumerate(code_blocks):
        code_text = code_block.get_text()
        
        # Check if it looks like a keystore JSON
        if ('crypto' in code_text.lower() and 
            'cipher' in code_text.lower() and 
            'kdf' in code_text.lower() and 
            'address' in code_text.lower()):
            
            try:
                # Try to parse as JSON
                start_idx = code_text.find('{')
                end_idx = code_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = code_text[start_idx:end_idx]
                    json_obj = json.loads(json_text)
                    
                    # Verify it's a v3 keystore
                    if 'version' in json_obj and json_obj['version'] == 3:
                        # Check for duplicates
                        artifact_hash = generate_hash(json_text)
                        if artifact_hash in artifact_hashes:
                            continue
                        
                        artifact_hashes.add(artifact_hash)
                        
                        # Score and create artifact
                        score = score_artifact(url, json_text, date)
                        
                        # Redact for summary
                        artifacts.append({
                            'type': 'ethereum_keystore',
                            'content': json_text,  # Full content stored for processing
                            'summary': f"[JSON keystore redacted] - v3 keystore for address 0x{json_obj.get('address', '')}",
                            'location': f"Code block #{i+1}",
                            'hash': artifact_hash,
                            'score': score,
                            'url': url,
                            'date': date
                        })
            except Exception as e:
                logger.debug(f"Error parsing potential JSON keystore: {str(e)}")
    
    return artifacts

def extract_seed_phrases(soup, url, date, artifact_hashes):
    """Extract BIP39 seed phrases from HTML."""
    artifacts = []
    
    # Find text that might contain seed phrases
    text = soup.get_text()
    
    # Look for sections mentioning mnemonic or seed phrases
    mnemonic_sections = re.finditer(r'(?:mnemonic|seed\s+phrase|recovery\s+phrase|backup\s+phrase)(?:\s*[:=])?\s*(?:\'|")?([a-z\s]+)(?:\'|")?', text, re.IGNORECASE)
    
    for match in mnemonic_sections:
        phrase_text = match.group(1).strip().lower()
        words = phrase_text.split()
        
        # Check if it's a valid length for BIP39 (12, 15, 18, 21, or 24 words)
        if len(words) in [12, 15, 18, 21, 24]:
            # Check if all words are in BIP39 wordlist
            if all(word in BIP39_WORDS for word in words):
                # Check for duplicates
                artifact_hash = generate_hash(phrase_text)
                if artifact_hash in artifact_hashes:
                    continue
                
                artifact_hashes.add(artifact_hash)
                
                # Score and create artifact
                score = score_artifact(url, phrase_text, date)
                
                # Redact for summary
                artifacts.append({
                    'type': 'seed_phrase',
                    'content': phrase_text,  # Full content stored for processing
                    'summary': f"[{len(words)}-word seed phrase redacted]",
                    'location': find_location(soup, phrase_text),
                    'hash': artifact_hash,
                    'score': score,
                    'url': url,
                    'date': date
                })
    
    # Also check for phrases with a specific number of words
    text_blocks = []
    for tag in soup.find_all(['p', 'pre', 'code']):
        text_blocks.append(tag.get_text())
    
    for i, block in enumerate(text_blocks):
        words = block.lower().split()
        if len(words) in [12, 15, 18, 21, 24]:
            # Check if all words are in BIP39 wordlist
            valid_words = [w for w in words if w in BIP39_WORDS]
            if len(valid_words) in [12, 15, 18, 21, 24]:
                phrase_text = ' '.join(valid_words)
                
                # Check for duplicates
                artifact_hash = generate_hash(phrase_text)
                if artifact_hash in artifact_hashes:
                    continue
                
                artifact_hashes.add(artifact_hash)
                
                # Score and create artifact
                score = score_artifact(url, phrase_text, date)
                
                # Redact for summary
                artifacts.append({
                    'type': 'seed_phrase',
                    'content': phrase_text,  # Full content stored for processing
                    'summary': f"[{len(valid_words)}-word seed phrase redacted]",
                    'location': f"Text block #{i+1}",
                    'hash': artifact_hash,
                    'score': score,
                    'url': url,
                    'date': date
                })
    
    return artifacts

def extract_api_keys(soup, url, date, artifact_hashes):
    """Extract API keys (Infura, Alchemy, Etherscan) from HTML."""
    artifacts = []
    
    # Find code blocks
    code_blocks = soup.find_all(['pre', 'code'])
    for i, code_block in enumerate(code_blocks):
        code_text = code_block.get_text()
        
        # Look for Infura endpoints
        infura_matches = re.finditer(r'https?://[^"\']*infura\.io/v3/([0-9a-fA-F]{32})', code_text)
        for match in infura_matches:
            api_key = match.group(1)
            
            # Check for duplicates
            artifact_hash = generate_hash(api_key)
            if artifact_hash in artifact_hashes:
                continue
            
            artifact_hashes.add(artifact_hash)
            
            # Score and create artifact
            score = score_artifact(url, api_key, date)
            
            # Redact for summary
            artifacts.append({
                'type': 'api_key',
                'content': api_key,  # Full content stored for processing
                'summary': f"[Infura API key redacted - {len(api_key)} chars]",
                'location': f"Code block #{i+1}",
                'hash': artifact_hash,
                'score': score,
                'url': url,
                'date': date
            })
        
        # Look for Alchemy endpoints
        alchemy_matches = re.finditer(r'https?://[^"\']*alchemy\.com/v2/([0-9a-zA-Z]{32,})', code_text)
        for match in alchemy_matches:
            api_key = match.group(1)
            
            # Check for duplicates
            artifact_hash = generate_hash(api_key)
            if artifact_hash in artifact_hashes:
                continue
            
            artifact_hashes.add(artifact_hash)
            
            # Score and create artifact
            score = score_artifact(url, api_key, date)
            
            # Redact for summary
            artifacts.append({
                'type': 'api_key',
                'content': api_key,  # Full content stored for processing
                'summary': f"[Alchemy API key redacted - {len(api_key)} chars]",
                'location': f"Code block #{i+1}",
                'hash': artifact_hash,
                'score': score,
                'url': url,
                'date': date
            })
        
        # Look for Etherscan API keys
        etherscan_matches = re.finditer(r'(?:etherscan|ETHERSCAN).*?(?:apikey|ApiKey|APIKEY).*?[\'"]([A-Za-z0-9]{34,})[\'"]', code_text)
        for match in etherscan_matches:
            api_key = match.group(1)
            
            # Check for duplicates
            artifact_hash = generate_hash(api_key)
            if artifact_hash in artifact_hashes:
                continue
            
            artifact_hashes.add(artifact_hash)
            
            # Score and create artifact
            score = score_artifact(url, api_key, date)
            
            # Redact for summary
            artifacts.append({
                'type': 'api_key',
                'content': api_key,  # Full content stored for processing
                'summary': f"[Etherscan API key redacted - {len(api_key)} chars]",
                'location': f"Code block #{i+1}",
                'hash': artifact_hash,
                'score': score,
                'url': url,
                'date': date
            })
    
    return artifacts

def score_artifact(url, content, date):
    """
    Score an artifact based on source and content.
    
    Args:
        url: Source URL
        content: Artifact content
        date: Content date
        
    Returns:
        Score value (int)
    """
    score = 0
    
    # Domain scoring
    domain = urlparse(url).netloc
    
    # +3 for trusted domains
    if any(domain.endswith(trusted) for trusted in TRUSTED_DOMAINS):
        score += 3
    
    # +1 for .org TLD
    if domain.endswith('.org'):
        score += 1
    
    # -5 for community domains
    if any(domain.endswith(community) for community in COMMUNITY_DOMAINS):
        score -= 5
    
    # Date scoring
    if date and date < "2022-01-01":
        # +1 for pre-2022 snapshot
        score += 1
    
    # Content scoring
    content_lower = content.lower()
    
    # -10 for warning phrases
    if any(warning in content_lower for warning in WARNING_PHRASES):
        score -= 10
    
    # +2 for syntactically valid artifacts (would add validation logic here)
    # This is simplified for the example
    if len(content) > 20:
        score += 2
    
    return score

def find_location(soup, text):
    """Find location of text in the HTML."""
    # Simplified location finding
    for i, tag in enumerate(soup.find_all(['pre', 'code', 'p'])):
        if text in tag.get_text():
            tag_type = tag.name
            return f"{tag_type} #{i+1}"
    
    return "Unknown location"

def generate_hash(content):
    """Generate a unique hash for artifact deduplication."""
    # Normalize by removing whitespace and converting to lowercase
    normalized = re.sub(r'\s+', '', content.lower())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def store_artifacts(artifacts):
    """Store high-scoring artifacts."""
    today = datetime.now().strftime('%Y-%m-%d')
    artifacts_dir = f'{base_dir}/results/artifacts/{today}'
    os.makedirs(artifacts_dir, exist_ok=True)
    
    # Store high-scoring artifacts in found.txt
    with open(f'{base_dir}/results/found.txt', 'a') as found_file:
        for artifact in artifacts:
            if artifact['score'] > 0:
                # Store as JSON
                artifact_path = f"{artifacts_dir}/{artifact['hash']}.json"
                
                # Create a safe version for storage
                safe_artifact = artifact.copy()
                
                # For sensitive artifacts, replace content with a hash reference
                if artifact['type'] in ['private_key', 'seed_phrase', 'api_key']:
                    # Replace the actual content with a reference
                    safe_artifact['content_hash'] = artifact['hash']
                    safe_artifact.pop('content', None)
                
                with open(artifact_path, 'w') as f:
                    json.dump(safe_artifact, f, indent=2)
                
                # Log to found.txt
                found_file.write(f"URL: {artifact['url']}\n")
                found_file.write(f"Type: {artifact['type']}\n")
                found_file.write(f"Score: {artifact['score']}\n")
                found_file.write(f"Location: {artifact['location']}\n")
                found_file.write(f"Summary: {artifact['summary']}\n")
                found_file.write(f"File: {artifact_path}\n")
                found_file.write("-" * 80 + "\n")
    
    return len([a for a in artifacts if a['score'] > 0])