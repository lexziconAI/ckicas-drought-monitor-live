import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import { NZ_REGIONS, RISK_COLORS } from '../constants';
import { fetchDroughtRisk } from '../services/api';
import { DroughtRiskData } from '../types';

// Leaflet CSS is loaded in index.html

interface DroughtMapProps {
  regionsData: DroughtRiskData[];
  onRegionSelect: (data: DroughtRiskData) => void;
  onAnalyzeInChat: (data: DroughtRiskData) => void;
}

const MapController = () => {
  const map = useMap();
  // Force map invalidation to fix rendering issues in some layouts
  useEffect(() => {
    setTimeout(() => {
      map.invalidateSize();
    }, 100);
  }, [map]);
  return null;
};

const DroughtMap: React.FC<DroughtMapProps> = ({ regionsData, onRegionSelect, onAnalyzeInChat }) => {
  const [loading, setLoading] = useState<boolean>(false);

  // Convert array to map for easier lookup
  const regionDataMap = React.useMemo(() => {
    const map: Record<string, DroughtRiskData> = {};
    regionsData.forEach(d => {
      map[d.region] = d;
    });
    return map;
  }, [regionsData]);

  const getRiskColor = (level: string) => {
    return RISK_COLORS[level as keyof typeof RISK_COLORS] || '#94a3b8';
  };

  // Lock map to NZ bounds
  const nzBounds: [[number, number], [number, number]] = [
    [-47.5, 165.0],  // Southwest
    [-33.5, 180.0]   // Northeast
  ];

  return (
    <div className="h-[400px] sm:h-[500px] lg:h-[600px] w-full rounded-xl overflow-hidden border border-slate-200 shadow-md relative bg-slate-100 z-0">
      {/* Loading overlay only if no data at all */}
      {regionsData.length === 0 && (
        <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-white/80 backdrop-blur-sm">
          <div className="flex flex-col items-center space-y-2">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-sm font-medium text-slate-600">Scanning Regions...</span>
          </div>
        </div>
      )}
      
      <MapContainer 
        center={[-41.2, 174.8]} 
        zoom={5} 
        minZoom={5}
        maxBounds={nzBounds}
        maxBoundsViscosity={1.0}
        scrollWheelZoom={false} 
        style={{ height: '100%', width: '100%' }}
      >
        <MapController />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {NZ_REGIONS.map((region) => {
          const riskData = regionDataMap[region.name];
          const color = riskData ? getRiskColor(riskData.risk_level) : '#cbd5e1';
          
          return (
            <CircleMarker
              key={region.name}
              center={[region.lat, region.lon]}
              pathOptions={{ 
                color: color, 
                fillColor: color, 
                fillOpacity: 0.6, 
                weight: 2 
              }}
              radius={20}
              eventHandlers={{
                click: () => {
                  if (riskData) onRegionSelect(riskData);
                },
              }}
            >
              <Popup>
                <div className="p-2 min-w-[200px]">
                  <h3 className="font-bold text-lg mb-1">{region.name}</h3>
                  {riskData ? (
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-slate-500">Risk Score:</span>
                        <span className="font-mono font-bold text-lg" style={{color}}>{riskData.risk_score}</span>
                      </div>
                      <div className="text-xs text-slate-500 border-t pt-2 mt-1">
                        <div>Rainfall Deficit: {riskData.factors.rainfall_deficit} mm</div>
                        <div>Soil Moisture: {riskData.factors.soil_moisture_index}</div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onAnalyzeInChat(riskData);
                        }}
                        className="w-full mt-2 text-xs bg-slate-100 hover:bg-slate-200 py-1 rounded text-slate-700 transition-colors"
                      >
                        Analyze in Chat
                      </button>
                    </div>
                  ) : (
                    <span>Loading data...</span>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
};

export default DroughtMap;