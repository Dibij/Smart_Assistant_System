# hybrid_qa.py (completely updated)
import pdf_qa
import web_qa
import re
import nltk
from nltk import pos_tag, word_tokenize
from nltk.chunk import ne_chunk

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('maxent_ne_chunker')
    nltk.download('words')

def extract_entities(question: str) -> list:
    """Extract key entities using NLP"""
    tokens = word_tokenize(question)
    tagged = pos_tag(tokens)
    entities = []
    
    # Extract noun phrases
    for chunk in ne_chunk(tagged):
        if isinstance(chunk, nltk.tree.Tree):
            entity = " ".join([word for word, tag in chunk.leaves()])
            entities.append(entity)
    
    # Add any capitalized multi-word phrases
    for match in re.finditer(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', question):
        entities.append(match.group(0))
    
    # Add any terms in quotes
    for match in re.finditer(r'"([^"]+)"', question):
        entities.append(match.group(1))
    
    # Add any terms after 'called', 'named', or 'termed'
    for match in re.finditer(r'(?:called|named|termed)\s+([^\s,.]+)', question, re.IGNORECASE):
        entities.append(match.group(1))
    
    return list(set(entities))

def hybrid_qa(question: str) -> str:
    """Answer questions by combining PDF content with web search"""
    # First try to answer from PDF only
    pdf_context = pdf_qa.retrieve_relevant_chunks(question)
    pdf_response = pdf_qa.ask_gemini(
        f"Answer this based ONLY on the context: {question}",
        pdf_context
    )
    pdf_answer = pdf_qa.format_response(pdf_response)
    
    # Check if answer is complete
    if "not in the text" not in pdf_answer.lower() and "not mentioned" not in pdf_answer.lower():
        return pdf_answer
    
    # Extract key entities
    entities = extract_entities(question)
    if not entities:
        print("🔍 Answer not found in PDF. Searching web...")
        return web_qa.web_search_and_summarize(question)
    
    # Prepare hybrid context
    hybrid_context = f"PDF CONTEXT:\n{pdf_context}\n\n"
    missing_in_pdf = []
    
    # Check PDF coverage for each entity
    for entity in entities:
        entity_context = pdf_qa.retrieve_relevant_chunks(entity, k=1)
        if not entity_context or "not found" in entity_context.lower():
            missing_in_pdf.append(entity)
            print(f"🔍 Entity '{entity}' not in PDF. Searching web...")
            web_info = web_qa.web_search_and_summarize(entity, num_results=1)
            hybrid_context += f"WEB INFO ABOUT '{entity}':\n{web_info}\n\n"
        else:
            hybrid_context += f"PDF INFO ABOUT '{entity}':\n{entity_context}\n\n"
    
    # Ask for comprehensive answer
    prompt = (
        f"Comprehensively answer this question: {question}\n\n"
        f"Use all available information below. "
        f"Highlight key points and differences where applicable. "
        f"Clearly indicate which information comes from the PDF and which comes from web sources.\n\n"
        f"{hybrid_context}"
    )
    
    hybrid_response = pdf_qa.ask_gemini(prompt)
    return pdf_qa.format_response(hybrid_response)

def get_quota_status():
    """Get combined quota status"""
    pdf_quota = f"PDF Quota: {pdf_qa.QUOTA_USED}/{pdf_qa.MAX_QUOTA}"
    web_quota = f"Web Quota: {web_qa.WEB_QUOTA_USED}/{web_qa.MAX_WEB_QUOTA}"
    return f"{pdf_quota} | {web_quota}"