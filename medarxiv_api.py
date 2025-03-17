import requests
from datetime import datetime
import re
from typing import Union, List, Dict, Any, Optional

def fetch_medarxiv_papers(topics: Union[str, List[str]], start_date: str, end_date: str, max_results: int = 100, server: str = "medrxiv") -> List[Dict[str, Any]]:
    """
    Fetch medRxiv papers on specified topics within a given timeframe.
    
    Args:
        topics (Union[str, List[str]]): List of medRxiv categories or search terms
        start_date (str): Start date in format 'YYYY-MM-DD'
        end_date (str): End date in format 'YYYY-MM-DD'
        max_results (int): Maximum number of results to return
        server (str): Server to query ('medrxiv' or 'biorxiv')
    
    Returns:
        list: List of dictionaries containing paper details (title, abstract, link)
    """
    # Convert date strings to datetime objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Format dates for API (YYYY-MM-DD)
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
    
    # Construct the date interval string (YYYY-MM-DD/YYYY-MM-DD)
    date_interval = f"{start_date_formatted}/{end_date_formatted}"
    
    # Results collection
    all_results = []
    cursor = 0
    
    # Paginate through results until we have enough or there are no more
    while len(all_results) < max_results:
        # Construct the API URL with the correct format
        api_url = f"https://api.medrxiv.org/details/{server}/{date_interval}/{cursor}/json"
        
        try:
            # Make the API request
            response = requests.get(api_url, params={"term": query})
            response.raise_for_status()  # Raise exception for HTTP errors
            
            data = response.json()
            
            # Check if we have results
            collection = data.get('collection', [])
            if not collection:
                break
            
            # Process the results
            for paper in collection:
                # Extract paper details
                paper_info = {
                    'title': paper.get('title', ''),
                    'abstract': paper.get('abstract', ''),
                    'link': paper.get('pdf_url', '') or f"https://www.{server}.org/content/{paper.get('doi')}.full.pdf",
                    'published': paper.get('date', ''),
                    'authors': [author.get('name', '') for author in paper.get('authors', [])],
                    'id': paper.get('doi', ''),
                    'categories': paper.get('category', [])
                }
                all_results.append(paper_info)
                
                # Stop if we've reached the maximum number of results
                if len(all_results) >= max_results:
                    break
            
            # Update cursor for next page (each page has 100 results)
            cursor += 100
            
            # If we got fewer than 100 results, there are no more pages
            if len(collection) < 100:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching papers from {server}: {e}")
            break
    
    return all_results[:max_results]


def fetch_paper_by_id(paper_id: str, server: str = "medrxiv") -> Optional[Dict[str, Any]]:
    """
    Fetch a single medRxiv paper by its ID (DOI).
    
    Args:
        paper_id (str): medRxiv paper DOI or ID
        server (str): Server to query ('medrxiv' or 'biorxiv')
    
    Returns:
        dict: Paper details or None if not found
    """
    # Clean up the ID if it contains the full URL or medrxiv prefix
    if '/' in paper_id:
        paper_id = paper_id.split('/')[-1]
    
    # Remove any medrxiv.org part
    if 'medrxiv.org' in paper_id.lower() or 'biorxiv.org' in paper_id.lower():
        match = re.search(r'10\.\d{4,}/\d{4}\.\d{2}\.\d{2}\.\d+', paper_id)
        if match:
            paper_id = match.group(0)
    
    # API endpoint for a specific paper using the correct format
    api_url = f"https://api.medrxiv.org/details/{server}/{paper_id}/na/json"
    
    try:
        # Make the API request
        response = requests.get(api_url)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        
        # Check if we have results
        collection = data.get('collection', [])
        if not collection:
            return None
        
        paper = collection[0]
        
        return {
            'title': paper.get('title', ''),
            'abstract': paper.get('abstract', ''),
            'link': paper.get('pdf_url', '') or f"https://www.{server}.org/content/{paper.get('doi')}.full.pdf",
            'published': paper.get('date', ''),
            'authors': [author.get('name', '') for author in paper.get('authors', [])],
            'id': paper.get('doi', ''),
            'categories': paper.get('category', [])
        }
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching paper from {server}: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    papers = fetch_medarxiv_papers("COVID-19", '2023-01-01', '2023-01-31', max_results=5)
    print(f"Found {len(papers)} papers")
    
    # Example of fetching a specific paper by DOI
    if papers:
        paper_id = papers[0]['id']
        paper = fetch_paper_by_id(paper_id)
        if paper:
            print(f"Retrieved paper: {paper['title']}")
