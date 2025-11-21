import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../constants';

interface CouncilAlert {
  title: string;
  source: string;
  link: string;
  severity: 'critical' | 'warning' | 'info';
  date: string;
  region: string;
}

const CouncilAlerts: React.FC = () => {
  const [alerts, setAlerts] = useState<CouncilAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    
    const loadAlerts = async () => {
      try {
        // Add 15-second timeout
        const controller = new AbortController();
        const fetchTimeoutId = setTimeout(() => controller.abort(), 15000);
        
        const response = await fetch(`${API_BASE_URL}/api/public/council-alerts`, {
          signal: controller.signal
        });
        
        clearTimeout(fetchTimeoutId);
        
        if (!response.ok) throw new Error('Failed to fetch');
        
        const data = await response.json();
        setAlerts(data);
        setIsLoading(false);
      } catch (error) {
        console.warn("CouncilAlerts: Backend unavailable, showing loading state");
        // Keep loading state - no mock data fallback
        setIsLoading(false);
        setAlerts([]);
      }
    };

    loadAlerts();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []);

  // Show loading state while fetching (no mock data fallback)
  if (isLoading || alerts.length === 0) {
    return (
      <div className="w-full bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white overflow-hidden py-3 px-4 flex items-center gap-4 border-t border-b border-slate-700 shadow-lg">
        <div className="flex items-center gap-2.5 text-orange-400 whitespace-nowrap">
          <svg className="w-4 h-4 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
          </svg>
          <span className="text-xs font-bold uppercase tracking-wider">Water Alerts</span>
        </div>
        <div className="flex-1 overflow-hidden relative h-7">
          <div className="animate-alerts-loading whitespace-nowrap absolute flex gap-6 items-center">
            {[...Array(8)].map((_, idx) => (
              <span key={idx} className="text-sm text-slate-400 italic tracking-widest">
                ......loading......
              </span>
            ))}
          </div>
        </div>
        <div className="text-xs text-slate-500 whitespace-nowrap">
          <span className="animate-pulse">{isLoading ? 'Checking alerts...' : 'No active alerts'}</span>
        </div>
        <style>{`
          .animate-alerts-loading {
            animation: alerts-loading 6s linear infinite;
          }
          @keyframes alerts-loading {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
          }
        `}</style>
      </div>
    );
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-400';
      case 'warning': return 'text-orange-400';
      case 'info': return 'text-blue-400';
      default: return 'text-slate-400';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return (
          <svg className="w-3.5 h-3.5 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'info':
        return (
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div className="w-full bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white overflow-hidden py-3 px-4 flex items-center gap-4 border-t border-b border-slate-700 shadow-lg">
      <div className="flex items-center gap-2.5 text-orange-400 whitespace-nowrap">
        <svg className="w-4 h-4 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
        </svg>
        <span className="text-xs font-bold uppercase tracking-wider">Water Alerts</span>
      </div>

      <div className="flex-1 overflow-hidden relative h-7">
        <div className="animate-marquee whitespace-nowrap absolute flex gap-8 items-center">
          {alerts.concat(alerts).map((alert, idx) => (
            <a
              key={idx}
              href={alert.link}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-slate-200 hover:text-white hover:underline transition-colors flex items-center gap-2.5 group"
            >
              <span className={`${getSeverityColor(alert.severity)} flex items-center gap-1`}>
                {getSeverityIcon(alert.severity)}
              </span>
              <span className="text-slate-400 text-xs font-medium">[{alert.region}]</span>
              <span className="group-hover:text-white">{alert.title}</span>
              <span className="text-slate-500 text-xs">• {alert.date}</span>
            </a>
          ))}
        </div>
      </div>

      <div className="text-xs text-slate-500 whitespace-nowrap hidden md:block">
        {alerts.length} active {alerts.length === 1 ? 'alert' : 'alerts'}
      </div>

      <style>{`
        .animate-marquee {
          animation: marquee 50s linear infinite;
        }
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-marquee:hover {
          animation-play-state: paused;
        }
      `}</style>
    </div>
  );
};

export default CouncilAlerts;
