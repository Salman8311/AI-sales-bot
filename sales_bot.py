import os
from openai import OpenAI
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style

# Load environment variables
load_dotenv()

colorama.init(autoreset=True)

SYSTEM_PROMPT = """You are a highly persuasive Sales Conversational AI for Mierae Solar.
Your objective is to convert users into solar leads.
You MUST speak in Hindi, Telugu, or Odia depending on the user's language. Do NOT use English unless the user explicitly forces it. Keep sentences relatively short and natural.

CRITICAL RULES:
- You must ONLY ask ONE question at a time! 
- Do NOT output the entire flow or multiple steps at once. 
- Wait for the user to answer before moving to the next question or step.
- Be highly conversational and natural. Do not list out step numbers.

Conversation Flow (Progress through these one by one):
1. Greeting: Introduce yourself concisely. Ask if they want to reduce their electricity bill.
2. Qualification: Ask these sequentially, ONE BY ONE, waiting for their reply each time: 
   - What is your monthly electricity bill? 
   - Is it your own house? 
   - Is the roof free/available? 
   - Which city?
3. Value Pitch: Pitch the PM Surya Ghar Yojana (Up to 40% subsidy, ₹78,000 subsidy, 300 units free, 1 crore homes target, ~6.75% loan, 25 years free electricity, 3kW makes bill zero).
4. Objection Handling (if they have doubts): "Too costly" -> mention EMI option. "Not sure" -> Free site visit. "No time" -> We manage everything.
5. Closing: Ask to book a free site visit and ask for their Phone number and Name.

Once you have successfully collected Name, Phone, City, Electricity bill, and House type, and confirmed they are Interested (Yes/No), gracefully end the conversation and append the following exact JSON block at the very end of your final message:

LEAD_CAPTURE: {
  "Name": "[Extracted Name]",
  "Phone": "[Extracted Phone]",
  "City": "[Extracted City]",
  "Electricity bill": "[Extracted Bill]",
  "House type": "[Extracted House Type]",
  "Interested": "Yes/No"
}
"""

def setup_client():
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        print(Fore.CYAN + "[System] Using Groq API for ultra-fast inference.")
        return OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key
        ), "llama-3.1-8b-instant"  # Using Groq's super fast Llama 3.1
    else:
        print(Fore.CYAN + "[System] No GROQ_API_KEY found. Falling back to local Ollama API.")
        print(Fore.YELLOW + "Note: Make sure Ollama is installed and running (`ollama run llama3.1`).")
        return OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"  # arbitrary key
        ), "llama3.1"

def main():
    print(Fore.GREEN + Style.BRIGHT + "=============================================")
    print(Fore.GREEN + Style.BRIGHT + "   Mierae Solar - AI Sales Bot Initialized   ")
    print(Fore.GREEN + Style.BRIGHT + "=============================================\n")
    
    try:
        client, model = setup_client()
    except Exception as e:
        print(Fore.RED + f"Failed to setup API Client: {e}")
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    print(Fore.MAGENTA + "Tip: Provide a starting greeting exactly as you want, or just press enter to let the bot initiate.")
    print(Fore.BLUE + "Type 'quit' or 'exit' to stop.")
    
    # Let bot speak first
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
        )
        bot_reply = response.choices[0].message.content
        print(Fore.YELLOW + "\nBot: " + Fore.WHITE + bot_reply)
        messages.append({"role": "assistant", "content": bot_reply})
    except Exception as e:
        print(Fore.RED + f"Error occurred: {e}. If using Ollama, make sure it is running locally.")
        return

    while True:
        user_input = input(Fore.GREEN + "\nYou: " + Fore.WHITE)
        if user_input.lower() in ["quit", "exit"]:
            print(Fore.CYAN + "Goodbye!")
            break
            
        messages.append({"role": "user", "content": user_input})
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
            )
            bot_reply = response.choices[0].message.content
            print(Fore.YELLOW + "\nBot: " + Fore.WHITE + bot_reply)
            
            messages.append({"role": "assistant", "content": bot_reply})
            
            if "LEAD_CAPTURE:" in bot_reply:
                print(Fore.GREEN + "\n[System] Lead capture detected. Saving lead and ending chat.")
                break
                
        except Exception as e:
            print(Fore.RED + f"Error occurred: {e}")
            break

if __name__ == "__main__":
    main()
