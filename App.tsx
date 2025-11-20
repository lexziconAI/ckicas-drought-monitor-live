import 'leaflet/dist/leaflet.css';
import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import DroughtMap from './components/DroughtMap';
import ChatInterface from './components/ChatInterface';
import StatusCard from './components/StatusCard';
import HistoricalChart from './components/HistoricalChart';
import CouncilAlerts from './components/CouncilAlerts';
import NewsTicker from './components/NewsTicker';
import WeatherNarrative from './components/WeatherNarrative';
import QuickStats from './components/QuickStats';
import DataRefreshIndicator from './components/DataRefreshIndicator';
import RegionSearch, { RegionSearchRef } from './components/RegionSearch';
import ShortcutsHelpModal from './components/ShortcutsHelpModal';
import QuickStatsSkeleton from './components/QuickStatsSkeleton';
import WeatherMetricsSkeleton from './components/WeatherMetricsSkeleton';
import HistoricalChartSkeleton from './components/HistoricalChartSkeleton';
import Triggers from './pages/Triggers';
import SystemDynamics from './pages/SystemDynamics';
import TRCMap from './components/TRCMap';
import RainfallExplorer from './components/RainfallExplorer';
import { checkApiHealth, fetchDataSources, fetchForecastTrend, fetchHistoricalData, fetchDroughtRisk, evaluateTriggers } from './services/api';
import { DataSource, DroughtRiskData, HistoricalDataPoint } from './types';
import { NZ_REGIONS } from './constants';
import { toastNotifications } from './utils/toast';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

// Default user ID for trigger evaluation (TODO: Replace with actual authentication)
const DEFAULT_USER_ID = 1;

