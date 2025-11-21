"""
Drought Risk Calculation for CKCIAS Drought Monitor
Analyzes and calculates drought risk levels using TRC SOS (WaterML2) and OpenWeather APIs
"""

import httpx
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, Any
import logging
import xml.etree.ElementTree as ET
import urllib.parse

# Load environment variables
load_dotenv("../sidecar/.env")

# API Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "d7ab6944b5791f6c502a506a6049165f")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
TRC_SOS_BASE_URL = "https://extranet.trc.govt.nz/getdata/merged.hts"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_openweather_data(location: str) -> Dict[str, Any]:
    """
    Fetch current weather data from OpenWeather API

    Args:
        location: City name or coordinates

    Returns:
        Dict containing temperature, humidity, and rainfall data
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch current weather
            current_url = f"{OPENWEATHER_BASE_URL}/weather"
            current_params = {
                "q": location,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric"
            }

            current_response = await client.get(current_url, params=current_params)
            current_response.raise_for_status()
            current_data = current_response.json()

            # Fetch forecast for rainfall prediction
            forecast_url = f"{OPENWEATHER_BASE_URL}/forecast"
            forecast_params = {
                "q": location,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "cnt": 8  # 24 hours (3-hour intervals)
            }

            forecast_response = await client.get(forecast_url, params=forecast_params)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()

            # Calculate 24-hour rainfall
            rainfall_24h = sum(
                item.get("rain", {}).get("3h", 0)
                for item in forecast_data.get("list", [])
            )

            return {
                "temperature": current_data["main"]["temp"],
                "humidity": current_data["main"]["humidity"],
                "rainfall_24h": rainfall_24h,
                "weather_description": current_data["weather"][0]["description"],
                "wind_speed": current_data.get("wind", {}).get("speed", 0),
                "pressure": current_data["main"]["pressure"],
                "weather_main": current_data["weather"][0]["main"],
                "coordinates": {
                    "lat": current_data["coord"]["lat"],
                    "lon": current_data["coord"]["lon"]
                }
            }

    except httpx.HTTPError as e:
        logger.error(f"OpenWeather API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error fetching OpenWeather data: {e}")
        raise


async def fetch_trc_flow_data(site_name: str = "Patea at Skinner Rd") -> Dict[str, Any]:
    """
    Fetch latest river flow data from TRC Hilltop SOS service (WaterML2)
    
    Args:
        site_name: The monitoring site name (e.g., "Patea at Skinner Rd")
        
    Returns:
        Dict containing flow value and timestamp, or None if failed.
    """
    try:
        # Construct URL manually to ensure correct encoding (spaces as %20)
        encoded_site = urllib.parse.quote(site_name)
        # SOS Request for latest observation (Flow)
        # Using P1D (1 day) filter to avoid timeouts but ensure recent data
        url = f"{TRC_SOS_BASE_URL}?Service=SOS&Request=GetObservation&FeatureOfInterest={encoded_site}&ObservedProperty=Flow&TemporalFilter=om:phenomenonTime,P1D"
        
        logger.info(f"Fetching TRC SOS data from: {url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                # Parse WaterML2 response
                try:
                    root = ET.fromstring(response.text)
                    ns = {'wml2': 'http://www.opengis.net/waterml/2.0'}
                    
                    # Get last point
                    points = root.findall('.//wml2:MeasurementTVP', ns)
                    if points:
                        last_point = points[-1]
                        time_el = last_point.find('wml2:time', ns)
                        value_el = last_point.find('wml2:value', ns)
                        
                        if time_el is not None and value_el is not None:
                            flow_val = float(value_el.text)
                            logger.info(f"TRC Flow Data: {flow_val} m3/s at {time_el.text}")
                            return {
                                "site": site_name,
                                "time": time_el.text,
                                "flow_rate": flow_val,
                                "unit": "m3/s"
                            }
                except ET.ParseError as e:
                    logger.error(f"XML Parse Error for TRC data: {e}")
            else:
                logger.warning(f"TRC SOS Error: {response.status_code} - {response.text[:100]}")
                
    except Exception as e:
        logger.warning(f"Error fetching TRC flow data: {e}")
    
    return None


def calculate_risk_score(temperature: float, humidity: float, rainfall_24h: float,
                        flow_data: Dict[str, Any] = None) -> tuple[float, Dict[str, float]]:
    """
    Calculate drought risk score based on weather factors and river flow

    Args:
        temperature: Current temperature in Celsius
        humidity: Current humidity percentage
        rainfall_24h: Predicted rainfall in next 24 hours (mm)
        flow_data: Optional TRC flow data

    Returns:
        Tuple of (risk_score, factors_dict)

    Risk Calculation:
        - Temperature factor (0-3): Above 25C increases risk
        - Humidity factor (0-4): Below 40% increases risk significantly
        - Rainfall factor (0-3): Below 5mm/24h increases risk
        - Flow factor (0-2): Low river flow increases risk
        - Total score 0-10
    """
    factors = {}

    # Temperature risk (0-3 points)
    # Normal range: 10-25C, above 25C increases risk
    if temperature >= 30:
        temp_risk = 3.0
    elif temperature >= 25:
        temp_risk = 2.0
    elif temperature >= 20:
        temp_risk = 1.0
    else:
        temp_risk = 0.0

    # Calculate temperature anomaly from baseline (15C for NZ)
    baseline_temp = 15.0
    temp_anomaly = round(temperature - baseline_temp, 1)

    factors["temperature_risk"] = temp_risk
    factors["temperature"] = temperature
    factors["temperature_anomaly"] = temp_anomaly

    # Humidity risk (0-4 points)
    # Critical: <30%, High: 30-40%, Moderate: 40-50%, Low: >50%
    if humidity < 30:
        humidity_risk = 4.0
    elif humidity < 40:
        humidity_risk = 3.0
    elif humidity < 50:
        humidity_risk = 2.0
    elif humidity < 60:
        humidity_risk = 1.0
    else:
        humidity_risk = 0.0
    factors["humidity_risk"] = humidity_risk
    factors["humidity"] = humidity

    # Rainfall risk (0-3 points)
    # Very dry: <1mm, Dry: 1-5mm, Moderate: 5-10mm, Wet: >10mm
    if rainfall_24h < 1:
        rainfall_risk = 3.0
    elif rainfall_24h < 5:
        rainfall_risk = 2.0
    elif rainfall_24h < 10:
        rainfall_risk = 1.0
    else:
        rainfall_risk = 0.0

    # Calculate rainfall deficit (expected 5mm/day - actual)
    expected_rainfall = 5.0
    rainfall_deficit = round(max(0, expected_rainfall - rainfall_24h), 1)

    factors["rainfall_risk"] = rainfall_risk
    factors["rainfall_24h"] = rainfall_24h
    factors["rainfall_deficit"] = rainfall_deficit
    
    # Flow Risk (0-2 points) - New Factor
    flow_risk = 0.0
    if flow_data:
        flow_rate = flow_data.get("flow_rate", 10.0)
        # Thresholds for Patea at Skinner Rd (Normal ~1.8-5.0)
        if flow_rate < 1.5:
            flow_risk = 2.0 # Very low - drought stress
        elif flow_rate < 2.5:
            flow_risk = 1.0 # Below normal
        else:
            flow_risk = 0.0 # Normal/healthy
        
        factors["flow_rate"] = flow_rate
        factors["flow_risk"] = flow_risk
        factors["trc_data_available"] = True
    else:
        factors["trc_data_available"] = False

    # Calculate weighted total score (0-10)
    # Adjusted max score potential: 3+4+3+2 = 12, so we cap at 10
    total_score = min(10.0, temp_risk + humidity_risk + rainfall_risk + flow_risk)

    # Calculate soil moisture index (inverse of risk, 0-100 scale)
    # Lower risk = higher soil moisture
    soil_moisture_index = round(100 - (total_score * 10), 1)
    factors["soil_moisture_index"] = soil_moisture_index

    return round(total_score, 2), factors


def categorize_risk(risk_score: float) -> str:
    """
    Categorize risk score into risk levels

    Args:
        risk_score: Numeric risk score (0-10)

    Returns:
        Risk level category
    """
    if risk_score < 2:
        return "Low"
    elif risk_score < 4:
        return "Moderate"
    elif risk_score < 6:
        return "High"
    elif risk_score < 8:
        return "Severe"
    else:
        return "Extreme"


async def calculate_drought_risk(location: str) -> Dict[str, Any]:
    """
    Calculate drought risk for a region using real API data

    Args:
        location: Location name (city/region)

    Returns:
        Dict containing:
            - risk_level: Category (Low/Moderate/High/Severe/Extreme)
            - risk_score: Numeric score (0-10)
            - factors: Dict of contributing factors

    Raises:
        Exception: If unable to fetch weather data
    """
    try:
        logger.info(f"Calculating drought risk for location: {location}")

        # Parallel fetching with graceful fallback
        weather_task = fetch_openweather_data(location)
        flow_task = None
        
        # Region-specific logic: Only call TRC Hilltop for Taranaki
        if "taranaki" in location.lower() or "new plymouth" in location.lower() or "patea" in location.lower():
            logger.info(f"Region is Taranaki-related ({location}), adding TRC flow task.")
            flow_task = fetch_trc_flow_data("Patea at Skinner Rd")
            
        # Execute tasks
        if flow_task:
            results = await asyncio.gather(weather_task, flow_task, return_exceptions=True)
            
            # Handle Weather Data (Critical)
            if isinstance(results[0], Exception):
                raise results[0]
            weather_data = results[0]
            
            # Handle Flow Data (Optional/Graceful Fallback)
            if isinstance(results[1], Exception):
                logger.warning(f"TRC flow fetch failed: {results[1]}")
                flow_data = None
            else:
                flow_data = results[1]
        else:
            weather_data = await weather_task
            flow_data = None

        logger.info(f"Weather data fetched: Temp={weather_data['temperature']}C, "
                   f"Humidity={weather_data['humidity']}%, "
                   f"Rainfall={weather_data['rainfall_24h']}mm")

        # Calculate risk score
        risk_score, factors = calculate_risk_score(
            temperature=weather_data["temperature"],
            humidity=weather_data["humidity"],
            rainfall_24h=weather_data["rainfall_24h"],
            flow_data=flow_data
        )

        # Categorize risk level
        risk_level = categorize_risk(risk_score)

        logger.info(f"Drought risk calculated: {risk_level} (score: {risk_score})")

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "factors": factors,
            "location": location,
            "region": location,
            "weather_description": weather_data["weather_description"],
            "extended_metrics": {
                "wind_speed": weather_data.get("wind_speed", 0),
                "humidity": weather_data.get("humidity", 0),
                "pressure": weather_data.get("pressure", 0),
                "weather_main": weather_data.get("weather_main", "Clear")
            },
            "coordinates": weather_data.get("coordinates", {}),
            "data_source": "OpenWeather + TRC SOS",
            "last_updated": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error calculating drought risk: {e}")
        # Return error response
        raise Exception(f"Unable to calculate drought risk for {location}: {str(e)}")
