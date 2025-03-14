import arxiv
from datetime import datetime

def fetch_arxiv_papers(topics, start_date, end_date, max_results=100):
    """
    Fetch arXiv papers on specified topics within a given timeframe.
    
    Args:
        topics (Union(str, list): List of arXiv categories or search terms
        start_date (str): Start date in format 'YYYY-MM-DD'
        end_date (str): End date in format 'YYYY-MM-DD'
        max_results (int): Maximum number of results to return
    
    Returns:
        list: List of dictionaries containing paper details (title, abstract, link)
    """
    # Convert date strings to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Build the query string from topics
    if isinstance(topics, list):
        query = " OR ".join([f"cat:{topic}" if "." in topic else topic for topic in topics])
    else:
        query = topics
    
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
            paper_info = {
                'title': paper.title,
                'abstract': paper.summary,
                'link': paper.pdf_url,
                'published': paper.published.strftime('%Y-%m-%d'),
                'authors': [author.name for author in paper.authors],
                'id': paper.entry_id
            }
            results.append(paper_info)
    
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
    fetch_arxiv_papers("cs.CV", '2025-01-01', '2025-01-31', max_results=5)
