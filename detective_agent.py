#!/usr/bin/env python3
"""
Detective Agent for Narrahunt Phase 2.

This module implements an autonomous research agent that follows leads
and discovers artifacts related to narrative objectives. It acts as the
central reasoning engine that coordinates between different components.
"""

import os
import re
import json
import time
import logging
import random
import sys
import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from urllib.parse import urlparse, urljoin

# Import internal modules
from narrative_matrix import NarrativeMatrix
from llm_integration import LLMIntegration
from crawler import Crawler
from wayback_integration import WaybackMachine
from artifact_extractor import extract_artifacts_from_html
from config_loader import get_api_key
from fetch import fetch_page  # Import fetch_page directly

# Configure logging
base_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(base_dir, 'logs'), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(base_dir, 'logs', 'detective.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('detective_agent')

class DetectiveAgent:
    """
    Autonomous research agent that follows leads and discovers artifacts.
    
    This agent acts as a detective, following breadcrumbs and investigating
    leads to uncover information relevant to the research objective.
    """
    
    def __init__(self, objective: str, entity: str, max_iterations: int = 50, 
                 max_time_hours: float = 24.0, max_idle_iterations: int = 5):
        """
        Initialize the detective agent.
        
        Args:
            objective: The research objective (e.g., "Find name artifacts around Vitalik Buterin")
            entity: The primary entity to investigate (e.g., "Vitalik Buterin")
            max_iterations: Maximum number of investigation iterations
            max_time_hours: Maximum runtime in hours
            max_idle_iterations: Maximum number of iterations without new discoveries
        """
        self.objective = objective
        self.entity = entity
        self.max_iterations = max_iterations
        self.max_time_seconds = max_time_hours * 3600
        self.max_idle_iterations = max_idle_iterations
        
        # Initialize components
        self.narrative_matrix = NarrativeMatrix()
        self.llm = LLMIntegration(use_claude=True)
        self.crawler = Crawler()
        self.wayback = WaybackMachine()
        
        # Research state
        self.research_queue = []
        self.investigated_urls = set()
        self.discoveries = []
        self.iteration_discoveries = {}
        self.current_iteration = 0
        self.idle_iterations = 0
        self.start_time = time.time()
        
        # Research metadata
        self.investigation_strategies = {}
        self.entity_aliases = set([entity])
        
        # Set priority domains that are likely to contain valuable artifacts
        self.priority_domains = set([
            'vitalik.ca',
            'bitcointalk.org',
            'github.com',
            'ethereum.org',
            'blog.ethereum.org',
            'ethereum.foundation'
        ])
        
        self.investigation_history = []
        
        # Create results directory
        self.results_dir = os.path.join(base_dir, 'results', 'detective')
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Initialize research log
        self.research_log_path = os.path.join(self.results_dir, f'research_log_{int(time.time())}.jsonl')
        
        logger.info(f"Detective Agent initialized with objective: {objective}")
        logger.info(f"Primary entity: {entity}")
    
    def start_investigation(self):
        """Start the investigation process."""
        logger.info("Starting investigation...")
        
        # Initialize research state
        self._initialize_research()
        
        # Main investigation loop
        while self._should_continue_investigation():
            self.current_iteration += 1
            logger.info(f"\n{'='*80}\nStarting iteration {self.current_iteration}/{self.max_iterations}\n{'='*80}")
            
            # Get next investigation target
            target = self._get_next_investigation_target()
            if not target:
                logger.warning("No more targets to investigate")
                self.idle_iterations += 1
                if self.idle_iterations >= self.max_idle_iterations:
                    logger.info(f"Reached maximum idle iterations ({self.max_idle_iterations})")
                    break
                
                # Ask the LLM for new investigation ideas
                self._generate_new_leads()
                continue
            
            # Execute the investigation
            new_discoveries = self._execute_investigation(target)
            
            # Track discoveries for this iteration
            self.iteration_discoveries[self.current_iteration] = new_discoveries
            
            # Reset idle iterations if we found something
            if new_discoveries:
                self.idle_iterations = 0
                
                # Consult LLM for next steps based on new discoveries
                new_targets = self._consult_llm_for_next_steps(new_discoveries)
                self._update_research_queue(new_targets)
                
                # Log the investigation results
                self._log_investigation_results(target, new_discoveries, new_targets)
            else:
                # No new discoveries in this iteration
                logger.info(f"No new discoveries in iteration {self.current_iteration}")
                self.idle_iterations += 1
            
            # Save state after each iteration
            self._save_state()
        
        logger.info(f"Investigation completed after {self.current_iteration} iterations")
        logger.info(f"Total discoveries: {len(self.discoveries)}")
        
        # Generate final report
        self._generate_investigation_report()
        
        return self.discoveries
    
    def _initialize_research(self):
        """Initialize the research state with initial targets and strategies."""
        logger.info("Initializing research...")
        
        # Get initial research strategy from LLM
        initial_strategy = self._get_initial_research_strategy()
        
        # Extract initial targets from the strategy
        initial_targets = []
        
        # Add websites to check
        for source in initial_strategy.get('sources', []):
            if self._is_valid_url(source):
                initial_targets.append({
                    'url': source,
                    'type': 'website',
                    'priority': 10,
                    'rationale': 'Initial source from research strategy',
                    'use_wayback': True
                })
            else:
                # If it's not a URL but a source name, add it to prioritized domains
                domain = self._extract_domain(source)
                if domain:
                    self.priority_domains.add(domain)
        
        # Add search queries
        for query in initial_strategy.get('search_queries', []):
            initial_targets.append({
                'query': query,
                'type': 'search',
                'priority': 8,
                'rationale': 'Initial search query from research strategy',
                'engine': 'google'
            })
        
        # Update the research queue with initial targets
        logger.info(f"Adding {len(initial_targets)} initial targets to research queue")
        self._update_research_queue(initial_targets)
        
        # Log the initialization
        self._log_to_research_log({
            'event': 'initialization',
            'timestamp': self._get_timestamp(),
            'objective': self.objective,
            'entity': self.entity,
            'initial_strategy': initial_strategy,
            'initial_targets': initial_targets
        })
    
    def _get_initial_research_strategy(self) -> Dict[str, Any]:
        """Get the initial research strategy from the LLM."""
        logger.info("Getting initial research strategy from LLM...")
        
        # Use LLM to generate research strategy
        strategy = self.llm.generate_research_strategy(self.objective, self.entity)
        
        # Log the strategy
        logger.info(f"Initial research strategy obtained:")
        logger.info(f"Sources: {strategy.get('sources', [])}")
        logger.info(f"Search queries: {strategy.get('search_queries', [])}")
        logger.info(f"Information types: {strategy.get('information_types', [])}")
        
        # If strategy is empty or missing critical components, add fallback values for testing
        if not strategy.get('sources') and not strategy.get('search_queries'):
            logger.warning("LLM returned empty strategy, adding fallback values for testing")
            strategy['sources'] = [
                # Direct links to high-value, artifact-rich pages
                "https://github.com/vbuterin",  # GitHub profile
                "https://bitcointalk.org/index.php?action=profile;u=11772",  # BitcoinTalk profile (known username)
                "https://ethereum.org/en/history/",  # Ethereum history page
                "https://ethereum.org/en/foundation/",  # Foundation page with potential names
                "https://github.com/ethereum/wiki/wiki/Vitalik-Buterin",  # Wiki page about Vitalik
                
                # Repository pages with potential commit history and usernames
                "https://github.com/vbuterin?tab=repositories",
                "https://github.com/ethereum/EIPs/graphs/contributors",
                "https://github.com/ethereum/yellowpaper/graphs/contributors",
                
                # Wayback Machine archives for historical content
                "https://web.archive.org/web/20140601000000/http://vitalik.ca",
                "https://web.archive.org/web/20150601000000/http://vitalik.ca/about.html",
                "https://web.archive.org/web/20131201000000/https://bitcointalk.org/index.php?action=profile;u=11772"
            ]
            # Replace vague search queries with direct, specific URLs
            strategy['search_queries'] = []
            strategy['information_types'] = [
                "usernames",
                "handles",
                "email addresses",
                "social media profiles"
            ]
        
        return strategy
    
    def _execute_investigation(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute an investigation on a target.
        
        Args:
            target: The investigation target
            
        Returns:
            List of new discoveries
        """
        target_type = target.get('type', 'unknown')
        
        if target_type == 'website':
            return self._investigate_website(target)
        elif target_type == 'search':
            return self._execute_search(target)
        elif target_type == 'wayback':
            return self._investigate_wayback(target)
        elif target_type == 'github':
            return self._investigate_github(target)
        else:
            logger.warning(f"Unknown target type: {target_type}")
            return []
    
    def _investigate_website(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Investigate a website target."""
        url = target.get('url')
        
        if not url:
            logger.warning("Website target missing URL")
            return []
        
        # Special handling for Wayback Machine calendar URLs (containing *)
        if '*' in url and 'web.archive.org/web/' in url:
            logger.info(f"Detected Wayback calendar URL: {url}")
            return self._investigate_wayback_calendar(url)
        
        if url in self.investigated_urls:
            logger.info(f"URL already investigated: {url}")
            return []
        
        logger.info(f"Investigating website: {url}")
        self.investigated_urls.add(url)
        
        # Crawl the website
        try:
            # Use fetch_page directly instead of self.crawler.fetch_url
            html_content, response_info = fetch_page(url)
            final_url = response_info.get('final_url', url) if response_info else url
            
            if not html_content:
                logger.warning(f"Failed to fetch content from {url}")
                
                # If fetch failed, try Wayback Machine if enabled
                if target.get('use_wayback', False):
                    logger.info(f"Trying Wayback Machine for {url}")
                    return self._investigate_wayback({'url': url, 'type': 'wayback'})
                return []
            
            # Extract artifacts from the content
            logger.info(f"Extracting artifacts from {len(html_content)} bytes of content from {final_url}")
            artifacts = extract_artifacts_from_html(html_content, final_url)
            logger.info(f"Found {len(artifacts)} artifacts from {final_url}")
            
            # Process the artifacts into discoveries
            discoveries = self._process_artifacts(artifacts, url)
            
            # If use_wayback is enabled, also check historical versions
            if target.get('use_wayback', False) and not url.startswith('https://web.archive.org/'):
                # Add wayback investigation to the queue with lower priority
                self._update_research_queue([{
                    'url': url,
                    'type': 'wayback',
                    'priority': target.get('priority', 5) - 2,
                    'rationale': f'Historical investigation of {url}',
                    'year_range': target.get('year_range', (2013, datetime.datetime.now().year))
                }])
            
            return discoveries
        
        except Exception as e:
            logger.error(f"Error investigating website {url}: {str(e)}")
            return []
    
    def _investigate_wayback_calendar(self, calendar_url: str) -> List[Dict[str, Any]]:
        """
        Investigate a Wayback Machine calendar URL (with * wildcard).
        
        Args:
            calendar_url: The Wayback Machine calendar URL
        
        Returns:
            List of discoveries
        """
        # Extract the timestamp and original URL from the calendar URL
        # Various possible formats:
        # - https://web.archive.org/web/YYYYMMDDHHMMSS*/https://original.url
        # - https://web.archive.org/web/YYYY*/https://original.url
        
        # Try to match with full timestamp format first
        match = re.match(r'https://web\.archive\.org/web/(\d{4,14})\*/(.+)', calendar_url)
        if not match:
            logger.warning(f"Invalid Wayback calendar URL format: {calendar_url}")
            return []
        
        timestamp = match.group(1)
        original_url = match.group(2)
        
        # Extract year from the timestamp (first 4 digits)
        year = timestamp[:4]
        
        logger.info(f"Processing Wayback calendar for {original_url} from year {year}")
        
        # Convert the Wayback calendar URL to a direct snapshot URL
        # This ensures we're looking at actual archived content
        wayback_url = f"https://web.archive.org/web/{timestamp}/http://{original_url.replace('https://', '').replace('http://', '')}"
        
        logger.info(f"Converted calendar URL to direct snapshot URL: {wayback_url}")
        
        # Directly investigate the wayback URL
        try:
            html_content, response_info = fetch_page(wayback_url)
            
            if not html_content:
                logger.warning(f"Failed to fetch content from direct Wayback URL: {wayback_url}")
                
                # Fall back to year-based search if direct URL fails
                return self._investigate_wayback({
                    'url': original_url,
                    'type': 'wayback',
                    'year_range': (int(year), int(year))
                })
            
            logger.info(f"Extracting artifacts from {len(html_content)} bytes of Wayback content from {wayback_url}")
            artifacts = extract_artifacts_from_html(html_content, wayback_url, date=timestamp)
            logger.info(f"Found {len(artifacts)} artifacts from Wayback snapshot {wayback_url}")
            
            # Process the artifacts into discoveries
            return self._process_artifacts(artifacts, wayback_url, is_wayback=True, original_url=original_url)
            
        except Exception as e:
            logger.error(f"Error investigating direct Wayback URL {wayback_url}: {str(e)}")
            
            # Fall back to year-based search if direct URL fails
            return self._investigate_wayback({
                'url': original_url,
                'type': 'wayback',
                'year_range': (int(year), int(year))
            })
    
    def _investigate_wayback(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Investigate a URL using the Wayback Machine."""
        url = target.get('url')
        
        if not url:
            logger.warning("Wayback target missing URL")
            return []
        
        wayback_url = f"wayback:{url}"
        if wayback_url in self.investigated_urls:
            logger.info(f"Wayback URL already investigated: {url}")
            return []
        
        logger.info(f"Investigating historical versions of: {url}")
        self.investigated_urls.add(wayback_url)
        
        # Get year range
        year_range = target.get('year_range', (2013, datetime.datetime.now().year))
        
        # Get snapshots from Wayback Machine
        try:
            # Convert years to strings for the API
            from_date = str(year_range[0])
            to_date = str(year_range[1])
            snapshots = self.wayback.get_snapshots(url, from_date=from_date, to_date=to_date)
            
            if not snapshots:
                logger.warning(f"No Wayback Machine snapshots found for {url}")
                return []
            
            logger.info(f"Found {len(snapshots)} Wayback Machine snapshots for {url}")
            
            # Sample snapshots if there are too many
            if len(snapshots) > 5:
                # Get earliest, latest, and 3 random snapshots in between
                sorted_snapshots = sorted(snapshots, key=lambda x: x.get('timestamp', ''))
                selected_snapshots = [
                    sorted_snapshots[0],  # Earliest
                    sorted_snapshots[-1]  # Latest
                ]
                
                # Add 3 random snapshots if available
                if len(sorted_snapshots) > 2:
                    middle_snapshots = sorted_snapshots[1:-1]
                    random_samples = random.sample(middle_snapshots, min(3, len(middle_snapshots)))
                    selected_snapshots.extend(random_samples)
            else:
                selected_snapshots = snapshots
            
            all_discoveries = []
            
            # Investigate each selected snapshot
            for snapshot in selected_snapshots:
                # Check for 'wayback_url' which is the field used in wayback_integration.py
                snapshot_url = snapshot.get('wayback_url')
                if not snapshot_url:
                    logger.warning(f"Missing wayback_url in snapshot: {snapshot}")
                    continue
                
                logger.info(f"Investigating Wayback snapshot: {snapshot_url}")
                
                try:
                    # Use fetch_page directly instead of self.crawler.fetch_url
                    html_content, response_info = fetch_page(snapshot_url)
                    
                    if not html_content:
                        logger.warning(f"Failed to fetch content from Wayback snapshot: {snapshot_url}")
                        continue
                    
                    # Extract artifacts from the content
                    logger.info(f"Extracting artifacts from {len(html_content)} bytes of Wayback content from {snapshot_url}")
                    artifacts = extract_artifacts_from_html(html_content, snapshot_url, date=snapshot.get('timestamp'))
                    logger.info(f"Found {len(artifacts)} artifacts from Wayback snapshot {snapshot_url}")
                    
                    # Process the artifacts into discoveries
                    discoveries = self._process_artifacts(artifacts, snapshot_url, is_wayback=True, original_url=url)
                    all_discoveries.extend(discoveries)
                    
                except Exception as e:
                    logger.error(f"Error investigating Wayback snapshot {snapshot_url}: {str(e)}")
            
            return all_discoveries
        
        except Exception as e:
            logger.error(f"Error investigating Wayback for {url}: {str(e)}")
            return []
    
    def _execute_search(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a search query and process the results."""
        query = target.get('query')
        
        if not query:
            logger.warning("Search target missing query")
            return []
        
        search_key = f"search:{query}"
        if search_key in self.investigated_urls:
            logger.info(f"Search query already executed: {query}")
            return []
        
        logger.info(f"Executing search query: {query}")
        self.investigated_urls.add(search_key)
        
        # Execute the search
        try:
            # Convert query string to a list of keywords
            keywords = query.split()
            search_results = self.crawler.search(keywords, max_results=10)
            
            if not search_results:
                logger.warning(f"No search results found for query: {query}")
                return []
            
            logger.info(f"Found {len(search_results)} search results for query: {query}")
            
            # Add search results to the research queue
            search_targets = []
            for result in search_results[:10]:  # Limit to top 10 results
                result_url = result.get('url')
                if not result_url or result_url in self.investigated_urls:
                    continue
                
                search_targets.append({
                    'url': result_url,
                    'type': 'website',
                    'priority': target.get('priority', 5) - 1,
                    'rationale': f'Search result for "{query}"',
                    'use_wayback': self._should_check_wayback(result_url)
                })
            
            self._update_research_queue(search_targets)
            
            # Return empty discoveries list since we just added targets to the queue
            return []
        
        except Exception as e:
            logger.error(f"Error executing search for {query}: {str(e)}")
            return []
    
    def _investigate_github(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Investigate a GitHub repository or user."""
        github_url = target.get('url')
        
        if not github_url:
            logger.warning("GitHub target missing URL")
            return []
        
        if github_url in self.investigated_urls:
            logger.info(f"GitHub URL already investigated: {github_url}")
            return []
        
        logger.info(f"Investigating GitHub: {github_url}")
        self.investigated_urls.add(github_url)
        
        # For now, treat GitHub URLs as regular websites
        # In a full implementation, we would use the GitHub API
        return self._investigate_website({'url': github_url, 'type': 'website'})
    
    def _process_artifacts(self, artifacts: List[Dict[str, Any]], source_url: str,
                          is_wayback: bool = False, original_url: str = None) -> List[Dict[str, Any]]:
        """
        Process artifacts into discoveries.
        
        Args:
            artifacts: List of artifacts from the artifact extractor
            source_url: The URL where the artifacts were found
            is_wayback: Whether this is from a Wayback Machine snapshot
            original_url: The original URL if is_wayback is True
            
        Returns:
            List of new discoveries
        """
        if not artifacts:
            return []
        
        logger.info(f"Processing {len(artifacts)} artifacts from {source_url}")
        
        new_discoveries = []
        
        for artifact in artifacts:
            # Skip low-scoring artifacts and prioritize high-value types
            score = artifact.get('score', 0)
            artifact_type = artifact.get('type', 'unknown')
            
            # Increase scores for high-value artifact types related to names
            if artifact_type in ['username', 'alias', 'wallet_address', 'private_key']:
                score += 2
            
            # Boost score for artifacts that match our entity or previously found aliases
            content = artifact.get('content', '').lower()
            if any(alias.lower() in content for alias in self.entity_aliases):
                score += 1
                
            # Skip artifacts that are still low-scoring after adjustments
            if score <= 0:
                continue
                
            # Update the artifact score with our adjustments
            artifact['score'] = score
            
            # Create a discovery from the artifact
            discovery = {
                'id': artifact.get('hash', str(len(self.discoveries) + len(new_discoveries) + 1)),
                'type': artifact.get('type', 'unknown'),
                'content': artifact.get('content', ''),
                'summary': artifact.get('summary', ''),
                'source_url': source_url,
                'original_url': original_url if is_wayback else source_url,
                'is_wayback': is_wayback,
                'date': artifact.get('date'),
                'score': artifact.get('score', 0),
                'timestamp': self._get_timestamp(),
                'iteration': self.current_iteration
            }
            
            # Check if this discovery is new
            if not self._is_duplicate_discovery(discovery):
                # Add to discoveries list
                self.discoveries.append(discovery)
                new_discoveries.append(discovery)
                
                # Update entity aliases if this is a name-related discovery
                if artifact.get('type') in ['username', 'alias', 'wallet_address']:
                    self.entity_aliases.add(artifact.get('content', ''))
            
            # Log the discovery
            logger.info(f"Discovery: {discovery['type']} - {discovery['summary']}")
        
        logger.info(f"Processed {len(new_discoveries)} new discoveries from {source_url}")
        return new_discoveries
    
    def _consult_llm_for_next_steps(self, discoveries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Consult the LLM for next investigation steps based on recent discoveries.
        
        Args:
            discoveries: Recent discoveries to analyze
            
        Returns:
            List of new investigation targets
        """
        if not discoveries:
            return []
        
        # Prepare context for the LLM
        context = self._prepare_llm_context(discoveries)
        
        # Build the prompt
        prompt = f"""
You are an expert digital detective investigating: "{self.objective}"

Recent findings:
{context}

Based on these findings, I need:
1. 3-5 specific URLs I should investigate next (with explanation for each)
2. 2-3 search queries I should run (with explanation for each)
3. Any specific archives, forums, or repositories to check
4. Any historical time periods I should focus on for Wayback Machine snapshots

Format your suggestions as a JSON object with the following structure:
{{
    "website_targets": [
        {{"url": "https://example.com/path", "rationale": "Explanation of why this is relevant"}}
    ],
    "search_queries": [
        {{"query": "example search query", "rationale": "Explanation of why this search would be valuable"}}
    ],
    "wayback_targets": [
        {{"url": "https://example.com", "year_range": [2013, 2016], "rationale": "Explanation of why checking these historical snapshots matters"}}
    ],
    "github_targets": [
        {{"url": "https://github.com/username/repo", "rationale": "Explanation of what to look for in this repository"}}
    ]
}}

Be specific, not generic. Use exact URLs and search terms tailored to our objective.
"""
        
        # Call the LLM
        try:
            # First try using analyze which expects a JSON response
            response = self.llm._call_claude(prompt)
            json_str = self.llm._extract_json(response)
            suggestions = json.loads(json_str)
            
            # Log the LLM suggestions
            logger.debug(f"LLM suggestions: {json.dumps(suggestions, indent=2)}")
            
            # Convert suggestions to investigation targets
            new_targets = []
            
            # Process website targets
            for target in suggestions.get('website_targets', []):
                url = target.get('url')
                if url and self._is_valid_url(url) and url not in self.investigated_urls:
                    new_targets.append({
                        'url': url,
                        'type': 'website',
                        'priority': 9,
                        'rationale': target.get('rationale', 'LLM suggestion'),
                        'use_wayback': self._should_check_wayback(url)
                    })
            
            # Process search queries
            for query in suggestions.get('search_queries', []):
                query_text = query.get('query')
                if query_text and f"search:{query_text}" not in self.investigated_urls:
                    new_targets.append({
                        'query': query_text,
                        'type': 'search',
                        'priority': 8,
                        'rationale': query.get('rationale', 'LLM suggestion'),
                        'engine': 'google'
                    })
            
            # Process Wayback targets
            for wayback in suggestions.get('wayback_targets', []):
                url = wayback.get('url')
                if url and self._is_valid_url(url) and f"wayback:{url}" not in self.investigated_urls:
                    new_targets.append({
                        'url': url,
                        'type': 'wayback',
                        'priority': 7,
                        'rationale': wayback.get('rationale', 'LLM suggestion for historical analysis'),
                        'year_range': wayback.get('year_range', [2013, datetime.datetime.now().year])
                    })
            
            # Process GitHub targets
            for github in suggestions.get('github_targets', []):
                url = github.get('url')
                if url and self._is_valid_url(url) and url not in self.investigated_urls:
                    new_targets.append({
                        'url': url,
                        'type': 'github',
                        'priority': 8,
                        'rationale': github.get('rationale', 'LLM suggestion for GitHub repository'),
                        'use_wayback': False
                    })
            
            # Log the LLM consultation
            self._log_to_research_log({
                'event': 'llm_consultation',
                'timestamp': self._get_timestamp(),
                'prompt': prompt,
                'response': response,
                'suggestions': suggestions,
                'new_targets': new_targets
            })
            
            return new_targets
            
        except Exception as e:
            logger.error(f"Error consulting LLM for next steps: {str(e)}")
            return []
    
    def _prepare_llm_context(self, discoveries: List[Dict[str, Any]]) -> str:
        """Prepare context for the LLM based on recent discoveries."""
        context_lines = []
        
        for i, discovery in enumerate(discoveries):
            discovery_type = discovery.get('type', 'unknown')
            summary = discovery.get('summary', '')
            source = discovery.get('source_url', '')
            
            context_line = f"{i+1}. [{discovery_type}] {summary} (Source: {source})"
            context_lines.append(context_line)
        
        # Add information about the entity aliases we've found
        if len(self.entity_aliases) > 1:
            aliases_str = ", ".join(f'"{alias}"' for alias in self.entity_aliases if alias != self.entity)
            if aliases_str:
                context_lines.append(f"\nKnown aliases for {self.entity}: {aliases_str}")
        
        return "\n".join(context_lines)
    
    def _generate_new_leads(self):
        """Generate new investigation leads when the queue is empty."""
        logger.info("Generating new investigation leads...")
        
        # Prepare context with all discoveries so far
        context = self._prepare_llm_context(self.discoveries)
        
        # Build the prompt
        prompt = f"""
You are an expert digital detective investigating: "{self.objective}"

So far, we've discovered:
{context}

We've hit a dead end and need fresh ideas. Based on what we've found so far:

1. What alternative sources should we check that we might have missed?
2. What new search strategies could yield more information?
3. Are there any connections between our findings that suggest new avenues to explore?
4. What historical periods or archives might contain relevant information?

Format your suggestions as a JSON object with the following structure:
{{
    "website_targets": [
        {{"url": "https://example.com/path", "rationale": "Explanation of why this is relevant"}}
    ],
    "search_queries": [
        {{"query": "example search query", "rationale": "Explanation of why this search would be valuable"}}
    ],
    "wayback_targets": [
        {{"url": "https://example.com", "year_range": [2013, 2016], "rationale": "Explanation of why checking these historical snapshots matters"}}
    ],
    "github_targets": [
        {{"url": "https://github.com/username/repo", "rationale": "Explanation of what to look for in this repository"}}
    ]
}}

Be creative and specific. Think of sources we haven't tried yet.
"""
        
        # Call the LLM
        try:
            response = self.llm._call_claude(prompt)
            json_str = self.llm._extract_json(response)
            suggestions = json.loads(json_str)
            
            # Convert suggestions to investigation targets
            new_targets = []
            
            # Process website targets
            for target in suggestions.get('website_targets', []):
                url = target.get('url')
                if url and self._is_valid_url(url) and url not in self.investigated_urls:
                    new_targets.append({
                        'url': url,
                        'type': 'website',
                        'priority': 7,  # Lower priority for these fallback targets
                        'rationale': target.get('rationale', 'LLM fallback suggestion'),
                        'use_wayback': self._should_check_wayback(url)
                    })
            
            # Process search queries
            for query in suggestions.get('search_queries', []):
                query_text = query.get('query')
                if query_text and f"search:{query_text}" not in self.investigated_urls:
                    new_targets.append({
                        'query': query_text,
                        'type': 'search',
                        'priority': 6,
                        'rationale': query.get('rationale', 'LLM fallback suggestion'),
                        'engine': 'google'
                    })
            
            # Process Wayback targets
            for wayback in suggestions.get('wayback_targets', []):
                url = wayback.get('url')
                if url and self._is_valid_url(url) and f"wayback:{url}" not in self.investigated_urls:
                    new_targets.append({
                        'url': url,
                        'type': 'wayback',
                        'priority': 5,
                        'rationale': wayback.get('rationale', 'LLM fallback suggestion for historical analysis'),
                        'year_range': wayback.get('year_range', [2013, datetime.datetime.now().year])
                    })
            
            # Process GitHub targets
            for github in suggestions.get('github_targets', []):
                url = github.get('url')
                if url and self._is_valid_url(url) and url not in self.investigated_urls:
                    new_targets.append({
                        'url': url,
                        'type': 'github',
                        'priority': 6,
                        'rationale': github.get('rationale', 'LLM fallback suggestion for GitHub repository'),
                        'use_wayback': False
                    })
            
            # Update the research queue
            self._update_research_queue(new_targets)
            
            # Log the new leads generation
            self._log_to_research_log({
                'event': 'new_leads_generation',
                'timestamp': self._get_timestamp(),
                'prompt': prompt,
                'response': response,
                'suggestions': suggestions,
                'new_targets': new_targets
            })
            
            logger.info(f"Generated {len(new_targets)} new investigation leads")
            
        except Exception as e:
            logger.error(f"Error generating new leads: {str(e)}")
    
    def _update_research_queue(self, new_targets: List[Dict[str, Any]]):
        """
        Update the research queue with new targets.
        
        Args:
            new_targets: List of new investigation targets
        """
        # Filter out targets that have already been investigated
        filtered_targets = []
        for target in new_targets:
            if target.get('type') == 'website' and target.get('url') in self.investigated_urls:
                continue
            if target.get('type') == 'wayback' and f"wayback:{target.get('url')}" in self.investigated_urls:
                continue
            if target.get('type') == 'search' and f"search:{target.get('query')}" in self.investigated_urls:
                continue
            if target.get('type') == 'github' and target.get('url') in self.investigated_urls:
                continue
            
            filtered_targets.append(target)
        
        # Add new targets to the research queue
        self.research_queue.extend(filtered_targets)
        
        # Sort the queue by priority (higher first)
        self.research_queue.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        logger.info(f"Added {len(filtered_targets)} new targets to the research queue")
        logger.info(f"Research queue now contains {len(self.research_queue)} targets")
    
    def _get_next_investigation_target(self) -> Optional[Dict[str, Any]]:
        """Get the next investigation target from the queue."""
        if not self.research_queue:
            return None
        
        # Get the highest priority target
        target = self.research_queue.pop(0)
        
        # Log the target selection
        logger.info(f"Selected target: {target.get('type')} - " +
                   (f"{target.get('url')}" if target.get('type') in ['website', 'wayback', 'github'] else
                    f"{target.get('query')}" if target.get('type') == 'search' else "Unknown"))
        
        return target
    
    def _should_continue_investigation(self) -> bool:
        """Determine if the investigation should continue."""
        # Check if we've reached the maximum number of iterations
        if self.current_iteration >= self.max_iterations:
            logger.info(f"Reached maximum iterations ({self.max_iterations})")
            return False
        
        # Check if we've been idle for too long
        if self.idle_iterations >= self.max_idle_iterations:
            logger.info(f"Reached maximum idle iterations ({self.max_idle_iterations})")
            return False
        
        # Check if we've exceeded the maximum runtime
        elapsed_time = time.time() - self.start_time
        if elapsed_time >= self.max_time_seconds:
            logger.info(f"Reached maximum runtime ({self.max_time_seconds} seconds)")
            return False
        
        return True
    
    def _is_duplicate_discovery(self, discovery: Dict[str, Any]) -> bool:
        """Check if a discovery is a duplicate of an existing one."""
        discovery_id = discovery.get('id')
        discovery_content = discovery.get('content', '')
        
        for existing in self.discoveries:
            if existing.get('id') == discovery_id:
                return True
            
            # For text-based artifacts, check content similarity
            if existing.get('content') == discovery_content and discovery_content:
                return True
        
        return False
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if a URL is valid."""
        if not url:
            return False
        
        try:
            result = urlparse(url)
            valid_format = all([result.scheme, result.netloc])
            
            if not valid_format:
                return False
            
            # Skip vitalik.ca direct URLs (DNS fails)
            if result.netloc == 'vitalik.ca' and not 'web.archive.org' in url:
                logger.warning(f"Skipping vitalik.ca direct URL (use Wayback instead): {url}")
                return False
            
            # Skip generic GitHub pages that never contain artifacts
            if result.netloc == 'github.com':
                skip_paths = [
                    '/login', '/signup', '/features', '/team', '/enterprise',
                    '/pricing', '/about', '/site', '/security', '/codespaces',
                    '/topics', '/collections', '/trending', '/copilot'
                ]
                
                for skip_path in skip_paths:
                    if result.path.startswith(skip_path):
                        logger.warning(f"Skipping generic GitHub page: {url}")
                        return False
            
            # Skip generic marketing/feature pages
            if 'features' in url or 'pricing' in url or 'about-us' in url or 'contact' in url:
                if not ('vitalik' in url.lower() or 'buterin' in url.lower()):
                    logger.warning(f"Skipping generic marketing page: {url}")
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error validating URL {url}: {str(e)}")
            return False
    
    def _extract_domain(self, text: str) -> Optional[str]:
        """Extract a domain name from text."""
        # Try to extract a domain from the text
        domain_match = re.search(r'((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9])', text.lower())
        
        if domain_match:
            return domain_match.group(1)
        
        return None
    
    def _should_check_wayback(self, url: str) -> bool:
        """Determine if we should check the Wayback Machine for a URL."""
        # Skip URLs that are already Wayback Machine URLs
        if 'web.archive.org' in url:
            return False
            
        # Always check wayback for domains in our priority list
        domain = urlparse(url).netloc
        
        if domain in self.priority_domains:
            return True
        
        # Check wayback for high-priority content-rich domains
        high_value_domains = [
            'vitalik.ca', 
            'bitcointalk.org',
            'blog.ethereum.org',
            'ethereum.foundation'
        ]
        
        for high_value in high_value_domains:
            if high_value in domain:
                return True
        
        # Selectively check wayback for other interesting domains
        # if the URL path suggests user-generated content
        interesting_domains = {
            'github.com': ['/vbuterin', '/ethereum', '/ethereum-foundation'],
            'medium.com': ['/vitalik', '/buterin', '/ethereum'],
            'twitter.com': ['/vitalikbuterin', '/VitalikButerin', '/ethereumproject'],
            'reddit.com': ['/user/vbuterin', '/r/ethereum'],
        }
        
        for interesting_domain, valuable_paths in interesting_domains.items():
            if interesting_domain in domain:
                path = urlparse(url).path
                # Only check wayback for specific valuable paths to avoid crawling generic pages
                for valuable_path in valuable_paths:
                    if valuable_path in path:
                        return True
                return False  # Skip other paths for these domains
        
        # For other domains, only check if they directly reference Vitalik or Ethereum
        if ('vitalik' in url.lower() or 'buterin' in url.lower()) and 'ethereum' in url.lower():
            return True
        
        # By default, don't check wayback to avoid too many requests
        return False
    
    def _get_timestamp(self) -> str:
        """Get the current timestamp as a string."""
        return datetime.datetime.now().isoformat()
    
    def _log_investigation_results(self, target: Dict[str, Any], discoveries: List[Dict[str, Any]], 
                                  new_targets: List[Dict[str, Any]]):
        """Log the results of an investigation."""
        log_entry = {
            'event': 'investigation',
            'timestamp': self._get_timestamp(),
            'iteration': self.current_iteration,
            'target': target,
            'discoveries': [
                {
                    'id': d.get('id'),
                    'type': d.get('type'),
                    'summary': d.get('summary'),
                    'source_url': d.get('source_url')
                } for d in discoveries
            ],
            'new_targets': [
                {
                    'type': t.get('type'),
                    'url': t.get('url') if t.get('type') in ['website', 'wayback', 'github'] else None,
                    'query': t.get('query') if t.get('type') == 'search' else None,
                    'rationale': t.get('rationale')
                } for t in new_targets
            ]
        }
        
        self._log_to_research_log(log_entry)
    
    def _log_to_research_log(self, entry: Dict[str, Any]):
        """Log an entry to the research log file."""
        try:
            with open(self.research_log_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Error writing to research log: {str(e)}")
    
    def _save_state(self):
        """Save the current state of the investigation."""
        state = {
            'objective': self.objective,
            'entity': self.entity,
            'current_iteration': self.current_iteration,
            'idle_iterations': self.idle_iterations,
            'start_time': self.start_time,
            'discoveries': self.discoveries,
            'entity_aliases': list(self.entity_aliases),
            'priority_domains': list(self.priority_domains),
            'research_queue': self.research_queue,
            'investigated_urls': list(self.investigated_urls),
            'timestamp': self._get_timestamp()
        }
        
        try:
            state_path = os.path.join(self.results_dir, f'investigation_state_{int(time.time())}.json')
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Also save discoveries separately
            discoveries_path = os.path.join(self.results_dir, 'discoveries.json')
            with open(discoveries_path, 'w') as f:
                json.dump(self.discoveries, f, indent=2)
                
            logger.info(f"Saved investigation state to {state_path}")
        except Exception as e:
            logger.error(f"Error saving investigation state: {str(e)}")
    
    def _generate_investigation_report(self):
        """Generate a final report of the investigation."""
        report = {
            'objective': self.objective,
            'entity': self.entity,
            'iterations': self.current_iteration,
            'total_discoveries': len(self.discoveries),
            'entity_aliases': list(self.entity_aliases),
            'start_time': datetime.datetime.fromtimestamp(self.start_time).isoformat(),
            'end_time': self._get_timestamp(),
            'runtime_seconds': time.time() - self.start_time,
            'discoveries_by_type': {},
            'top_discoveries': [],
            'summary': ""
        }
        
        # Count discoveries by type
        for discovery in self.discoveries:
            discovery_type = discovery.get('type', 'unknown')
            if discovery_type not in report['discoveries_by_type']:
                report['discoveries_by_type'][discovery_type] = 0
            report['discoveries_by_type'][discovery_type] += 1
        
        # Get top discoveries (highest scoring)
        sorted_discoveries = sorted(self.discoveries, key=lambda x: x.get('score', 0), reverse=True)
        report['top_discoveries'] = [
            {
                'type': d.get('type'),
                'summary': d.get('summary'),
                'source_url': d.get('source_url'),
                'score': d.get('score', 0)
            } for d in sorted_discoveries[:10]  # Top 10 discoveries
        ]
        
        # Generate an investigation summary using the LLM
        report['summary'] = self._generate_investigation_summary()
        
        # Save the report
        try:
            report_path = os.path.join(self.results_dir, f'investigation_report_{int(time.time())}.json')
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"Saved investigation report to {report_path}")
        except Exception as e:
            logger.error(f"Error saving investigation report: {str(e)}")
    
    def _generate_investigation_summary(self) -> str:
        """Generate a summary of the investigation using the LLM."""
        # Prepare context with top discoveries
        sorted_discoveries = sorted(self.discoveries, key=lambda x: x.get('score', 0), reverse=True)
        top_discoveries = sorted_discoveries[:20]  # Use top 20 for the summary
        
        context = self._prepare_llm_context(top_discoveries)
        
        # Build the prompt
        prompt = f"""
You are an expert digital detective who has completed an investigation on: "{self.objective}"

Here are the most significant findings from the investigation:
{context}

Please provide a detailed summary of the investigation results, including:
1. A high-level overview of what was discovered
2. The most important findings and their significance
3. Connections between different discoveries
4. Conclusions that can be drawn from the evidence

Write in a professional, analytical tone appropriate for an investigation report.
"""
        
        # Call the LLM
        try:
            summary = self.llm._call_claude(prompt)
            return summary
        except Exception as e:
            logger.error(f"Error generating investigation summary: {str(e)}")
            return "Failed to generate investigation summary."


def main():
    """Main function to run the detective agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the Detective Agent")
    parser.add_argument("--objective", type=str, default="Find name artifacts around Vitalik Buterin",
                        help="The research objective")
    parser.add_argument("--entity", type=str, default="Vitalik Buterin",
                        help="The primary entity to investigate")
    parser.add_argument("--max-iterations", type=int, default=50,
                        help="Maximum number of investigation iterations")
    parser.add_argument("--max-time-hours", type=float, default=24.0,
                        help="Maximum runtime in hours")
    parser.add_argument("--max-idle-iterations", type=int, default=5,
                        help="Maximum number of iterations without new discoveries")
    
    args = parser.parse_args()
    
    # Create and run the detective agent
    detective = DetectiveAgent(
        objective=args.objective,
        entity=args.entity,
        max_iterations=args.max_iterations,
        max_time_hours=args.max_time_hours,
        max_idle_iterations=args.max_idle_iterations
    )
    
    discoveries = detective.start_investigation()
    
    logger.info(f"Investigation complete. Found {len(discoveries)} discoveries.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())