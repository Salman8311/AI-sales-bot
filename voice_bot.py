import os
import time
import ctypes
import speech_recognition as sr
from gtts import gTTS
from openai import OpenAI
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style

load_dotenv()
colorama.init(autoreset=True)

# Language configuration map
LANG_CONFIG = {
    "1": {"name": "Hindi", "stt_code": "hi-IN", "tts_code": "hi"},
    "2": {"name": "Telugu", "stt_code": "te-IN", "tts_code": "te"},
    "3": {"name": "Urdu", "stt_code": "ur-PK", "tts_code": "ur"},
}

# The system prompt placeholder for dynamic language
SYSTEM_PROMPT_TEMPLATE = """You are a highly persuasive Sales Conversational AI for Mierae Solar.
Your objective is to convert users into solar leads.
You MUST speak in {language}. Do NOT use English unless the user explicitly forces it. Keep sentences relatively short and natural.

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

LEAD_CAPTURE: {{
  "Name": "[Extracted Name]",
  "Phone": "[Extracted Phone]",
  "City": "[Extracted City]",
  "Electricity bill": "[Extracted Bill]",
  "House type": "[Extracted House Type]",
  "Interested": "Yes"
}}
"""

def setup_client():
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        print(Fore.CYAN + "[System] Using Groq API for ultra-fast inference.")
        return OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key
        ), "llama-3.1-8b-instant"
    else:
        print(Fore.CYAN + "[System] No GROQ_API_KEY found. Falling back to local Ollama API.")
        return OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        ), "llama3.1"

def speak(text, lang_code):
    """Convert text to speech and play it."""
    try:
        # Generate speech
        tts = gTTS(text=text, lang=lang_code, slow=False)
        filename = "response.mp3"
        tts.save(filename)
        
        # Play speech
        from playsound import playsound
        playsound(filename)
        
        # Clean up
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                pass # Can ignore if windows locks the file
    except Exception as e:
        print(Fore.RED + f"[TTS Error] {e}")

def listen(lang_code):
    """Listen to microphone natively on Windows using ctypes and convert to text."""
    filename = "temp_record.wav"
    winmm = ctypes.windll.winmm
    
    print(Fore.GREEN + f"\n[Listening...] Speak now!")
    
    # Use native Windows MCI to record audio (solves PyAudio C++ compile errors)
    winmm.mciSendStringW("open new type waveaudio alias recsound", None, 0, 0)
    winmm.mciSendStringW("record recsound", None, 0, 0)
    
    input(Fore.BLUE + "-- Press Enter when you finish speaking --")
    
    winmm.mciSendStringW(f"save recsound {filename}", None, 0, 0)
    winmm.mciSendStringW("close recsound", None, 0, 0)
    
    print(Fore.CYAN + "[System] Recognizing speech...")
    r = sr.Recognizer()
    try:
        with sr.AudioFile(filename) as source:
            audio = r.record(source)
        text = r.recognize_google(audio, language=lang_code)
        return text
    except sr.UnknownValueError:
        print(Fore.RED + "[System] Sorry, I couldn't understand that.")
        return ""
    except sr.RequestError as e:
        print(Fore.RED + f"[System] Could not request results from Google SR service; {e}")
        return ""
    except Exception as e:
        print(Fore.RED + f"[System] Microphone error: {e}")
        return ""
    finally:
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass

def main():
    print(Fore.GREEN + Style.BRIGHT + "=============================================")
    print(Fore.GREEN + Style.BRIGHT + "   Mierae Solar - Voice AI Sales Bot         ")
    print(Fore.GREEN + Style.BRIGHT + "=============================================\n")
    
    # 1. Select Language
    print(Fore.CYAN + "Please select the language for the bot:")
    print("1. Hindi")
    print("2. Telugu")
    print("3. Urdu")
    
    choice = input("Enter 1, 2, or 3: ").strip()
    config = LANG_CONFIG.get(choice)
    if not config:
        print(Fore.RED + "Invalid choice. Defaulting to Hindi.")
        config = LANG_CONFIG["1"]
        
    language_name = config["name"]
    stt_lang = config["stt_code"]
    tts_lang = config["tts_code"]
    
    print(Fore.YELLOW + f"[System] Selected Language: {language_name}")
    
    # Setup LLM Client
    try:
        client, model = setup_client()
    except Exception as e:
        print(Fore.RED + f"Failed to setup API Client: {e}")
        return

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language=language_name)
    messages = [{"role": "system", "content": system_prompt}]
    
    print(Fore.MAGENTA + "Tip: Say 'quit' or 'exit' (in English) into the microphone to terminate.")
    
    # Let bot initiate the conversation via LLM
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
        )
        bot_reply = response.choices[0].message.content
        print(Fore.YELLOW + f"\nBot [{language_name}]: {Fore.WHITE}{bot_reply}")
        messages.append({"role": "assistant", "content": bot_reply})
        # Speak the bot's reply
        speak(bot_reply, tts_lang)
    except Exception as e:
        print(Fore.RED + f"Error occurred: {e}")
        return

    while True:
        # Listen for user input
        user_input = listen(stt_lang)
        if not user_input:
            continue # Try listening again if empty or failed
            
        print(Fore.GREEN + f"You [{language_name}]: {Fore.WHITE}{user_input}")
        
        # Check termination (in both english and transliterated cases)
        if "quit" in user_input.lower() or "exit" in user_input.lower() or "stop" in user_input.lower():
            print(Fore.CYAN + "Goodbye!")
            break
            
        messages.append({"role": "user", "content": user_input})
        
        try:
            print(Fore.CYAN + "[System] Processing reply...")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
            )
            bot_reply = response.choices[0].message.content
            
            clean_reply = bot_reply.split("LEAD_CAPTURE:")[0].strip() # Don't speak the JSON
            if clean_reply:
                print(Fore.YELLOW + f"\nBot [{language_name}]: {Fore.WHITE}{clean_reply}")
            
            messages.append({"role": "assistant", "content": bot_reply})
            
            # Speak the text
            if clean_reply:
                speak(clean_reply, tts_lang)
            
            if "LEAD_CAPTURE:" in bot_reply:
                print(Fore.YELLOW + bot_reply[bot_reply.index("LEAD_CAPTURE:"):])
                print(Fore.GREEN + "\n[System] Lead capture detected. Saving lead and ending chat.")
                break
                
        except Exception as e:
            print(Fore.RED + f"Error occurred: {e}")
            break

if __name__ == "__main__":
    main()
