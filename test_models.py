import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv('.env')
print(f"API key length: {len(os.environ.get('GEMINI_API_KEY', ''))}")
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

try:
    for m in genai.list_models():
        print(m.name, m.supported_generation_methods)
except Exception as e:
    print("Error:", e)
