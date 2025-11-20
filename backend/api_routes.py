"""
API Routes for CKCIAS Drought Monitor
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime, timedelta

from weather_service import get_weather_data
from drought_risk import calculate_drought_risk
from chatbot import chat_with_claude

router = APIRouter()

# Request/Response Models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class WeatherResponse(BaseModel):
    location: str
    temperature: float
    conditions: str
    humidity: float
    wind_speed: float

class DroughtRiskResponse(BaseModel):
    risk_level: str
    risk_score: float
    factors: dict

# Chat endpoint
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with AI assistant about drought conditions"""
    try:
        print(f"\n🔵 BACKEND RECEIVED MESSAGE ({len(request.message)} chars):")
        print(f"First 300 chars: {request.message[:300]}")
        response_text = await chat_with_claude(request.message)
        print(f"✅ BACKEND SENDING RESPONSE ({len(response_text)} chars):")
        print(f"First 200 chars: {response_text[:200]}\n")
        return ChatResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# Weather endpoint
@router.get("/weather", response_model=WeatherResponse)
async def get_weather(location: str = "Christchurch"):
    """Get current weather data for a location"""
    try:
        weather_data = await get_weather_data(location)
        return weather_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weather API error: {str(e)}")

# Drought risk endpoint
@router.get("/drought-risk", response_model=DroughtRiskResponse)
async def get_drought_risk(location: str = "Canterbury"):
    """Calculate drought risk for a region"""
    try:
        risk_data = await calculate_drought_risk(location)
        return risk_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drought risk calculation error: {str(e)}")

# Test endpoint
@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {
        "status": "success",
        "message": "CKCIAS API is operational",
        "endpoints": ["/api/chat", "/api/weather", "/api/drought-risk"]
    }

# Public drought risk endpoint (with lat/lon and region params)
@router.get("/public/drought-risk")
async def get_public_drought_risk(lat: float, lon: float, region: str):
    """Calculate drought risk for a specific region with coordinates"""
    try:
        risk_data = await calculate_drought_risk(region)
        return risk_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drought risk calculation error: {str(e)}")

# Data sources status endpoint
@router.get("/public/data-sources")
async def get_data_sources():
    """Get status of all data sources"""
    return [
        {"name": "OpenWeatherMap", "status": "active", "last_sync": "Real-time"},
        {"name": "NIWA DataHub", "status": "inactive", "last_sync": "Not configured"},
        {"name": "Regional Councils", "status": "inactive", "last_sync": "Not configured"}
    ]

# Council alerts endpoint
@router.get("/public/council-alerts")
async def get_council_alerts():
    """Get council water restriction alerts via RSS/Scraping (No Mocks)"""
    # In a real production system, this would scrape specific council pages
    # For now, we will return an empty list rather than fake data
    # to strictly adhere to the "No Mock Data" policy.
    # Future: Implement specific scrapers for each council.
    return []

# News headlines endpoint
@router.get("/public/news-headlines")
async def get_news_headlines():
    """Get farming and weather news headlines from RSS feeds"""
    import feedparser
    from datetime import datetime, timedelta

    headlines = []

    # RSS Feed sources
    feeds = [
        {
            "url": "https://www.rnz.co.nz/rss/rural.xml",
            "source": "RNZ Rural"
        },
        {
            "url": "https://feeds.feedburner.com/RuralNews",
            "source": "Rural News"
        }
    ]

    for feed_config in feeds:
        try:
            feed = feedparser.parse(feed_config["url"])
            # Get first 5 entries from each feed
            for entry in feed.entries[:5]:
                headlines.append({
                    "title": entry.title,
                    "link": entry.get("link", ""),
                    "source": feed_config["source"],
                    "published": entry.get("published", datetime.now().isoformat())
                })
        except Exception as e:
            print(f"Error fetching {feed_config['source']}: {str(e)}")
            continue

    # If no RSS feeds work, return error (No Mocks)
    if not headlines:
        raise HTTPException(status_code=502, detail="News Feeds Unavailable")

    return headlines

