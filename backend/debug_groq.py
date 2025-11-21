import os
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

# 1. Load Environment
print("--- GROQ DIAGNOSTIC START ---")
load_dotenv()

# Load from environment
if "GROQ_API_KEY" not in os.environ:
    print("❌ GROQ_API_KEY not set in environment")
    exit(1)
if "GROQ_KIMI_MODEL" not in os.environ:
    os.environ["GROQ_KIMI_MODEL"] = "moonshotai/kimi-k2-instruct-0905"

# 2. Check Key
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    masked_key = api_key[:10] + "..." + api_key[-4:]
    print(f"✅ API Key found: {masked_key}")
else:
    print("❌ GROQ_API_KEY is missing or empty")
    exit(1)

# 3. Check Model
model = os.getenv("GROQ_KIMI_MODEL")
print(f"ℹ️  Target Model: {model}")

# 4. Test Connection
async def test_connection():
    print("\nAttempting API Call to Groq...")
    try:
        client = AsyncGroq(api_key=api_key)
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello, are you operational? Reply with 'YES' only."}
            ],
            max_tokens=10
        )
        print(f"✅ API Response: {completion.choices[0].message.content}")
        print("--- DIAGNOSTIC SUCCESS ---")
    except Exception as e:
        print(f"❌ API Call Failed: {str(e)}")
        print("--- DIAGNOSTIC FAILURE ---")

if __name__ == "__main__":
    asyncio.run(test_connection())
