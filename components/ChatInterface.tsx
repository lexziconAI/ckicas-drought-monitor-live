import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, DroughtRiskData } from '../types';
import { sendChatMessage, fetchDroughtRisk } from '../services/api';
import { NZ_REGIONS } from '../constants';

interface ChatInterfaceProps {
  selectedRegion: string | null;
  selectedRegionData: DroughtRiskData | null;
  trigger?: number;
  isDataLoaded?: boolean; // New prop to track if initial data is loaded
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ selectedRegion, selectedRegionData, trigger = 0, isDataLoaded = false }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Kia ora! I am your CKICAS drought monitoring assistant. Ask me about drought risks in any NZ region or select a region on the map.',
      timestamp: Date.now(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (selectedRegion && selectedRegionData && trigger > 0) {
      // Build a data-rich prompt with actual metrics
      const prompt = `Analyze the current drought situation for ${selectedRegion} based on this real-time data:

Region: ${selectedRegionData.region}
Risk Level: ${selectedRegionData.risk_level}
Risk Score: ${selectedRegionData.risk_score}/100

Current Metrics:
- Temperature: ${selectedRegionData.factors.temperature || 'N/A'}°C (Anomaly: ${selectedRegionData.factors.temperature_anomaly || 'N/A'}°C)
- Humidity: ${selectedRegionData.extended_metrics?.humidity || selectedRegionData.factors.humidity || 'N/A'}%
- Rainfall (24h forecast): ${selectedRegionData.factors.rainfall_24h || 'N/A'}mm
- Rainfall Deficit: ${selectedRegionData.factors.rainfall_deficit || 'N/A'}mm
- Soil Moisture Index: ${selectedRegionData.factors.soil_moisture_index || 'N/A'}
- Wind Speed: ${selectedRegionData.extended_metrics?.wind_speed || 'N/A'} m/s
- Pressure: ${selectedRegionData.extended_metrics?.pressure || 'N/A'} hPa
- Weather: ${selectedRegionData.extended_metrics?.weather_main || selectedRegionData.weather_description || 'N/A'}

Data Source: ${selectedRegionData.data_source || 'OpenWeather'}
Last Updated: ${selectedRegionData.last_updated || selectedRegionData.timestamp}

Please provide a concise analysis of the drought risk, what the data indicates, and any recommendations for this region.`;

      handleSend(prompt);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trigger]);

  const handleSend = async (text: string = input) => {
    if (!text.trim() || isTyping) return;

    // Check if initial data has loaded
    if (!isDataLoaded) {
      const waitMsg: ChatMessage = {
        role: 'assistant',
        content: 'Please wait a few moments while the regional drought data finishes loading. The system is currently gathering real-time weather information from all New Zealand regions.',
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, waitMsg]);
      return;
    }

    const userMsg: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      // Detect if the user is asking about a specific region
      const detectedRegion = NZ_REGIONS.find(region =>
        text.toLowerCase().includes(region.name.toLowerCase())
      );

      console.log('🔍 Region detection:', {
        userText: text,
        detectedRegion: detectedRegion?.name || 'None',
        selectedRegionData: selectedRegionData?.region || 'None'
      });

      let enrichedPrompt = text;

      // If a region is mentioned and we don't have its data already, fetch it
      if (detectedRegion && (!selectedRegionData || selectedRegionData.region !== detectedRegion.name)) {
        try {
          console.log('📡 Fetching data for:', detectedRegion.name);
          const regionData = await fetchDroughtRisk(detectedRegion.lat, detectedRegion.lon);
          console.log('✅ Data fetched:', regionData);

          // Enrich the prompt with real-time data
          enrichedPrompt = `${text}

Here is the current real-time data for ${regionData.region}:

Risk Level: ${regionData.risk_level}
Risk Score: ${regionData.risk_score}/100

Current Metrics:
- Temperature: ${regionData.factors.temperature || 'N/A'}°C (Anomaly: ${regionData.factors.temperature_anomaly || 'N/A'}°C)
- Humidity: ${regionData.extended_metrics?.humidity || regionData.factors.humidity || 'N/A'}%
- Rainfall (24h forecast): ${regionData.factors.rainfall_24h || 'N/A'}mm
- Rainfall Deficit: ${regionData.factors.rainfall_deficit || 'N/A'}mm
- Soil Moisture Index: ${regionData.factors.soil_moisture_index || 'N/A'}
- Wind Speed: ${regionData.extended_metrics?.wind_speed || 'N/A'} m/s
- Pressure: ${regionData.extended_metrics?.pressure || 'N/A'} hPa
- Weather: ${regionData.extended_metrics?.weather_main || regionData.weather_description || 'N/A'}

Data Source: ${regionData.data_source || 'OpenWeather'}
Last Updated: ${regionData.last_updated || regionData.timestamp}

Please analyze this data and provide a detailed response to the user's question.`;
        } catch (fetchError) {
          console.error('Error fetching region data:', fetchError);
          // Continue with original prompt if fetch fails
        }
      } else if (selectedRegionData && text.toLowerCase().includes(selectedRegionData.region.toLowerCase())) {
        // Use already selected region data
        enrichedPrompt = `${text}

Here is the current real-time data for ${selectedRegionData.region}:

Risk Level: ${selectedRegionData.risk_level}
Risk Score: ${selectedRegionData.risk_score}/100

Current Metrics:
- Temperature: ${selectedRegionData.factors.temperature || 'N/A'}°C (Anomaly: ${selectedRegionData.factors.temperature_anomaly || 'N/A'}°C)
- Humidity: ${selectedRegionData.extended_metrics?.humidity || selectedRegionData.factors.humidity || 'N/A'}%
- Rainfall (24h forecast): ${selectedRegionData.factors.rainfall_24h || 'N/A'}mm
- Rainfall Deficit: ${selectedRegionData.factors.rainfall_deficit || 'N/A'}mm
- Soil Moisture Index: ${selectedRegionData.factors.soil_moisture_index || 'N/A'}
- Wind Speed: ${selectedRegionData.extended_metrics?.wind_speed || 'N/A'} m/s
- Pressure: ${selectedRegionData.extended_metrics?.pressure || 'N/A'} hPa
- Weather: ${selectedRegionData.extended_metrics?.weather_main || selectedRegionData.weather_description || 'N/A'}

Data Source: ${selectedRegionData.data_source || 'OpenWeather'}
Last Updated: ${selectedRegionData.last_updated || selectedRegionData.timestamp}

Please analyze this data and provide a detailed response to the user's question.`;
      }

      console.log('📤 Sending prompt to backend:', enrichedPrompt.substring(0, 200) + '...');
      const responseText = await sendChatMessage(enrichedPrompt);
      console.log('📥 Received response:', responseText.substring(0, 200) + '...');
      const botMsg: ChatMessage = {
        role: 'assistant',
        content: responseText,
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (error) {
      const errorMsg: ChatMessage = {
        role: 'assistant',
        content: "Sorry, I'm having trouble connecting to the drought analysis engine. Please ensure the backend is running on port 9101.",
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  // Helper to render simple Markdown (Bold, Italic, and Lists)
  const renderMessageContent = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, i) => {
      // Check for bullet points
      let isList = false;
      let cleanLine = line;

      if (line.trim().startsWith('- ')) {
        isList = true;
        cleanLine = line.trim().substring(2);
      } else if (line.trim().startsWith('* ') && !line.trim().endsWith('*')) {
        // Only treat as bullet if it doesn't look like a full italic sentence
        isList = true;
        cleanLine = line.trim().substring(2);
      }

      // Parse bold syntax (**text**)
      const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
      const formattedLine = parts.map((part, j) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={j} className="font-bold text-slate-900">{part.slice(2, -2)}</strong>;
        }
        
        // Parse italics syntax (*text*)
        const italicParts = part.split(/(\*.*?\*)/g);
        return italicParts.map((subPart, k) => {
          if (subPart.startsWith('*') && subPart.endsWith('*') && subPart.length > 2) {
            return <em key={`${j}-${k}`} className="italic text-slate-700">{subPart.slice(1, -1)}</em>;
          }
          return <span key={`${j}-${k}`}>{subPart}</span>;
        });
      });

      if (isList) {
        return (
          <div key={i} className="flex items-start gap-2 ml-3 mt-1 mb-1">
            <span className="text-slate-400 mt-1.5 text-[10px]">•</span>
            <div className="flex-1 leading-relaxed">{formattedLine}</div>
          </div>
        );
      }

      // Standard paragraph (only add margin if it's not the first line)
      return (
        <p key={i} className={`leading-relaxed ${i > 0 ? 'mt-2' : ''}`}>
          {formattedLine}
        </p>
      );
    });
  };

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-xl border border-slate-200 shadow-md overflow-hidden">
      <div className="bg-slate-800 text-white p-4 flex justify-between items-center">
        <div>
          <h2 className="font-bold text-lg">Drought Assistant</h2>
          <p className="text-xs text-slate-400">Powered by Groq Llama 3.3 70B</p>
        </div>
        <div className={`w-2 h-2 rounded-full ${isTyping ? 'bg-green-400 animate-pulse' : 'bg-slate-500'}`}></div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] p-3 rounded-lg text-sm ${
              msg.role === 'user' 
                ? 'bg-blue-600 text-white rounded-br-none' 
                : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-sm'
            }`}>
              {renderMessageContent(msg.content)}
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-200 p-3 rounded-lg rounded-bl-none shadow-sm flex space-x-1">
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms'}}></div>
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms'}}></div>
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms'}}></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t border-slate-200">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about rainfall, soil moisture, or risk..."
            className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            disabled={isTyping}
          />
          <button
            onClick={() => handleSend()}
            disabled={isTyping || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white px-4 py-2 rounded-lg font-medium transition-colors text-sm"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;