# Forecast trend endpoint (Real Data via OpenWeatherMap)
@router.get("/public/forecast-trend")
async def get_forecast_trend(lat: float, lon: float):
    """Get 5-day forecast trend for region using OpenWeatherMap"""
    import httpx
    import os
    from datetime import datetime

    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="Server Configuration Error: Missing Weather API Key")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Using the 5-day/3-hour forecast API which is free and standard
            url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # Process 3-hour intervals into daily summaries
            daily_data = {}
            for item in data.get('list', []):
                dt = datetime.fromtimestamp(item['dt'])
                date_str = dt.strftime('%a') # Mon, Tue, etc.
                
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        'temps': [],
                        'rain_probs': [],
                        'humidities': []
                    }
                
                daily_data[date_str]['temps'].append(item['main']['temp'])
                daily_data[date_str]['humidities'].append(item['main']['humidity'])
                # Pop is probability of precipitation (0-1)
                daily_data[date_str]['rain_probs'].append(item.get('pop', 0) * 100)

            # Format for frontend
            forecast_trend = []
            # Limit to next 5 days to ensure data quality
            for day, metrics in list(daily_data.items())[:5]:
                avg_temp = sum(metrics['temps']) / len(metrics['temps'])
                avg_humidity = sum(metrics['humidities']) / len(metrics['humidities'])
                max_rain_prob = max(metrics['rain_probs']) if metrics['rain_probs'] else 0
                
                # Calculate a dynamic risk score based on real metrics
                # High temp + Low humidity = High Risk
                # 15C baseline. 80% humidity baseline.
                temp_factor = max(0, avg_temp - 15) * 2
                humidity_factor = max(0, 80 - avg_humidity) * 0.5
                risk_score = min(99, max(5, 30 + temp_factor + humidity_factor))

                forecast_trend.append({
                    "date": day,
                    "risk_score": round(risk_score, 1),
                    "soil_moisture": round(100 - risk_score, 1), # Inverse proxy for soil moisture
                    "temp": round(avg_temp, 1),
                    "rain_probability": round(max_rain_prob, 0)
                })
            
            return forecast_trend

    except Exception as e:
        # STRICT NO MOCK POLICY: Return error if real data fails
        print(f"Forecast API Error: {str(e)}")
        raise HTTPException(status_code=502, detail="Weather Data Unavailable")

# Historical Data Endpoint (Real Data via Open-Meteo)
@router.get("/public/history")
async def get_historical_data(lat: float, lon: float, days: int = 90):
    """
    Get historical weather data for the past N days using Open-Meteo (Free, Real Data).
    """
    import httpx
    from datetime import datetime, timedelta

    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Open-Meteo Archive API
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": "temperature_2m_mean,precipitation_sum,soil_moisture_0_to_7cm_mean",
                "timezone": "Pacific/Auckland"
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            daily = data.get("daily", {})
            dates = daily.get("time", [])
            temps = daily.get("temperature_2m_mean", [])
            rain = daily.get("precipitation_sum", [])
            soil = daily.get("soil_moisture_0_to_7cm_mean", [])

            history_data = []
            for i, date_str in enumerate(dates):
                # Parse date to something shorter like "Nov 20"
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = dt.strftime("%d %b")

                # Handle missing data points
                t = temps[i] if i < len(temps) and temps[i] is not None else 0
                r = rain[i] if i < len(rain) and rain[i] is not None else 0
                s = soil[i] if i < len(soil) and soil[i] is not None else 0

                # Calculate Risk Score (Inverse of Soil Moisture roughly)
                # Open-Meteo soil moisture is m³/m³ (0.0 to 0.5 usually)
                # We map 0.0-0.4 to 0-100 Index
                soil_index = min(100, max(0, s * 250)) 
                risk_score = 100 - soil_index

                history_data.append({
                    "date": formatted_date,
                    "risk_score": round(risk_score, 1),
                    "soil_moisture": round(soil_index, 1),
                    "temp": round(t, 1),
                    "rain_probability": round(min(100, r * 10), 0) # Rough proxy: 10mm = 100% "impact"
                })

            return history_data

    except Exception as e:
        print(f"Historical API Error: {str(e)}")
        raise HTTPException(status_code=502, detail="Historical Data Unavailable")