const Dashboard: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'online' | 'offline' | 'checking' | 'serverless'>('checking');
  const [latency, setLatency] = useState(0);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [selectedRegionData, setSelectedRegionData] = useState<DroughtRiskData | null>(null);
  const [trendData, setTrendData] = useState<HistoricalDataPoint[]>([]);
  const [loadingTrend, setLoadingTrend] = useState(false);
  const [chartMode, setChartMode] = useState<'forecast' | 'history'>('forecast');
  const [chatTrigger, setChatTrigger] = useState<number>(0);
  const [allRegionsData, setAllRegionsData] = useState<DroughtRiskData[]>([]);
  const [lastDataUpdate, setLastDataUpdate] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showShortcutsModal, setShowShortcutsModal] = useState(false);

  // Ref for RegionSearch component
  const regionSearchRef = useRef<RegionSearchRef>(null);

  // Helper function to extract weather data for trigger evaluation
  const extractWeatherData = (regionData: DroughtRiskData) => {
    return {
      temperature: regionData.factors.temperature_anomaly + 15.0, // Add baseline temp back
      rainfall: regionData.factors.rainfall_deficit,
      humidity: regionData.extended_metrics?.humidity || 0,
      wind_speed: regionData.extended_metrics?.wind_speed || 0
    };
  };

  // Helper function to evaluate triggers for current weather conditions
  const evaluateTriggersForRegions = async (regionsData: DroughtRiskData[]) => {
    if (regionsData.length === 0) return;

    // Use the first region's weather data as a representative sample
    // In a production app, you might want to evaluate for the user's specific region
    const weatherData = extractWeatherData(regionsData[0]);

    try {
      const evaluation = await evaluateTriggers(DEFAULT_USER_ID, weatherData);

      if (evaluation && evaluation.total_alerts > 0) {
        console.log(`[Trigger Evaluation] ${evaluation.total_alerts} alerts triggered at ${evaluation.evaluated_at}`);

        // Show toast notifications
        if (evaluation.total_alerts === 1) {
          const alert = evaluation.alerts[0];
          toastNotifications.triggerFired(alert.trigger.name, alert.trigger.region);
          console.log(`[Alert] ${alert.trigger.name} in ${alert.trigger.region}:`, alert.recommendations);
        } else {
          toastNotifications.multipleTriggersFired(evaluation.total_alerts);
          evaluation.alerts.forEach(alert => {
            console.log(`[Alert] ${alert.trigger.name} in ${alert.trigger.region}:`, alert.recommendations);
          });
        }
      } else if (evaluation) {
        console.log(`[Trigger Evaluation] No alerts triggered at ${evaluation.evaluated_at}`);
      }
    } catch (error) {
      console.error('[Trigger Evaluation] Failed to evaluate triggers:', error);
    }
  };

  useEffect(() => {
    const initSystem = async () => {
      setIsRefreshing(true);
      const health = await checkApiHealth();
      setApiStatus(health.status);
      setLatency(health.latency);

      if (health.status === 'online' || health.status === 'serverless') {
        try {
          const sources = await fetchDataSources();
          setDataSources(sources);

          // Fetch data for all regions to calculate stats
          const regionsData = await Promise.all(
            NZ_REGIONS.map(region => fetchDroughtRisk(region.lat, region.lon))
          );
          setAllRegionsData(regionsData);
          setLastDataUpdate(new Date());

          // Evaluate triggers with current weather data
          await evaluateTriggersForRegions(regionsData);
        } catch (e) {
          console.error("Failed to load sources", e);
        }
      }
      setIsRefreshing(false);
    };

    initSystem();
    const interval = setInterval(initSystem, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRegionSelect = async (data: DroughtRiskData) => {
    setSelectedRegionData(data);
    setLoadingTrend(true);
    setChartMode('forecast'); // Reset to forecast on new region select
    
    // Find the region definition to get lat/lon
    const regionDef = NZ_REGIONS.find(r => r.name === data.region);
    
    if (regionDef) {
      const trends = await fetchForecastTrend(regionDef.lat, regionDef.lon);
      setTrendData(trends);
    } else {
      console.warn(`Could not find coordinates for region: ${data.region}`);
      // Fallback to Wellington if not found, or handle error
      const trends = await fetchForecastTrend(-41.2866, 174.7756);
      setTrendData(trends);
    }
    setLoadingTrend(false);
  };

  const handleChartModeChange = async (mode: 'forecast' | 'history') => {
    if (!selectedRegionData) return;
    
    setChartMode(mode);
    setLoadingTrend(true);
    
    const regionDef = NZ_REGIONS.find(r => r.name === selectedRegionData.region);
    const lat = regionDef ? regionDef.lat : -41.2866;
    const lon = regionDef ? regionDef.lon : 174.7756;

    try {
      if (mode === 'history') {
        const history = await fetchHistoricalData(lat, lon, 90); // 3 months
        setTrendData(history);
      } else {
        const trends = await fetchForecastTrend(lat, lon);
        setTrendData(trends);
      }
    } catch (error) {
      console.error("Failed to switch chart data:", error);
      setTrendData([]);
    } finally {
      setLoadingTrend(false);
    }
  };

  const handleAnalyzeInChat = (data: DroughtRiskData) => {
    // Only trigger chat analysis, do NOT update chart or forecast data
    setChatTrigger(prev => prev + 1);
  };

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    const health = await checkApiHealth();
    setApiStatus(health.status);
    setLatency(health.latency);

    if (health.status === 'online' || health.status === 'serverless') {
      try {
        const sources = await fetchDataSources();
        setDataSources(sources);

        const regionsData = await Promise.all(
          NZ_REGIONS.map(region => fetchDroughtRisk(region.lat, region.lon))
        );
        setAllRegionsData(regionsData);
        setLastDataUpdate(new Date());

        // Evaluate triggers with current weather data
        await evaluateTriggersForRegions(regionsData);

        // Show success toast
        toastNotifications.dataRefreshSuccess();
      } catch (e) {
        console.error("Failed to load sources", e);
        // Show error toast
        toastNotifications.dataRefreshError();
      }
    } else {
      // Show error toast if API is offline
      toastNotifications.dataRefreshError();
    }
    setIsRefreshing(false);
  };

  const handleRegionSearchSelect = async (region: { name: string; lat: number; lon: number; baseRisk: number }) => {
    setLoadingTrend(true);

    try {
      const data = await fetchDroughtRisk(region.lat, region.lon);
      setSelectedRegionData(data);

      const trends = await fetchForecastTrend(region.lat, region.lon);
      setTrendData(trends);

      // Show region loaded toast
      toastNotifications.regionLoaded(region.name);
    } catch (error) {
      console.error(`Failed to load data for ${region.name}:`, error);
    } finally {
      setLoadingTrend(false);
    }
  };

  // Keyboard shortcuts
  useKeyboardShortcuts({
    shortcuts: [
      {
        key: 'r',
        description: 'Refresh data',
        action: () => {
          if (!isRefreshing) {
            handleManualRefresh();
          }
        }
      },
      {
        key: '/',
        description: 'Focus search',
        action: () => {
          regionSearchRef.current?.focus();
        }
      },
      {
        key: 'Escape',
        description: 'Clear search',
        action: () => {
          regionSearchRef.current?.clear();
          setSelectedRegionData(null);
        },
        preventDefault: false
      },
      {
        key: '?',
        description: 'Show shortcuts',
        action: () => {
          setShowShortcutsModal(true);
        }
      }
    ]
  });

  const activeSourcesCount = dataSources.filter(s => s.status === 'active').length;

  // Calculate quick stats from all regions data
  const quickStats = {
    totalRegions: NZ_REGIONS.length,
    regionsInDrought: allRegionsData.filter(r => r.risk_score >= 50).length,
    highestRiskRegion: allRegionsData.length > 0
      ? allRegionsData.reduce((max, r) => r.risk_score > max.risk_score ? r : max, allRegionsData[0]).region
      : 'Loading...',
    nationalAverage: allRegionsData.length > 0
      ? Math.round(allRegionsData.reduce((sum, r) => sum + r.risk_score, 0) / allRegionsData.length)
      : 0
  };

  const getStatusBadge = () => {
    if (apiStatus === 'online') {
      return (
        <div className="flex items-center gap-2 px-3 py-1 bg-green-100 text-green-800 rounded-full">
          <div className="w-2 h-2 rounded-full bg-green-500"></div>
          <span className="font-medium text-xs">System Online ({latency}ms)</span>
        </div>
      );
    } else if (apiStatus === 'serverless') {
       return (
        <div className="flex items-center gap-2 px-3 py-1 bg-blue-100 text-blue-800 rounded-full">
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
          <span className="font-medium text-xs">Live (Serverless Mode)</span>
        </div>
      );
    } else if (apiStatus === 'checking') {
      return (
        <div className="flex items-center gap-2 px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full">
          <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
          <span className="font-medium text-xs">Checking...</span>
        </div>
      );
    } else {
      return (
        <div className="flex items-center gap-2 px-3 py-1 bg-red-100 text-red-800 rounded-full">
          <div className="w-2 h-2 rounded-full bg-red-500"></div>
          <span className="font-medium text-xs">System Offline</span>
        </div>
      );
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img 
              src="/CKICAS_LOGO.png" 
              alt="CKICAS Logo" 
              className="h-14 w-auto object-contain" 
            />
            <h1 className="font-bold text-xl text-slate-900 tracking-tight">CKCIAS <span className="text-slate-500 font-normal">Drought Monitor</span></h1>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <Link
              to="/triggers"
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              Alert Triggers
            </Link>
            <Link
              to="/trc-data"
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
              TRC Sites
            </Link>
            <Link
              to="/rainfall-explorer"
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
            >
              <span className="text-lg leading-none">🌧️</span>
              Rainfall Sim
            </Link>
            <Link
              to="/system-dynamics"
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
            >
              <span className="text-lg leading-none">🌀</span>
              System Dynamics
            </Link>
            <button
              onClick={() => setShowShortcutsModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors group"
              title="View keyboard shortcuts"
            >
              <svg className="w-4 h-4 text-slate-400 group-hover:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
              <span className="hidden sm:inline">Keyboard shortcuts: Press</span>
              <kbd className="px-1.5 py-0.5 text-xs font-semibold text-slate-700 bg-slate-100 border border-slate-300 rounded shadow-sm group-hover:bg-white">?</kbd>
            </button>
            <DataRefreshIndicator
              lastUpdated={lastDataUpdate}
              onRefresh={handleManualRefresh}
              isRefreshing={isRefreshing}
            />
            {getStatusBadge()}
          </div>
        </div>
        <CouncilAlerts />
        <NewsTicker />
        <WeatherNarrative />
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Quick Stats Summary */}
        {allRegionsData.length === 0 ? (
          <QuickStatsSkeleton />
        ) : (
          <QuickStats
            totalRegions={quickStats.totalRegions}
            regionsInDrought={quickStats.regionsInDrought}
            highestRiskRegion={quickStats.highestRiskRegion}
            nationalAverage={quickStats.nationalAverage}
          />
        )}

        {/* Region Search */}
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-700">Find Region</h3>
          </div>
          <RegionSearch ref={regionSearchRef} regions={NZ_REGIONS} onRegionSelect={handleRegionSearchSelect} />
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatusCard
            title="Active Sensors"
            value={activeSourcesCount}
            subtitle={`Total Sources: ${dataSources.length}`}
            status={activeSourcesCount > 0 ? 'success' : 'warning'}
            icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <StatusCard
            title="Nat'l Avg Risk"
            value="42/100"
            subtitle="Moderate Concern"
            status="warning"
            icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
          />
          <StatusCard
            title="AI Model"
            value="Claude Haiku 4.5"
            subtitle="Anthropic"
            status="success"
            icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>}
          />
          <StatusCard
            title="Last Update"
            value="Just now"
            subtitle="Real-time Sync"
            status="neutral"
            icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
        </div>

        {/* Main Interface: Map and Chat */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 flex flex-col gap-6">
            <div className="bg-white p-1 rounded-xl shadow-sm border border-slate-200">
               <DroughtMap onRegionSelect={handleRegionSelect} onAnalyzeInChat={handleAnalyzeInChat} />
            </div>

            {/* Detailed Region Panel (Visible on Selection) */}
            {selectedRegionData && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in-up">
                {/* Extended Metrics */}
                {loadingTrend ? (
                  <WeatherMetricsSkeleton />
                ) : (
                  <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center justify-between">
                      <span>Weather Metrics: {selectedRegionData.region}</span>
                      <span className="text-xs font-normal px-2 py-1 bg-slate-100 rounded text-slate-500">{selectedRegionData.extended_metrics?.weather_main || 'Clear'}</span>
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-slate-50 rounded-lg">
                        <div className="text-xs text-slate-500 mb-1">Wind Speed</div>
                        <div className="text-xl font-bold text-slate-700">{selectedRegionData.extended_metrics?.wind_speed || '--'} <span className="text-xs font-normal">m/s</span></div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg">
                        <div className="text-xs text-slate-500 mb-1">Humidity</div>
                        <div className="text-xl font-bold text-blue-600">{selectedRegionData.extended_metrics?.humidity || '--'} <span className="text-xs font-normal">%</span></div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg">
                        <div className="text-xs text-slate-500 mb-1">Pressure</div>
                        <div className="text-xl font-bold text-slate-700">{selectedRegionData.extended_metrics?.pressure || '--'} <span className="text-xs font-normal">hPa</span></div>
                      </div>
                       <div className="p-3 bg-slate-50 rounded-lg">
                        <div className="text-xs text-slate-500 mb-1">Soil Deficit</div>
                        <div className="text-xl font-bold text-orange-600">{selectedRegionData.factors.rainfall_deficit} <span className="text-xs font-normal">mm</span></div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Historical Graph */}
                <div className="h-[250px] relative">
                  {/* Chart Controls */}
                  <div className="absolute top-4 right-4 z-10 flex bg-slate-100 rounded-lg p-1 border border-slate-200">
                    <button
                      onClick={() => handleChartModeChange('forecast')}
                      className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                        chartMode === 'forecast' 
                          ? 'bg-white text-blue-600 shadow-sm' 
                          : 'text-slate-500 hover:text-slate-700'
                      }`}
                    >
                      7-Day Forecast
                    </button>
                    <button
                      onClick={() => handleChartModeChange('history')}
                      className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                        chartMode === 'history' 
                          ? 'bg-white text-blue-600 shadow-sm' 
                          : 'text-slate-500 hover:text-slate-700'
                      }`}
                    >
                      3-Month History
                    </button>
                  </div>

                  {loadingTrend ? (
                    <HistoricalChartSkeleton />
                  ) : (
                    <HistoricalChart 
                      data={trendData} 
                      regionName={selectedRegionData.region} 
                      title={chartMode === 'history' ? '3-Month Historical Data' : '7-Day Forecast Trend'}
                    />
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="lg:col-span-1">
            <ChatInterface
              selectedRegion={selectedRegionData?.region || null}
              selectedRegionData={selectedRegionData}
              trigger={chatTrigger}
            />
          </div>
        </div>
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 mt-8">
        <div className="max-w-7xl mx-auto px-4 text-center text-slate-500 text-sm">
          <p>&copy; 2025 CKCIAS Drought Monitor. A Vibe Coding Project.</p>
          <p className="mt-1">Worker Army Deployment • Claude Haiku 4.5 Integrated • OpenWeather Forecasts</p>
        </div>
      </footer>

      {/* Keyboard Shortcuts Help Modal */}
      <ShortcutsHelpModal
        isOpen={showShortcutsModal}
        onClose={() => setShowShortcutsModal(false)}
      />
    </div>
  );
};

const App: React.FC = () => {
  return (
    <Router>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/triggers" element={<Triggers />} />
        <Route path="/system-dynamics" element={<SystemDynamics />} />
        <Route path="/trc-data" element={<TRCMap />} />
        <Route path="/rainfall-explorer" element={
          <div className="min-h-screen bg-slate-50">
            <header className="bg-white border-b border-slate-200 shadow-sm">
              <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                    <img src="/CKICAS_LOGO.png" alt="CKICAS Logo" className="h-10 w-auto" />
                    <span className="font-bold text-xl text-slate-900">CKCIAS <span className="text-slate-500 font-normal">Drought Monitor</span></span>
                  </Link>
                </div>
                <Link to="/" className="text-sm font-medium text-slate-600 hover:text-slate-900">← Back to Dashboard</Link>
              </div>
            </header>
            <main className="max-w-7xl mx-auto px-4 py-8">
              <RainfallExplorer />
            </main>
          </div>
        } />
      </Routes>
    </Router>
  );
};

export default App;
