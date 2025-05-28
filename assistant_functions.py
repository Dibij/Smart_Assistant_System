import sqlite3
import re
import dateparser
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, Tuple

class EnhancedDateParser:
    """Handles natural language date parsing with improved relative date support"""
    
    def __init__(self):
        self.now = datetime.now()
        
    def parse_natural_date(self, date_str: str) -> Optional[datetime]:
        """Parse natural language dates with better relative date handling"""
        try:
            # First try standard dateparser
            parsed = dateparser.parse(
                date_str,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RELATIVE_BASE': self.now,
                    'TIMEZONE': 'UTC'
                }
            )
            
            if parsed:
                return parsed
                
            # Handle special cases like "next Tuesday"
            if date_str.lower().startswith('next '):
                day_name = date_str[5:].strip().lower()
                days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                if day_name in days:
                    target_day = days.index(day_name)
                    current_day = self.now.weekday()
                    days_ahead = (target_day - current_day + 7) % 7
                    if days_ahead == 0:  # Today is the same day
                        days_ahead = 7
                    return self.now + timedelta(days=days_ahead)
                    
            # Handle "in X days/weeks/months"
            if date_str.lower().startswith('in '):
                parts = date_str[3:].split()
                if len(parts) == 2:
                    try:
                        num = int(parts[0])
                        unit = parts[1].lower()
                        if unit.startswith('day'):
                            return self.now + timedelta(days=num)
                        elif unit.startswith('week'):
                            return self.now + timedelta(weeks=num)
                        elif unit.startswith('month'):
                            return self.now + relativedelta(months=+num)
                    except ValueError:
                        pass
                        
            return None
        except Exception:
            return None

