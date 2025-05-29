# main.py
import assistant_functions as af
import pdf_qa
import web_qa
import hybrid_qa 
import os
import re

def handle_web_search_flow():
    """Handles the web search functionality"""
    print("\nWeb Search Mode Activated")
    print("Ask any question to search the web and get a summarized answer")
    print("Type 'back' to return to the main menu\n")
    
    while True:
        query = input("\nWeb Search Query: ").strip()
        if not query:
            continue
            
        if query.lower() in ['back', 'exit', 'quit']:
            print("Returning to main menu...\n")
            break
            
        # Perform web search and get summary
        result = web_qa.web_search_and_summarize(query)
        print(f"\n Summary:\n{result}\n")

# Global state for PDF loading
pdf_loaded = False

def handle_booking_flow():
    """Handles the appointment/call booking flow"""
    chatbot = af.Chatbot()
    print(chatbot.start_conversation())
    print("Type 'exit' at any time to return to the main menu.\n")
    
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ['exit', 'quit']:
            print("Returning to main menu...\n")
            break
            
        response, done = chatbot.handle_response(user_input)
        print("\nAssistant:", response)
        
        if done:
            break

# Global state for PDF loading
pdf_loaded = False
def handle_pdf_flow():
    """Handles the PDF Q&A functionality with hybrid capabilities"""
    global pdf_loaded
    
    # Load PDF if not already loaded
    if pdf_loaded == False:
        pdf_path = input("\nPlease provide the path to the PDF file: ").strip()
        if not os.path.exists(pdf_path):
            print("Error: File not found. Returning to main menu.")
            return
            
        print("Processing PDF...")
        chunks = pdf_qa.extract_text_chunks(pdf_path)
        if not chunks:
            print("Failed to extract text from PDF. Returning to main menu.")
            return
            
        if pdf_qa.build_vector_index(chunks):
            pdf_loaded = True
            print(f"PDF processed. {len(chunks)} chunks indexed.")
        else:
            print("Failed to build index. Using simple text matching.")
    
    # Q&A loop
    print("\nAsk questions about the PDF (type 'back' to return to main menu)")
    print("I'll automatically supplement missing info with web searches!")
    while True:
        question = input("\nPDF Question: ").strip()
        if question.lower() in ['back', 'exit', 'quit']:
            print("Returning to main menu...\n")
            break
            
        # Use hybrid QA system
        answer = hybrid_qa.hybrid_qa(question)
        print(f"\nAnswer: {answer}")
        print(hybrid_qa.get_quota_status())
        
def main():
    """Main routing function"""
    print("\n" + "=" * 60)
    print("🤖 Enhanced Assistant System")
    print("You can request assistance with:")
    print("  - Appointments (say 'appointment' or 'book')")
    print("  - Call requests (say 'call' or 'phone')")
    print("  - PDF documents (say 'pdf' or 'document')")
    print("  - Web search (say 'web' or 'search')")  
    print("Type 'exit' to quit at any time")
    print("=" * 60)
    
    while True:
        user_input = input("\nHow can I help you? ").strip().lower()
        
        if not user_input:
            continue
            
        if user_input in ['exit', 'quit']:
            print("\nGoodbye! Have a great day!")
            break
            
        # Route to appropriate functionality
        if 'appointment' in user_input or 'book' in user_input:
            print("\nStarting appointment booking system...")
            handle_booking_flow()
            
        elif 'call' in user_input or 'phone' in user_input:
            print("\nStarting call request system...")
            handle_booking_flow()
            
        elif 'pdf' in user_input or 'document' in user_input:
            print("\nStarting PDF assistance module...")
            handle_pdf_flow()
            
        elif 'web' in user_input or 'search' in user_input: 
            print("\nStarting web search module...")
            handle_web_search_flow()
            
        else:
            print("I'm not sure what you need. Please specify if you want help with:")
            print("- Appointment booking")
            print("- Call request")
            print("- PDF document questions")
            print("- Web search")  

if __name__ == "__main__":
    main()