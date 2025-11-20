import { GoogleGenAI } from "@google/genai";
import { NZ_REGIONS, API_BASE_URL, GOOGLE_API_KEY, OPENWEATHER_API_KEY } from '../constants';
import { DroughtRiskData, DataSource, HistoricalDataPoint, RssFeedItem } from '../types';

// Initialize GenAI Client (Client-side fallback)
const genAI = new GoogleGenAI({ apiKey: GOOGLE_API_KEY });

// Helper to suppress connection errors in console but log real issues
const safeFetch = async (url: string, options?: RequestInit) => {
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      throw new Error(`HTTP_${res.status}`);
    }
    return res;
  } catch (error) {
    const msg = (error as Error).message;
    if (msg.startsWith('HTTP_')) {
      throw error; 
    }
    throw new Error('CONNECTION_REFUSED');
  }
};

export const checkApiHealth = async (): Promise<{ status: 'online' | 'offline' | 'serverless', latency: number }> => {
  const start = Date.now();
  try {
    await safeFetch(`${API_BASE_URL}/health`, { method: 'GET' });
    return { status: 'online', latency: Date.now() - start };
  } catch (e) {
    if (GOOGLE_API_KEY && OPENWEATHER_API_KEY) {
      return { status: 'serverless', latency: 0 };
    }
    return { status: 'offline', latency: 0 };
  }
};

export const fetchDroughtRisk = async (lat: number, lon: number): Promise<DroughtRiskData> => {
  const region = NZ_REGIONS.find(r => 
    Math.abs(r.lat - lat) < 0.1 && Math.abs(r.lon - lon) < 0.1
  ) || { name: "Unknown Region", lat: 0, lon: 0, baseRisk: 30 };

  try {
    const res = await safeFetch(`${API_BASE_URL}/api/public/drought-risk?lat=${lat}&lon=${lon}&region=${encodeURIComponent(region.name)}`);
    return await res.json();
  } catch (error) {
    // Failover: Client-Side OpenWeatherMap Call
    try {
       const weatherRes = await fetch(
        `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&appid=${OPENWEATHER_API_KEY}&units=metric`
      );
      
      if (weatherRes.ok) {
        const weatherData = await weatherRes.json();
        const currentTemp = weatherData.main.temp;
        const humidity = weatherData.main.humidity;
        
        const baselineTemp = 15.0;
        const tempAnomaly = currentTemp - baselineTemp;
        const humidityDeficit = Math.max(0, 80 - humidity);
        
        let baseRisk = region.baseRisk;
        let riskScore = baseRisk + (tempAnomaly * 2.0) + (humidityDeficit * 0.5);
        riskScore = Math.min(99, Math.max(5, Math.floor(riskScore)));

        let riskLevel: 'Low' | 'Medium' | 'High' | 'Critical' = 'Low';
        if (riskScore > 75) riskLevel = 'Critical';
        else if (riskScore > 50) riskLevel = 'High';
        else if (riskScore > 25) riskLevel = 'Medium';

        return {
          region: region.name,
          risk_score: riskScore,
          risk_level: riskLevel,
          factors: {
            rainfall_deficit: humidityDeficit,
            soil_moisture_index: 100 - riskScore,
            temperature_anomaly: parseFloat(tempAnomaly.toFixed(1))
          },
          extended_metrics: {
            wind_speed: weatherData.wind.speed,
            humidity: humidity,
            pressure: weatherData.main.pressure,
            weather_main: weatherData.weather[0].main
          },
          data_source: 'OpenWeatherMap (Live Client)',
          last_updated: new Date().toISOString()
        };
      } else {
        throw new Error("OpenWeatherMap API failed");
      }
    } catch (owError) {
      throw new Error("DATA_UNAVAILABLE");
    }
  }
};

export const fetchForecastTrend = async (lat: number, lon: number): Promise<HistoricalDataPoint[]> => {
  try {
    const res = await safeFetch(`${API_BASE_URL}/api/public/forecast-trend?lat=${lat}&lon=${lon}`);
    return await res.json();
  } catch (e) {
    // No Mock Data - Return Empty Array to signal UI to show "No Data" state
    console.error("Forecast fetch failed:", e);
    return [];
  }
};

export const fetchHistoricalData = async (lat: number, lon: number, days: number = 90): Promise<HistoricalDataPoint[]> => {
  try {
    const res = await safeFetch(`${API_BASE_URL}/api/public/history?lat=${lat}&lon=${lon}&days=${days}`);
    return await res.json();
  } catch (e) {
    console.error("History fetch failed:", e);
    return [];
  }
};

export const fetchCouncilAlerts = async (): Promise<RssFeedItem[]> => {
  try {
    const res = await safeFetch(`${API_BASE_URL}/api/public/council-alerts`);
    return await res.json();
  } catch (e) {
    return [
      {
        title: "System: Connect Backend for Live Council Feeds",
        link: "#",
        source: "System",
        published: "Now",
        summary: "To see real council RSS feeds, please ensure the Python backend is running."
      }
    ];
  }
};

export const fetchNewsHeadlines = async (): Promise<RssFeedItem[]> => {
  try {
    const res = await safeFetch(`${API_BASE_URL}/api/public/news-headlines`);
    return await res.json();
  } catch (e) {
    return [
      {
        title: "System: Connect Backend for Live News Feeds",
        link: "#",
        source: "System",
        published: new Date().toISOString(),
        summary: "To see real news feeds, please ensure the Python backend is running."
      }
    ];
  }
};

export const fetchDataSources = async (): Promise<DataSource[]> => {
  try {
    const res = await safeFetch(`${API_BASE_URL}/api/public/data-sources`);
    return await res.json();
  } catch (e) {
    return [
      { name: 'NIWA DataHub', status: 'inactive', last_sync: 'Backend Offline' },
      { name: 'OpenWeatherMap', status: OPENWEATHER_API_KEY ? 'active' : 'inactive', last_sync: OPENWEATHER_API_KEY ? 'Live (Client-Side)' : 'Missing Key' },
      { name: 'Regional Councils', status: 'inactive', last_sync: 'Backend Offline' }
    ];
  }
};

export const sendChatMessage = async (message: string): Promise<string> => {
  try {
    const res = await safeFetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    const data = await res.json();
    return data.response;
  } catch (error) {
    if (GOOGLE_API_KEY) {
      try {
         const response = await genAI.models.generateContent({
          model: 'gemini-2.5-flash',
          contents: message,
          config: {
            systemInstruction: "You are the CKICAS Drought Monitor AI Assistant for New Zealand. Provide concise, expert advice on drought risk, rainfall, and soil moisture for NZ farmers. Only base your advice on general knowledge if specific real-time data is unavailable."
          }
        });
        return response.text || "Analysis complete.";
      } catch (geminiError) {
        return "Error connecting to Gemini AI directly.";
      }
    }
    return "I am currently offline. Please check your internet connection or API keys.";
  }
};

export const evaluateTriggers = async (userId: number, weatherData: any): Promise<any> => {
  try {
    const res = await safeFetch(`${API_BASE_URL}/api/triggers/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, weather_data: weatherData })
    });
    return await res.json();
  } catch (e) {
    console.warn("Trigger evaluation failed (backend offline?)", e);
    return null;
  }
};
