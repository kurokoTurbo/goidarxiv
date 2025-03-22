from itertools import permutations, combinations
import arxiv
from datetime import datetime

def fetch_arxiv_papers(topics, start_date: datetime, end_date: datetime, max_results=100) -> list[arxiv.Result]:
    """
    Fetch arXiv papers on specified topics within a given timeframe.
    
    Args:
        topics (Union(str, list): List of arXiv categories or search terms
        start_date (datetime): Start date
        end_date (datetime): End date
        max_results (int): Maximum number of results to return
    
    Returns:
        list: List of dictionaries containing paper details (title, abstract, link)
    """
    
    # Build the query string from topics
    if isinstance(topics, list):
        query = " OR ".join([f"cat:{topic}" if "." in topic else topic for topic in topics])
    else:
        # If topics is a string and contains commas, treat it as a list of topics
        if ',' in topics:
            topic_list = [t.strip() for t in topics.split(',')]
            query = " OR ".join([f"cat:{topic}" if "." in topic else topic for topic in topic_list])
        else:
            query = f"cat:{topics}" if "." in topics else topics
    
    # Set up the search client
    client = arxiv.Client()
    
    # Create a search query
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    # Execute the search and filter by date
    results = []
    for paper in client.results(search):
        published_date = paper.published
        if start_date <= published_date.replace(tzinfo=None) <= end_date:
            results.append(paper)
    
    return results

def fetch_paper_by_id(paper_id):
    """
    Fetch a single arXiv paper by its ID.
    
    Args:
        paper_id (str): arXiv paper ID (e.g., '2101.12345')
    
    Returns:
        dict: Paper details or None if not found
    """
    # Clean up the ID if it contains the full URL or arxiv prefix
    if '/' in paper_id:
        paper_id = paper_id.split('/')[-1]
    if 'arxiv.org' in paper_id.lower():
        paper_id = paper_id.split('arxiv.org/')[-1]
    if 'abs' in paper_id:
        paper_id = paper_id.split('abs/')[-1]
    if '.pdf' in paper_id:
        paper_id = paper_id.replace('.pdf', '')
    
    # Create search query for the specific paper
    client = arxiv.Client()
    search = arxiv.Search(id_list=[paper_id])
    
    # Get the paper
    results = list(client.results(search))
    
    if not results:
        return None
    
    paper = results[0]
    return {
        'title': paper.title,
        'abstract': paper.summary,
        'link': paper.pdf_url,
        'published': paper.published.strftime('%Y-%m-%d'),
        'authors': [author.name for author in paper.authors],
        'id': paper.entry_id,
        'categories': paper.categories
    }


if __name__ == "__main__":    
    fetch_arxiv_papers("cs.CV", 
                       datetime.strptime('2025-01-01', '%Y-%m-%d'), 
                       datetime.strptime('2025-01-31', '%Y-%m-%d'), 
                       max_results=5)
