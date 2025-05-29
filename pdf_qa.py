import os
import re
import requests
import numpy as np
import faiss
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from pdfminer.high_level import extract_text  # Lightweight PDF extraction
import logging

# Suppress PDFMiner warnings
logging.getLogger('pdfminer').setLevel(logging.ERROR)

# Load environment
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
QUOTA_USED = 0
MAX_QUOTA = 500  # Free tier daily limit

# Initialize embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')
vector_index = None
chunks = []

def extract_text_chunks(pdf_path: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """Extract text and split into semantic chunks"""
    try:
        text = extract_text(pdf_path)
    except Exception as e:
        print(f"PDF extraction error: {str(e)}")
        return []
    
    # Clean text
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', ' ', text)
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Create chunks with overlap
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        words = sentence.split()
        word_count = len(words)
        
        if current_length + word_count > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            # Keep overlap
            current_chunk = current_chunk[-overlap//10:] if overlap else []
            current_length = sum(len(s.split()) for s in current_chunk)
        
        current_chunk.append(sentence)
        current_length += word_count
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def build_vector_index(text_chunks: list):
    """Create FAISS index for semantic search"""
    global vector_index, chunks
    chunks = text_chunks
    
    if not chunks:
        print("No chunks to index")
        return False
    
    try:
        # Generate embeddings
        embeddings = model.encode(chunks, convert_to_numpy=True)
        embeddings = embeddings.astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create index
        vector_index = faiss.IndexFlatIP(embeddings.shape[1])
        vector_index.add(embeddings)
        return True
    except Exception as e:
        print(f"Index build error: {str(e)}")
        return False

def retrieve_relevant_chunks(question: str, k: int = 1) -> str:
    """Get most relevant context using semantic search"""
    if not vector_index:
        return ""
    
    try:
        # Embed question
        query_embed = model.encode([question], convert_to_numpy=True)
        query_embed = query_embed.astype('float32')
        faiss.normalize_L2(query_embed)
        
        # Search index
        distances, indices = vector_index.search(query_embed, k)
        
        # Return best context
        return "\n".join([chunks[i] for i in indices[0] if i < len(chunks)])
    except:
        return ""

def ask_gemini(question: str, context: str = ""):
    """Call Gemini API with quota tracking"""
    global QUOTA_USED
    
    if QUOTA_USED >= MAX_QUOTA:
        return {"error": "Daily quota exhausted"}
    
    # Use the latest model names
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    
    # Build efficient prompt
    prompt = f"Based ONLY on this context:\n{context[:1500]}\n\n" if context else ""
    prompt += f"Answer this: {question}"
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "maxOutputTokens": 500,
            "temperature": 0.3
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        QUOTA_USED += 1
        return response.json()
    except Exception as e:
        return {"error": f"API request failed: {str(e)}"}

def get_quota_status():
    """Return current quota usage"""
    return f"Quota: {QUOTA_USED}/{MAX_QUOTA} used"

def format_response(response: dict) -> str:
    """Extract answer from Gemini response"""
    if 'error' in response:
        return f"Error: {response['error']}"
    
    try:
        candidates = response.get('candidates', [])
        if not candidates:
            return "No response from Gemini"
            
        parts = candidates[0].get('content', {}).get('parts', [])
        if not parts:
            return "No answer content found"
            
        return parts[0].get('text', "Empty response")
    except:
        return "Could not parse response"

if __name__ == "__main__":
    # Load PDF
    pdf_path = input("Enter PDF path: ").strip()
    
    print("Processing PDF...")
    chunks = extract_text_chunks(pdf_path)
    if not chunks:
        print("Failed to extract text from PDF. Exiting.")
        exit()
        
    if build_vector_index(chunks):
        print(f"PDF processed. {len(chunks)} chunks indexed.")
    else:
        print("Failed to build index. Using simple text matching.")
    
    print("\nAsk questions about the PDF (type 'quit' to exit)")
    
    while True:
        question = input("\nYour question: ").strip()
        if question.lower() in ['quit', 'exit']:
            break
            
        # Get most relevant context
        context = retrieve_relevant_chunks(question)
        print(f"Using {len(context)} characters of context")
        
        # Call Gemini
        response = ask_gemini(question, context)
        
        # Handle response
        answer = format_response(response)
        print(f"\nAnswer: {answer}")
        
        # Show quota status
        print(f"\n{get_quota_status()}")