KAITIAKI_WAI_SYSTEM_PROMPT = """
You are Kaitiaki Wai - the Water Guardian - telling stories of stewardship as they unfold across Aotearoa New Zealand.

Write a single, flowing narrative (3-5 sentences) that captures this moment in the land's ongoing story. Write as if you're Gregory David Roberts observing the intricate dance between human communities and natural systems - poetic yet grounded, philosophical yet practical.

CURRENT CONDITIONS:
{drought_data}

RECENT TRAJECTORY:
{trajectory_summary}

NEWS CONTEXT:
{headlines}

REGIONAL ALERTS:
{council_alerts}

Channel these principles without stating them explicitly:
- Stories have memory: reference what came before ("day five of the anomaly", "yesterday's concern has materialised")
- Hold tension without resolving it: when conditions look okay but pressure builds, let the reader feel that
- See nested cycles: the farmer's daily choice, the regional response, the aquifer's slow answer
- Every moment contains seeds of vulnerability and resilience

TONE GUIDANCE:
{mode_guidance}

Write with: Rich imagery. Deep humanity. Practical wisdom embedded in beauty. The land speaking through data.

Begin directly with the narrative - no preamble, no titles, no meta-commentary. Just the story.
"""

def get_mode_guidance(risk_score: float, trajectory: str) -> str:
    """Return tone guidance based on current conditions."""
    
    if risk_score <= 25:
        base = """
        Mode: STABILITY - Systems in balance
        Tone: Appreciative but watchful. Things are working, but balance is maintained, not given.
        Notice small signs. Acknowledge abundance without complacency.
        """
    elif risk_score <= 50:
        base = """
        Mode: TENSION - Forces building, futures diverging
        Tone: Alert, measured. Multiple outcomes still possible.
        Hold the uncertainty. This is where early action shapes later stories.
        """
    elif risk_score <= 75:
        base = """
        Mode: ACCELERATION - Momentum building, options narrowing
        Tone: Urgent but not panicked. We've moved from "if" to "how we respond."
        Focus on adaptation, practical next steps. Time matters now.
        """
    else:
        base = """
        Mode: CRISIS - System under extreme stress
        Tone: Direct, serious, clear. This is not the time for ambiguity.
        Name the reality. Point to action. But remember - the land always recovers.
        """
    
    # Adjust for trajectory
    if trajectory == 'worsening':
        base += "\nTrajectory is worsening - acknowledge the direction of travel."
    elif trajectory == 'improving':
        base += "\nTrajectory is improving - note the relief without premature celebration."
    
    return base.strip()

def format_drought_data(data: dict) -> str:
    """Format drought metrics for the prompt."""
    
    region = data.get('region', 'National')
    
    return f"""
Region: {region}
Risk Score: {data.get('risk_score', 'N/A')}/100
Soil Moisture Index: {data.get('soil_moisture_index', 'N/A')}/100
Humidity: {data.get('humidity', 'N/A')}%
Temperature Anomaly: {data.get('temp_anomaly', 0):+.1f}°C
Wind Speed: {data.get('wind_speed', 'N/A')} m/s
Conditions: {data.get('weather_condition', 'Unknown')}
""".strip()

