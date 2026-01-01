from google import genai
import os

# Client automatically finds 'GEMINI_API_KEY' in environment variables
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Write a haiku about coding."
)

print(response.text)