class BookingSystem:
    """Handles call requests and appointment bookings with SQLite storage"""
    
    def __init__(self):
        self.db_conn = sqlite3.connect('bookings.db')
        self.date_parser = EnhancedDateParser()
        self.create_tables()
        
    def create_tables(self):
        """Create database tables if they don't exist"""
        c = self.db_conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS call_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    call_date TEXT NOT NULL,
                    timestamp TEXT NOT NULL)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    appointment_date TEXT NOT NULL,
                    timestamp TEXT NOT NULL)''')
        
        self.db_conn.commit()
        
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format (digits only with valid length)"""
        cleaned = re.sub(r'\D', '', phone)
        return 7 <= len(cleaned) <= 15
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def parse_date(self, date_str: str) -> Optional[str]:
        """Parse natural language date to YYYY-MM-DD format"""
        parsed = self.date_parser.parse_natural_date(date_str)
        return parsed.strftime('%Y-%m-%d') if parsed else None
    
    def validate_date(self, date_str: str) -> Tuple[bool, str]:
        """Validate that date can be parsed and is in the future"""
        parsed_date = self.parse_date(date_str)
        if not parsed_date:
            return False, "I couldn't understand that date. Please try something like 'tomorrow' or 'next Friday'."
        
        try:
            date_obj = datetime.strptime(parsed_date, '%Y-%m-%d')
            if date_obj.date() < datetime.now().date():
                return False, "Date must be in the future. Please try again."
            return True, parsed_date
        except:
            return False, "Invalid date format. Please try again."
    
    def save_booking(self, intent: str, name: str, phone: str, email: str, date_str: str):
        """Save booking to the appropriate table"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        table = "call_requests" if intent == "call" else "appointments"
        date_column = "call_date" if intent == "call" else "appointment_date"
        
        c = self.db_conn.cursor()
        c.execute(f'''INSERT INTO {table} 
                    (name, phone, email, {date_column}, timestamp) 
                    VALUES (?, ?, ?, ?, ?)''', 
                (name, phone, email, date_str, timestamp))
        self.db_conn.commit()
        
        return table, date_str

class Chatbot:
    """Conversational chatbot for handling booking requests"""
    
    def __init__(self):
        self.booking_system = BookingSystem()
        self.current_state = "START"
        self.current_intent = None
        self.user_data = {}
        
    def start_conversation(self):
        """Initialize the conversation"""
        return ("Hello! I'm your booking assistant. Do you want us to call you "
                "or would you like to book an appointment?")
    
    def handle_response(self, user_input: str) -> Tuple[str, bool]:
        """Process user input and return bot response + completion flag"""
        user_input = user_input.strip().lower()
        completion_flag = False
        
        # State machine for conversation flow
        if self.current_state == "START":
            if "call" in user_input or "call me" in user_input:
                self.current_intent = "call"
                self.current_state = "GET_NAME"
                return "Great! Let me get some details for your call request. What's your full name?", False
            elif "book" in user_input or "appointment" in user_input:
                self.current_intent = "appointment"
                self.current_state = "GET_NAME"
                return "Great! Let's schedule your appointment. What's your full name?", False
            else:
                return ("I'm not sure what you'd like to do. Please specify if you want us to "
                        "'call you' or if you want to 'book an appointment'.", False)
        
        elif self.current_state == "GET_NAME":
            self.user_data["name"] = user_input
            self.current_state = "GET_PHONE"
            return "What's your phone number?", False
        
        elif self.current_state == "GET_PHONE":
            if self.booking_system.validate_phone(user_input):
                self.user_data["phone"] = user_input
                self.current_state = "GET_EMAIL"
                return "What's your email address?", False
            else:
                return ("Invalid phone number. Please enter a valid phone number (7-15 digits).", False)
        
        elif self.current_state == "GET_EMAIL":
            if self.booking_system.validate_email(user_input):
                self.user_data["email"] = user_input
                self.current_state = "GET_DATE"
                intent_str = "call you" if self.current_intent == "call" else "schedule your appointment"
                return f"When would you like us to {intent_str}? (e.g., 'tomorrow', 'next Friday')", False
            else:
                return ("Invalid email format. Please enter a valid email address.", False)
        
        elif self.current_state == "GET_DATE":
            valid_date, date_result = self.booking_system.validate_date(user_input)
            if valid_date:
                self.user_data["date"] = date_result
                self.current_state = "CONFIRM"
                intent_str = "call" if self.current_intent == "call" else "appointment"
                date_str = datetime.strptime(date_result, '%Y-%m-%d').strftime('%B %d, %Y')
                return (f"Just to confirm:\n"
                        f"Name: {self.user_data['name']}\n"
                        f"Phone: {self.user_data['phone']}\n"
                        f"Email: {self.user_data['email']}\n"
                        f"Date: {date_str}\n\n"
                        f"Should I book this {intent_str}? (yes/no)", False)
            else:
                return (date_result, False)  # date_result contains error message
        
        # ... existing code ...

        elif self.current_state == "CONFIRM":
            if user_input in ["yes", "y", "confirm"]:
                # Save booking to database
                table, date_str = self.booking_system.save_booking(
                    self.current_intent,
                    self.user_data["name"],
                    self.user_data["phone"],
                    self.user_data["email"],
                    self.user_data["date"]
                )
                
                # Format confirmation message BEFORE resetting data
                intent_str = "call" if self.current_intent == "call" else "appointment"
                date_formatted = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
                phone = self.user_data["phone"]
                email = self.user_data["email"]
                
                # Reset for next conversation
                self.current_state = "START"
                self.current_intent = None
                self.user_data = {}
                completion_flag = True
                
                return (f" All set! Your {intent_str} is confirmed for {date_formatted}.\n"
                        f"We'll contact you at {phone} or {email} "
                        "if needed. Thank you!", completion_flag)
            
            elif user_input in ["no", "n"]:
                self.current_state = "GET_DATE"
                intent_str = "call" if self.current_intent == "call" else "appointment"
                return f"Okay, let's try again. When would you like to {intent_str}?", False
            
            else:
                return "Please answer with 'yes' or 'no'.", False        
        return "I'm not sure how to handle that. Could you rephrase?", False

def run_chatbot_cli():
    """Run the chatbot in CLI mode"""
    chatbot = Chatbot()
    print(chatbot.start_conversation())
    print("Type 'exit' at any time to quit.\n")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            print("Goodbye!")
            break
            
        response, done = chatbot.handle_response(user_input)
        print("\nAssistant:", response)
        
        if done:
            print("\n" + "="*50)
            print(chatbot.start_conversation())

if __name__ == "__main__":
    run_chatbot_cli()