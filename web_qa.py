import requests
from bs4 import BeautifulSoup
from pdf_qa import ask_gemini, format_response
import re
import time
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

# Track web-specific quota usage
WEB_QUOTA_USED = 0
MAX_WEB_QUOTA = 100  # Separate from PDF quota

def google_search(query: str, num_results: int = 3) -> list:
    """Perform a Google search using the Custom Search JSON API"""
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        print("Google API credentials missing. Please set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env")
        return []
    
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': GOOGLE_API_KEY,
        'cx': GOOGLE_CSE_ID,
        'q': query,
        'num': num_results
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get('items', []):
            results.append({
                'title': item.get('title'),
                'url': item.get('link'),
                'snippet': item.get('snippet')
            })
        return results
    
    except Exception as e:
        print(f"Google search API error: {str(e)}")
        return []

def clean_text(text: str) -> str:
    """Clean and normalize scraped text"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove JavaScript and CSS
    text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove special characters
    text = re.sub(r'[^\w\s.,;:!?\-()\[\]{}"\'\/]', '', text)
    return text.strip()

def scrape_website(url: str) -> str:
    """Scrape main content from a website with robust error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unnecessary elements
        for element in soup(['header', 'footer', 'nav', 'aside', 'script', 'style', 'noscript', 'svg']):
            element.decompose()
        
        # Extract main content using common patterns
        content_selectors = [
            'article',
            'main',
            '.content',
            '.article-body',
            '.post-content',
            '#content'
        ]
        
        for selector in content_selectors:
            article = soup.select_one(selector)
            if article:
                content = article.get_text()
                break
        else:
            # Fallback to body if no specific content found
            content = soup.find('body').get_text() if soup.find('body') else soup.get_text()
        
        return clean_text(content)[:15000]  # Limit to 15k characters
    
    except Exception as e:
        print(f"Scraping error for {url}: {str(e)}")
        return ""

def web_search_and_summarize(query: str, num_results: int = 3) -> str:
    """Search the web and summarize results using Gemini"""
    global WEB_QUOTA_USED
    
    if WEB_QUOTA_USED >= MAX_WEB_QUOTA:
        return "Web search quota exhausted for today"
    
    print(f" Searching the web for: {query}")
    search_results = google_search(query, num_results)
    
    if not search_results:
        return "No search results found. Try a different query."
    
    print(f" Found {len(search_results)} results. Processing content...")
    contents = []
    
    for i, result in enumerate(search_results):
        print(f" Scraping ({i+1}/{len(search_results)}): {result['title']}")
        
        # Try to scrape content, but use snippet if scraping fails
        content = scrape_website(result['url'])
        if not content:
            print("  Using snippet instead of full content")
            content = result.get('snippet', '') + " [Source: " + result['url'] + "]"
        
        if content:
            contents.append(f"# Source: {result['title']} ({result['url']})\n{content}\n")
        time.sleep(1)  # Be polite to servers
    
    if not contents:
        return "Could not retrieve content from any sources."
    
    context = "\n\n".join(contents)
    print(f"Context size: {len(context)} characters")
    
    # Ask Gemini to summarize
    prompt = (
        f"You are a research assistant. Summarize the key information from these sources "
        f"about '{query}'. Provide a comprehensive digest with key points, important dates, "
        f"and notable opinions. Cite your sources using the provided URLs.\n\n"
        f"{context}"
    )
    
    response = ask_gemini(prompt, max_context_length=30000)
    WEB_QUOTA_USED += 1
    return format_response(response)