import logging
import os
from typing import Optional
from tavily import TavilyClient

logger = logging.getLogger(__name__)

class WebSearchAgent:
    """
    Specialist agent for web search using Tavily API
    """
    
    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()
        self.api_key = os.getenv('TAVILY_API_KEY')
        self.client = TavilyClient(api_key=self.api_key) if self.api_key else None
    
    async def search(self, query: str, max_results: int = 10) -> dict:
        """
        Execute a web search and return results with citations
        
        Returns:
        {
            'query': str,
            'results': [
                {
                    'title': str,
                    'url': str,
                    'content': str,
                    'source': str
                },
                ...
            ],
            'total_results': int,
            'search_time': float
        }
        """
        if not self.client:
            logger.error('Tavily API key not configured')
            return {
                'query': query,
                'results': [],
                'error': 'Tavily API key not configured'
            }
        
        try:
            logger.info(f'Searching web for: {query}')
            
            response = self.client.search(
                query=query,
                max_results=max_results,
                include_answer=True
            )
            
            # Parse Tavily response
            results = []
            if 'results' in response:
                for item in response['results']:
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'content': item.get('content', ''),
                        'source': item.get('source', '')
                    })
            
            output = {
                'query': query,
                'results': results,
                'total_results': len(results),
                'answer': response.get('answer', ''),
                'search_time': response.get('response_time', 0)
            }
            
            logger.info(f'Web search completed: {len(results)} results found')
            return output
        
        except Exception as e:
            logger.error(f'Web search failed: {str(e)}')
            return {
                'query': query,
                'results': [],
                'error': str(e)
            }

# Global web search agent instance
web_search_agent = WebSearchAgent()
