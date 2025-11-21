import os
import asyncio
from dotenv import load_dotenv
from anthropic import AsyncAnthropic

# 1. Load Environment
print("--- DIAGNOSTIC START ---")
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '.env')
print(f"Looking for .env at: {env_path}")

if os.path.exists(env_path):
    print("✅ .env file found")
    load_dotenv(env_path)
else:
    print("❌ .env file NOT found")

# 2. Check Key
api_key = os.getenv("ANTHROPIC_API_KEY")
if api_key:
    masked_key = api_key[:10] + "..." + api_key[-4:]
    print(f"✅ API Key found: {masked_key}")
else:
    print("❌ ANTHROPIC_API_KEY is missing or empty")
    exit(1)

# 3. Check Model
model = os.getenv("ANTHROPIC_HAIKU_MODEL", "claude-3-haiku-20240307")
print(f"ℹ️  Target Model: {model}")

# 4. Test Connection
async def test_connection():
    print("\nAttempting API Call...")
    try:
        client = AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model=model,
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Hello, are you operational? Reply with 'YES' only."}
            ]
        )
        print(f"✅ API Response: {message.content[0].text}")
        print("--- DIAGNOSTIC SUCCESS ---")
    except Exception as e:
        print(f"❌ API Call Failed: {str(e)}")
        print("--- DIAGNOSTIC FAILURE ---")

if __name__ == "__main__":
    asyncio.run(test_connection())