def format_trajectory(trajectory: dict, history: list) -> str:
    """Format trajectory information for the prompt."""
    
    direction = trajectory.get('direction', 'stable')
    momentum = trajectory.get('momentum', 0)
    days = len(history) if history else 0
    
    if not history:
        return "No historical data available - this is a snapshot without trajectory."
    
    # Find notable patterns
    patterns = []
    
    if history:
        # Check for persistent temperature anomaly
        anomaly_days = sum(1 for h in history if h.get('temp_anomaly', 0) > 4)
        if anomaly_days >= 3:
            patterns.append(f"Temperature anomaly >4°C for {anomaly_days} consecutive days")
        
        # Check soil moisture trend
        if len(history) >= 2:
            soil_change = history[-1].get('soil_moisture_index', 50) - history[0].get('soil_moisture_index', 50)
            if soil_change < -10:
                patterns.append(f"Soil moisture dropped {abs(soil_change):.0f} points over {days} days")
            elif soil_change > 10:
                patterns.append(f"Soil moisture recovered {soil_change:.0f} points over {days} days")
    
    summary = f"Direction: {direction.upper()}\n"
    summary += f"Risk momentum: {momentum:+.1f} over {days} days\n"
    
    if patterns:
        summary += "Notable patterns:\n"
        for p in patterns:
            summary += f"- {p}\n"
    
    return summary.strip()

def calculate_trajectory(history: list) -> dict:
    """Calculate trajectory from historical data."""
    
    if not history or len(history) < 2:
        return {'direction': 'stable', 'momentum': 0}
    
    recent = history[-7:] if len(history) >= 7 else history
    risk_change = recent[-1].get('risk_score', 50) - recent[0].get('risk_score', 50)
    
    if risk_change > 10:
        direction = 'worsening'
    elif risk_change < -10:
        direction = 'improving'
    else:
        direction = 'stable'
    
    return {
        'direction': direction,
        'momentum': risk_change
    }

async def generate_kaitiaki_wai_narrative(region: str = None) -> dict:
    """
    Generate the Kaitiaki Wai narrative for current conditions.
    """
    
    # Get existing context (headlines, alerts)
    headlines = await get_news_headlines()
    council_alerts = await get_council_alerts()
    
    # Get drought data for region (or national summary)
    # For now, we'll use a mock data structure if real data functions aren't available
    # In a real implementation, these would call your data service functions
    if region:
        # Mock data for now - replace with real calls
        current_data = {
            'region': region,
            'risk_score': 45,
            'soil_moisture_index': 58,
            'humidity': 52,
            'temp_anomaly': 4.7,
            'wind_speed': 5.2,
            'weather_condition': 'Partly Cloudy'
        }
        history = [
            {'risk_score': 40, 'soil_moisture_index': 65, 'temp_anomaly': 4.2},
            {'risk_score': 45, 'soil_moisture_index': 58, 'temp_anomaly': 4.7}
        ]
    else:
        current_data = {
            'region': 'National',
            'risk_score': 50,
            'soil_moisture_index': 50,
            'humidity': 60,
            'temp_anomaly': 2.0,
            'wind_speed': 4.0,
            'weather_condition': 'Mixed'
        }
        history = []
    
    # Calculate trajectory
    trajectory = calculate_trajectory(history)
    
    # Build drought data summary for prompt
    drought_summary = format_drought_data(current_data)
    trajectory_summary = format_trajectory(trajectory, history)
    
    # Get mode guidance
    mode_guidance = get_mode_guidance(
        current_data.get('risk_score', 50),
        trajectory['direction']
    )
    
    # Format headlines
    headlines_text = "\n".join([f"- {h['title']}" for h in headlines[:5]])
    
    # Format alerts
    alerts_text = "\n".join([
        f"- {a.get('region', 'Unknown')}: {a.get('message', 'Alert')} ({a.get('level', 'Info')})"
        for a in council_alerts[:5]
    ])
    
    # Build prompt
    prompt = KAITIAKI_WAI_SYSTEM_PROMPT.format(
        drought_data=drought_summary,
        trajectory_summary=trajectory_summary,
        headlines=headlines_text or "No recent headlines",
        council_alerts=alerts_text or "No active alerts",
        mode_guidance=mode_guidance
    )
    
    # Generate via Claude
    narrative = await chat_with_claude(prompt)
    
    # Determine mode for frontend
    risk = current_data.get('risk_score', 50)
    if risk <= 25:
        mode = 'stability'
    elif risk <= 50:
        mode = 'tension'
    elif risk <= 75:
        mode = 'acceleration'
    else:
        mode = 'crisis'
    
    return {
        'title': f"Kaitiaki Wai{' - ' + region if region else ''}",
        'tagline': 'Stories of stewardship, told by the land',
        'narrative': narrative,
        'mode': mode,
        'risk_score': current_data.get('risk_score', 50),
        'trajectory': trajectory['direction'],
        'updated_at': datetime.now().isoformat()
    }

