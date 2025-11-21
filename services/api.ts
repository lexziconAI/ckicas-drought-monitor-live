import { NZ_REGIONS, API_BASE_URL, OPENWEATHER_API_KEY } from '../constants';
import { DroughtRiskData, DataSource, HistoricalDataPoint, RssFeedItem } from '../types';
import { TRC_SITES_FALLBACK } from '../data/trcSitesFallback';

// Helper to suppress connection errors in console but log real issues
const safeFetch = async (url: string, options?: RequestInit, timeoutMs: number = 5000) => {
  try {
    // Add configurable timeout (default 5 seconds)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const res = await fetch(url, {
      ...options,
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      throw new Error(`HTTP_${res.status}`);
    }
    return res;
  } catch (error) {
    const msg = (error as Error).message;
    if (msg.startsWith('HTTP_')) {
      throw error;
    }

    const domError = error as DOMException;
    if (domError?.name === 'AbortError') {
      throw new Error('TIMEOUT');
    }

    throw new Error('CONNECTION_REFUSED');
  }
};

export interface HilltopSite {
  name: string;
  latitude: number;
  longitude: number;
  region: string;
  stationType?: 'river' | 'weather';
}

export const checkApiHealth = async (): Promise<{ status: 'online' | 'offline' | 'serverless', latency: number }> => {
  const start = Date.now();
  try {
    await safeFetch(`${API_BASE_URL}/health`, { method: 'GET' });
    return { status: 'online', latency: Date.now() - start };
  } catch (e) {
    if (OPENWEATHER_API_KEY) {
      return { status: 'serverless', latency: 0 };
    }
    return { status: 'offline', latency: 0 };
  }
};

export const fetchDroughtRisk = async (lat: number, lon: number): Promise<DroughtRiskData> => {
  const startTime = Date.now();
  const region = NZ_REGIONS.find(r => 
    Math.abs(r.lat - lat) < 0.1 && Math.abs(r.lon - lon) < 0.1
  ) || { name: "Unknown Region", lat: 0, lon: 0, baseRisk: 30 };

  try {
    const res = await safeFetch(
      `${API_BASE_URL}/api/public/drought-risk?lat=${lat}&lon=${lon}&region=${encodeURIComponent(region.name)}`,
      undefined,
      12000
    );
    console.log(`[${region.name}] Backend fetch: ${Date.now() - startTime}ms`);
    return await res.json();
  } catch (error) {
    console.warn(`[${region.name}] Backend failed after ${Date.now() - startTime}ms, using OpenWeatherMap`);
    // Failover: Client-Side OpenWeatherMap Call
    try {
       const owmStartTime = Date.now();
       const weatherRes = await fetch(
        `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&appid=${OPENWEATHER_API_KEY}&units=metric`,
        { signal: AbortSignal.timeout(3000) } // 3 second timeout for OWM
      );
      
      console.log(`[${region.name}] OpenWeatherMap fetch: ${Date.now() - owmStartTime}ms`);
      
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
    const res = await safeFetch(
      `${API_BASE_URL}/api/public/forecast-trend?lat=${lat}&lon=${lon}`,
      undefined,
      10000
    );
    return await res.json();
  } catch (e) {
    // No Mock Data - Return Empty Array to signal UI to show "No Data" state
    console.error("Forecast fetch failed:", e);
    return [];
  }
};

export const fetchHistoricalData = async (lat: number, lon: number, days: number = 90): Promise<HistoricalDataPoint[]> => {
  try {
    const res = await safeFetch(
      `${API_BASE_URL}/api/public/history?lat=${lat}&lon=${lon}&days=${days}`,
      undefined,
      10000
    );
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

export const fetchHilltopSites = async (): Promise<{ sites: HilltopSite[]; source: 'live' | 'fallback'; message?: string }> => {
  try {
    const res = await safeFetch(`${API_BASE_URL}/api/public/hilltop/sites`, undefined, 10000);
    const data = await res.json();

    if (Array.isArray(data?.sites) && data.sites.length > 0) {
      const normalizedSites: HilltopSite[] = data.sites.map((site: any) => ({
        name: site.name,
        latitude: site.latitude,
        longitude: site.longitude,
        region: site.region || 'Taranaki',
        stationType: site.stationType
      }));
      return { sites: normalizedSites, source: 'live' };
    }

    return {
      sites: TRC_SITES_FALLBACK,
      source: 'fallback',
      message: 'Live TRC feed returned no sites; showing cached map points.'
    };
  } catch (error) {
    console.warn('TRC Hilltop site fetch failed, using fallback dataset.', error);
    return {
      sites: TRC_SITES_FALLBACK,
      source: 'fallback',
      message: 'Live TRC feed unavailable; displaying cached coordinates instead.'
    };
  }
};

export const sendChatMessage = async (message: string): Promise<string> => {
  try {
    // Use 30-second timeout for chat (LLM calls can be slow)
    const res = await safeFetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    }, 30000);
    const data = await res.json();
    if (!data.response) {
      console.error('Chat response missing "response" field:', data);
      return "Backend returned unexpected response format. Check backend logs.";
    }
    return data.response;
  } catch (error) {
    // Groq Kimi K2 is our primary chat backend - no fallback
    const errorMsg = (error as Error).message;
    console.error('Chat backend connection failed:', errorMsg);

    if (errorMsg === 'CONNECTION_REFUSED') {
      return "Cannot connect to Groq Kimi K2 backend. Please ensure the backend server is running on port 9101.";
    } else if (errorMsg === 'TIMEOUT') {
      return "Groq Kimi K2 backend is taking longer than expected to respond. Please try again in a few seconds.";
    } else if (errorMsg.startsWith('HTTP_')) {
      const status = errorMsg.replace('HTTP_', '');
      return `Backend returned error ${status}. Check backend logs for details.`;
    }
    return `Chat error: ${errorMsg}`;
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
    // Silently fail - this is expected when backend is offline
    // console.debug("Trigger evaluation skipped (backend offline)");
    return null;
  }
};
