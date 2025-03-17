import requests
from datetime import datetime
import re
from typing import Union, List, Dict, Any, Optional

def fetch_medarxiv_papers(topics: Union[str, List[str]], start_date: str, end_date: str, max_results: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch medRxiv papers on specified topics within a given timeframe.
    
    Args:
        topics (Union[str, List[str]]): List of medRxiv categories or search terms
        start_date (str): Start date in format 'YYYY-MM-DD'
        end_date (str): End date in format 'YYYY-MM-DD'
        max_results (int): Maximum number of results to return
    
    Returns:
        list: List of dictionaries containing paper details (title, abstract, link)
    """
    # Convert date strings to datetime objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Format dates for API
    start_date_formatted = start_date_obj.strftime('%Y-%m-%d')
    end_date_formatted = end_date_obj.strftime('%Y-%m-%d')
    
    # Build the query string from topics
    if isinstance(topics, list):
        query = " OR ".join(topics)
    else:
        # If topics is a string and contains commas, treat it as a list of topics
        if ',' in topics:
            topic_list = [t.strip() for t in topics.split(',')]
            query = " OR ".join(topic_list)
        else:
            query = topics
    
    # medRxiv API endpoint
    api_url = "https://api.medrxiv.org/papers"
    
    # Parameters for the API request
    params = {
        "q": query,
        "from_date": start_date_formatted,
        "to_date": end_date_formatted,
        "limit": max_results,
        "format": "json"
    }
    
    try:
        # Make the API request
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        
        # Process the results
        results = []
        for paper in data.get('results', []):
            # Extract paper details
            paper_info = {
                'title': paper.get('title', ''),
                'abstract': paper.get('abstract', ''),
                'link': paper.get('pdf_url') or f"https://www.medrxiv.org/content/{paper.get('doi')}.full.pdf",
                'published': paper.get('date', ''),
                'authors': [author.get('name', '') for author in paper.get('authors', [])],
                'id': paper.get('doi', ''),
                'categories': paper.get('category', [])
            }
            results.append(paper_info)
        
        return results
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching papers from medRxiv: {e}")
        return []


def fetch_paper_by_id(paper_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single medRxiv paper by its ID (DOI).
    
    Args:
        paper_id (str): medRxiv paper DOI or ID
    
    Returns:
        dict: Paper details or None if not found
    """
    # Clean up the ID if it contains the full URL or medrxiv prefix
    if '/' in paper_id:
        paper_id = paper_id.split('/')[-1]
    
    # Remove any medrxiv.org part
    if 'medrxiv.org' in paper_id.lower():
        match = re.search(r'10\.\d{4,}/\d{4}\.\d{2}\.\d{2}\.\d+', paper_id)
        if match:
            paper_id = match.group(0)
    
    # API endpoint for a specific paper
    api_url = f"https://api.medrxiv.org/papers/{paper_id}"
    
    try:
        # Make the API request
        response = requests.get(api_url, params={"format": "json"})
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        
        if not data.get('results'):
            return None
        
        paper = data['results'][0]
        
        return {
            'title': paper.get('title', ''),
            'abstract': paper.get('abstract', ''),
            'link': paper.get('pdf_url') or f"https://www.medrxiv.org/content/{paper.get('doi')}.full.pdf",
            'published': paper.get('date', ''),
            'authors': [author.get('name', '') for author in paper.get('authors', [])],
            'id': paper.get('doi', ''),
            'categories': paper.get('category', [])
        }
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching paper from medRxiv: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    fetch_medarxiv_papers("COVID-19", '2023-01-01', '2023-01-31', max_results=5)