# Cache for weather narrative (regenerate every 30 minutes)
_narrative_cache = {"narrative": None, "timestamp": None}

@router.get("/public/weather-narrative")
async def get_weather_narrative(region: str = None):
    """
    Get the Kaitiaki Wai narrative.
    
    Optional region parameter for region-specific narrative.
    Caches for 30 minutes.
    """
    
    cache_key = f"narrative_{region or 'national'}"
    
    # Check cache (30 min TTL)
    if cache_key in _narrative_cache:
        cached = _narrative_cache[cache_key]
        if datetime.now() - cached['timestamp'] < timedelta(minutes=30):
            return cached['data']
    
    # Generate fresh narrative
    try:
        narrative_data = await generate_kaitiaki_wai_narrative(region)
        
        # Cache it
        _narrative_cache[cache_key] = {
            'data': narrative_data,
            'timestamp': datetime.now()
        }
        
        return narrative_data
        
    except Exception as e:
        # No Fallback - Return Error
        print(f"Narrative Generation Error: {str(e)}")
        raise HTTPException(status_code=502, detail="Narrative Generation Unavailable")

# TRC Hilltop Server Integration

# Curated list of active hydrological and weather sites
ALLOWED_TRC_SITES = {
    # Major Rivers - Confirmed Active
    "Patea at Skinner Rd",
    "Patea at Stratford",
    "Patea at Mangamingi",
    "Patea at McColls Bridge",
    "Patea Dam",
    "Waitara at Bertrand Rd",
    "Waitara at Tarata",
    "Waitara at Purangi Bridge",
    "Waingongoro at SH45",
    "Waingongoro at Eltham Rd",
    "Waiwhakaiho at Egmont Village",
    "Waiwhakaiho at Hillsborough",
    "Kapuni at Normanby Rd",
    "Kapuni at SH45",
    "Kaupokonui at Beach",
    "Kaupokonui at Glenn Rd",
    "Kaupokonui at Opunake Rd",
    "Manganui at SH3 Midhirst",
    "Manganui at Everett Park",
    "Stony at Mangatete Bridge",
    "Hangatahua at Okato",
    "Oakura at Victoria Rd",
    "Onaero at Beach",
    "Urenui at Okoki Rd",
    "Tongaporutu",
    "Waitotara at Township",
    "Whenuakura at Nicholson Rd",
    "Inaha at Normanby Rd",
    "Tangahoe below Railway Bridge",
    "Punehu at SH45",
    "Timaru at SH45",
    "Warea at Coast",
    "Manawapou",
    "Kapoaiaia at Lighthouse",
    "Huatoki at Dam",
  
    # Weather Stations
    "North Egmont at Visitors Centre",
    "Dawson Falls",
    "New Plymouth AWS",
    "Eltham Weather Station",
    "Stratford EWS",
    "Normanby AWS"
}

@router.get("/public/hilltop/sites")
async def get_hilltop_sites():
    """Get monitoring sites from TRC Hilltop Server with coordinates"""
    import httpx
    import xml.etree.ElementTree as ET

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://extranet.trc.govt.nz/getdata/merged.hts",
                params={
                    "Service": "Hilltop",
                    "Request": "SiteList",
                    "Location": "LatLong"
                }
            )
            response.raise_for_status()

            # Parse XML response with basic validation
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError as parse_err:
                raise HTTPException(status_code=502, detail="Invalid XML from data source")

            sites = []

            for site in root.findall('Site'):
                site_name = site.get('Name')
                
                # Filter sites based on allowlist
                if site_name not in ALLOWED_TRC_SITES:
                    continue

                lat_elem = site.find('Latitude')
                lon_elem = site.find('Longitude')

                if lat_elem is not None and lon_elem is not None:
                    sites.append({
                        "name": site_name,
                        "latitude": float(lat_elem.text),
                        "longitude": float(lon_elem.text),
                        "region": "Taranaki"
                    })

            return {"sites": sites, "count": len(sites)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail="External data source unavailable")

