import os
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
import tempfile
from fastapi.middleware.cors import CORSMiddleware

from database import save_lead

load_dotenv()

app = FastAPI()

# Enable CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Make sure static directory exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in the environment.")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

SYSTEM_PROMPT_TEMPLATE = """You are a highly persuasive Sales Conversational AI for Mierae Solar.
Your objective is to convert users into solar leads.
You MUST speak in {language}. Do NOT use English unless the user explicitly forces it. Keep sentences relatively short and natural.

CRITICAL RULES:
- You must ONLY ask ONE question at a time!
- Do NOT output the entire flow or multiple steps at once.
- Wait for the user to answer before moving to the next question or step.
- Be highly conversational and natural. Do not list out step numbers.
- NEVER output LEAD_CAPTURE until the user has ACTUALLY typed or spoken their real Name and Phone number in this conversation. If you have not yet received the actual name and phone number from the user's messages, keep asking — do NOT generate LEAD_CAPTURE yet.

Conversation Flow (Progress through these one by one):
1. Greeting: Introduce yourself concisely. Ask if they want to reduce their electricity bill.
2. Qualification: Ask these sequentially, ONE BY ONE, waiting for their reply each time:
   - What is your monthly electricity bill?
   - Is it your own house?
   - Is the roof free/available?
   - Which city?
3. Value Pitch: Pitch the PM Surya Ghar Yojana (Up to 40% subsidy, ₹78,000 subsidy, 300 units free, 1 crore homes target, ~6.75% loan, 25 years free electricity, 3kW makes bill zero).
4. Objection Handling (if they have doubts): "Too costly" -> mention EMI option. "Not sure" -> Free site visit. "No time" -> We manage everything.
5. Closing: Ask to book a free site visit. Ask for their Name first, wait for reply, then ask for their Phone number, wait for reply.

Only AFTER the user has given you their actual Name AND actual Phone number in their messages, output LEAD_CAPTURE at the very end of your final message:

LEAD_CAPTURE: {{
  "Name": "<actual name the user told you>",
  "Phone": "<actual phone number the user told you>",
  "City": "<actual city the user told you>",
  "Electricity bill": "<actual bill amount the user told you>",
  "House type": "<own/rented as the user told you>",
  "Interested": "Yes"
}}

IMPORTANT: The values in LEAD_CAPTURE must be real data from the conversation — never placeholder text like [Extracted Name]. If you don't have the real value yet, do NOT output LEAD_CAPTURE.
"""

LANG_MAP = {
    "Hindi": "hi",
    "Telugu": "te",
    "Urdu": "ur",
    "Odia": "or",
    "English": "en"
}

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    language: str

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.post("/api/chat")
def chat(payload: ChatRequest):
    try:
        language_name = payload.language

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language=language_name)
        api_messages = [{"role": "system", "content": system_prompt}]
        for m in payload.messages:
            api_messages.append({"role": m.role, "content": m.content})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=api_messages,
            temperature=0.7,
        )
        
        bot_reply = response.choices[0].message.content
        completed = False

        # Check for lead capture JSON
        if "LEAD_CAPTURE:" in bot_reply:
            try:
                parts = bot_reply.split("LEAD_CAPTURE:")
                clean_reply = parts[0].strip()
                json_str = parts[1].strip()

                # sometimes LLM outputs ```json around it
                if json_str.startswith("```json"):
                    json_str = json_str[7:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]

                lead_data = json.loads(json_str.strip())

                # Guard: only accept if Name and Phone are real values, not placeholders
                name  = lead_data.get("Name",  "")
                phone = lead_data.get("Phone", "")
                has_real_data = (
                    name and phone
                    and "[" not in name  and "]" not in name
                    and "[" not in phone and "]" not in phone
                    and name.strip()  != ""
                    and phone.strip() != ""
                )

                if has_real_data:
                    save_lead(lead_data)
                    bot_reply = clean_reply
                    completed = True
                else:
                    # LLM generated LEAD_CAPTURE prematurely — ignore it, keep chatting
                    print("[Guard] LEAD_CAPTURE rejected: placeholder values detected.")
                    bot_reply = clean_reply or bot_reply

            except Exception as e:
                print("Error parsing LEAD_CAPTURE:", e)

        # TTS is handled client-side via Web Speech API
        return {
            "reply": bot_reply,
            "audio_base64": "",
            "completed": completed
        }

    except Exception as e:
        print("Chat Error:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = Form("Hindi")):
    # Save uploaded file temporarily
    try:
        suffix = os.path.splitext(file.filename)[1] or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
            fp.write(await file.read())
            temp_path = fp.name
            
        with open(temp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(file.filename, f.read()),
                model="whisper-large-v3",
                response_format="text",
                language=LANG_MAP.get(language, "hi") # Provide hint
            )
            
        os.remove(temp_path)
        return {"text": transcription}
    except Exception as e:
        print("Transcription Error:", e)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
