# main.py
import assistant_functions as af
import pdf_qa
import os
import re

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

def handle_pdf_flow():
    """Handles the PDF Q&A functionality"""
    global pdf_loaded
    
    # Load PDF if not already loaded
    if not pdf_loaded:
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
    while True:
        question = input("\nPDF Question: ").strip()
        if question.lower() in ['back', 'exit', 'quit']:
            print("Returning to main menu...\n")
            break
            
        # Get relevant context and generate answer
        context = pdf_qa.retrieve_relevant_chunks(question)
        response = pdf_qa.ask_gemini(question, context)
        answer = pdf_qa.format_response(response)
        print(f"\nAnswer: {answer}")
        print(pdf_qa.get_quota_status())

# Global state for PDF loading
pdf_loaded = False

def main():
    """Main routing function"""
    print("\n" + "=" * 60)
    print("Welcome to the Assistant System!")
    print("You can request assistance with:")
    print("  - Appointments (say 'appointment' or 'book')")
    print("  - Call requests (say 'call' or 'phone')")
    print("  - PDF documents (say 'pdf' or 'document')")
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
            handle_booking_flow()  # Same flow as appointments
            
        elif 'pdf' in user_input or 'document' in user_input:
            print("\nStarting PDF assistance module...")
            handle_pdf_flow()
            
        else:
            print("I'm not sure what you need. Please specify if you want help with:")
            print("- Appointment booking")
            print("- Call request")
            print("- PDF document questions")

if __name__ == "__main__":
    main()