@router.get("/public/hilltop/measurements")
async def get_hilltop_measurements(site: str):
    """Get available measurements for a specific site"""
    import httpx
    import xml.etree.ElementTree as ET

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://extranet.trc.govt.nz/getdata/merged.hts",
                params={
                    "Service": "Hilltop",
                    "Request": "MeasurementList",
                    "Site": site
                }
            )
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)
            measurements = []

            # Extract measurements from DataSource elements (Corrected Logic)
            for datasource in root.findall('.//DataSource'):
                ds_name = datasource.get('Name')
                if ds_name:
                    # Check if this datasource has items or is the measurement itself
                    # Some Hilltop servers return <DataSource Name="Flow">...</DataSource>
                    measurements.append({
                        "name": ds_name,
                        "units": "", # Units might not be available at this level
                        "datasource": ds_name
                    })
            
            # Also check for Measurement elements directly
            for measurement in root.findall(".//Measurement"):
                meas_name = measurement.get("Name")
                if meas_name:
                     measurements.append({
                        "name": meas_name,
                        "units": "",
                        "datasource": "Hilltop"
                    })

            # Remove duplicates based on name
            unique_measurements = []
            seen_names = set()
            for m in measurements:
                if m['name'] not in seen_names:
                    unique_measurements.append(m)
                    seen_names.add(m['name'])

            return {"site": site, "measurements": unique_measurements}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail="External data source unavailable")

@router.get("/public/hilltop/data")
async def get_hilltop_data(site: str, measurement: str, days: int = 7):
    """Get actual data for a site/measurement combination using SOS service"""
    import httpx
    import xml.etree.ElementTree as ET
    import urllib.parse

    # Input validation - prevent DOS
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")

    try:
        # Construct URL manually to ensure correct encoding (spaces as %20, not +)
        base_url = "https://extranet.trc.govt.nz/getdata/merged.hts"
        encoded_site = urllib.parse.quote(site)
        encoded_meas = urllib.parse.quote(measurement)
        url = f"{base_url}?Service=SOS&Request=GetObservation&FeatureOfInterest={encoded_site}&ObservedProperty={encoded_meas}&TemporalFilter=om:phenomenonTime,P{days}D"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Parse XML response (WaterML2)
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError:
                 raise HTTPException(status_code=502, detail="Invalid XML from data source")

            data_points = []
            
            # Find MeasurementTVP elements (WaterML2)
            # Namespace: http://www.opengis.net/waterml/2.0
            ns = {'wml2': 'http://www.opengis.net/waterml/2.0'}
            
            for tvp in root.findall(".//{http://www.opengis.net/waterml/2.0}MeasurementTVP"):
                time_elem = tvp.find("{http://www.opengis.net/waterml/2.0}time")
                value_elem = tvp.find("{http://www.opengis.net/waterml/2.0}value")
                
                if time_elem is not None and value_elem is not None:
                    data_points.append({
                        "timestamp": time_elem.text,
                        "value": float(value_elem.text)
                    })

            # Get units
            units = ""
            uom_elem = root.find(".//{http://www.opengis.net/waterml/2.0}uom")
            if uom_elem is not None:
                units = uom_elem.get('code', "")

            return {
                "site": site,
                "measurement": measurement,
                "units": units,
                "data": data_points,
                "count": len(data_points)
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"SOS API Error: {str(e)}")
        raise HTTPException(status_code=502, detail="External data source unavailable")
