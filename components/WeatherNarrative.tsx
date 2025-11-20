import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../constants';

interface KaitiakiWaiData {
  title: string;
  tagline: string;
  narrative: string;
  mode: 'stability' | 'tension' | 'acceleration' | 'crisis';
  risk_score: number;
  trajectory: 'improving' | 'stable' | 'worsening';
  updated_at: string;
  sentences?: string[];
}

const WeatherNarrative: React.FC = () => {
  const [data, setData] = useState<KaitiakiWaiData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadNarrative = async () => {
      try {
        console.log('WeatherNarrative: Fetching narrative...');
        const response = await fetch(`${API_BASE_URL}/api/public/weather-narrative`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const narrativeData = await response.json();
        console.log('WeatherNarrative: Data loaded:', narrativeData);

        // Split narrative into sentences for scrolling
        const sentences = narrativeData.narrative
          .split(/(?<=[.!?])\s+/)
          .filter((s: string) => s.trim().length > 0);

        setData({ ...narrativeData, sentences });
        setError(null);
        setIsLoading(false);
      } catch (error) {
        console.error('WeatherNarrative: Failed to load:', error);
        setError(error instanceof Error ? error.message : 'Unknown error');
        setIsLoading(false);
      }
    };

    loadNarrative();

    // Refresh every 30 minutes
    const interval = setInterval(loadNarrative, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    console.error('WeatherNarrative: Error state:', error);
    return null;
  }

  if (isLoading) {
    console.log('WeatherNarrative: Loading...');
    return null;
  }

  if (!data) {
    console.log('WeatherNarrative: No data');
    return null;
  }

  console.log('WeatherNarrative: Rendering with data:', data.narrative.substring(0, 50));

  const sentences = data.sentences || [data.narrative];

  const modeColors = {
    stability: 'from-emerald-950 via-teal-900 to-emerald-950 border-emerald-800',
    tension: 'from-amber-950 via-yellow-900 to-amber-950 border-amber-800',
    acceleration: 'from-orange-950 via-red-900 to-orange-950 border-orange-800',
    crisis: 'from-red-950 via-rose-900 to-red-950 border-red-800'
  };

  const trajectoryIcons = {
    improving: '↗',
    stable: '→',
    worsening: '↘'
  };

  return (
    <div className={`w-full bg-gradient-to-r ${modeColors[data.mode || 'stability']} text-white overflow-hidden py-4 px-6 flex items-center gap-4 border-t border-b shadow-xl transition-colors duration-1000`}>
      <div className="flex flex-col items-start whitespace-nowrap min-w-[140px]">
        <div className="flex items-center gap-2 text-white/90">
          <span className="text-lg">{trajectoryIcons[data.trajectory || 'stable']}</span>
          <span className="text-sm font-bold uppercase tracking-widest">{data.title || 'Kaitiaki Wai'}</span>
        </div>
        <span className="text-[10px] text-white/60 italic">{data.tagline || 'Stories of stewardship'}</span>
      </div>

      <div className="flex-1 overflow-hidden relative h-8">
        <div className="animate-narrative-scroll whitespace-nowrap absolute flex gap-8 items-center">
          {sentences.concat(sentences).map((sentence, idx) => (
            <span key={idx} className="text-sm leading-relaxed text-slate-100 italic font-light tracking-wide flex items-center gap-8">
              {sentence}
              <span className="text-white/30">•</span>
            </span>
          ))}
        </div>
      </div>

      <div className="flex flex-col items-end gap-0.5 text-xs text-white/60 whitespace-nowrap min-w-[100px]">
        <div className="flex items-center gap-2">
          <span className="uppercase tracking-wider font-semibold text-[10px]">{data.mode || 'STABILITY'}</span>
          <span className={`w-1.5 h-1.5 rounded-full ${data.mode === 'crisis' ? 'bg-red-500 animate-pulse' : 'bg-emerald-400'}`}></span>
        </div>
        <span className="text-[10px]">Risk Score {data.risk_score || 50}/100</span>
      </div>

      <style>{`
        .animate-narrative-scroll {
          animation: narrative-scroll 120s linear infinite;
        }
        @keyframes narrative-scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-narrative-scroll:hover {
          animation-play-state: paused;
        }
      `}</style>
    </div>
  );
};

export default WeatherNarrative;
