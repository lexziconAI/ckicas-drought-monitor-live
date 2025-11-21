import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from chatbot import chat_with_claude

async def test_chatbot():
    print("Testing Chatbot API Integration (Direct Anthropic)...")
    try:
        # Test a simple prompt
        message = "What is the capital of New Zealand? Answer in one word."
        print(f"Sending message: '{message}'")
        
        response = await chat_with_claude(message)
        
        print("\nResult:")
        print(f"Response: {response}")
        
        if "Wellington" in response:
            print("\n✅ SUCCESS: Chatbot API returned correct response.")
        else:
            print("\n⚠️ WARNING: Response was unexpected, but API call succeeded.")
            
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_chatbot())
