"""
AXIOM-X ULTIMATE DEBUG SCRIPT
Powered by Groq (Kimi K2)

This script performs a comprehensive health check of the CKCIAS Drought Monitor backend.
It verifies:
1. AI Narrative Generation (Groq/Kimi K2)
2. News Feed Fetching (RSS)
3. Council Alerts Scraping (HTTP/BS4)
4. Weather Data Access (OpenWeatherMap)
5. Historical Data Access (Open-Meteo)

Usage: python backend/axiom_x_ultimate_debug.py
"""

import asyncio
import os
import sys
import httpx
import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Import Chatbot (Groq)
try:
    from chatbot import chat_with_claude
except ImportError:
    print("❌ Could not import chatbot.py")
    sys.exit(1)

async def test_groq_narrative():
    print("\n🔍 [1/5] Testing AI Narrative (Groq Kimi K2)...")
    try:
        response = await chat_with_claude("Briefly describe the current drought status in Taranaki based on: Temp 25C, Rain 0mm.")
        print("✅ Groq API Success!")
        print(f"📝 Response Preview: {response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Groq API Failed: {e}")
        return False

async def test_news_feed():
    print("\n🔍 [2/5] Testing News Feed (RSS)...")
    feeds = ["https://feeds.feedburner.com/RuralNews", "https://www.farmersweekly.co.nz/feed/"]
    success = False
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                print(f"✅ RSS Success ({url}): Found {len(feed.entries)} entries")
                print(f"📰 Headline: {feed.entries[0].title}")
                success = True
                break
        except Exception as e:
            print(f"⚠️ RSS Failed ({url}): {e}")
    
    if not success:
        print("❌ All RSS feeds failed")
    return success

async def test_council_alerts():
    print("\n🔍 [3/5] Testing Council Alerts (Scraping)...")
    url = "https://www.trc.govt.nz/council/news-and-events/council-news/"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.title.string if soup.title else "No Title"
                print(f"✅ Scraping Success (TRC): {title}")
                return True
            else:
                print(f"❌ Scraping Failed: Status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Scraping Error: {e}")
        return False

async def test_weather_api():
    print("\n🔍 [4/5] Testing OpenWeatherMap API...")
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        print("❌ Missing OPENWEATHER_API_KEY")
        return False
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat=-39.1&lon=174.1&appid={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Weather API Success: {data['name']} - {data['weather'][0]['description']}")
                return True
            else:
                print(f"❌ Weather API Failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Weather API Error: {e}")
        return False

async def test_historical_api():
    print("\n🔍 [5/5] Testing Open-Meteo Historical API...")
    url = "https://api.open-meteo.com/v1/forecast?latitude=-39.1&longitude=174.1&past_days=7&forecast_days=1&daily=temperature_2m_mean"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Historical API Success: Got {len(data['daily']['time'])} days of data")
                return True
            else:
                print(f"❌ Historical API Failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Historical API Error: {e}")
        return False

async def main():
    print("🚀 STARTING AXIOM-X ULTIMATE DEBUG")
    print("==================================")
    
    results = await asyncio.gather(
        test_groq_narrative(),
        test_news_feed(),
        test_council_alerts(),
        test_weather_api(),
        test_historical_api()
    )
    
    print("\n==================================")
    if all(results):
        print("✅ SYSTEM STATUS: ALL SYSTEMS OPERATIONAL")
        print("If the frontend is still loading, check:")
        print("1. Frontend is running on port 3005")
        print("2. Backend is running on port 9101")
        print("3. Browser Console for CORS errors (Fixed in backend/main.py)")
    else:
        print("⚠️ SYSTEM STATUS: PARTIAL FAILURE")
        print("Check the logs above for specific failures.")

if __name__ == "__main__":
    asyncio.run(main())
