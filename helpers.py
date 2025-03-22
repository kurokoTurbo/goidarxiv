def escape_html(text):
    """Escape HTML special characters
    
    Args:
        text: Text to escape
    """
    if not text:
        return ""

    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def paper_id_without_dot(paper_id: str) -> str:
    if "." in paper_id:
        return paper_id.replace(".", "")
    else:
        return paper_id


def paper_id_with_dot(paper_id: str) -> str:
    if "." in paper_id:
        return paper_id
    else:
        return paper_id[: 4] + "." + paper_id[4:]

def chunk_html_message(message, max_length=4000):
    """Split a long HTML message into chunks without breaking HTML tags.
    
    Args:
        message (str): The HTML message to split
        max_length (int): Maximum length of each chunk
        
    Returns:
        list: List of message chunks
    """
    if len(message) <= max_length:
        return [message]

    chunks = []
    current_chunk = ""

    # Simple approach: split on double newlines to keep paragraphs together
    paragraphs = message.split("\n\n")

    for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit, start a new chunk
        if len(current_chunk) + len(paragraph) + 2 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                # If a single paragraph is too long, we need to split it
                if len(paragraph) > max_length:
                    # Try to split at a safe position like a space
                    safe_length = max_length
                    while safe_length > 0 and paragraph[safe_length - 1] != ' ':
                        safe_length -= 1

                    if safe_length > 0:
                        chunks.append(paragraph[:safe_length])
                        current_chunk = paragraph[safe_length:]
                    else:
                        # Worst case: just split at max_length
                        chunks.append(paragraph[:max_length])
                        current_chunk = paragraph[max_length:]
                else:
                    current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def format_papers(papers):
    # Format and send results for each topic
    message = f"📚 <b>Papers Today</b> 📚\n\n"
    for i in range(len(papers)):
        paper = papers[i]
        title = escape_html(paper.title)
        authors = ', '.join(author.name for author in paper.authors[:3])
        if len(paper.authors) > 3:
            authors += ' et al.'
        authors = escape_html(authors)

        message += f"{i}. <b>{title}</b>\n"
        message += f"   Authors: {authors}\n"

        paper_id = paper.entry_id.split('/')[-1]  # Extract just the ID part
        message += f"   /abstract{paper_id_without_dot(paper_id)}\n\n"
    return message