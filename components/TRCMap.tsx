import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, Polygon } from 'react-leaflet';
import L from 'leaflet';
import taranakiGeoJSON from '../data/taranaki.json';
import { API_BASE_URL } from '../constants';
import { fetchHilltopSites, HilltopSite } from '../services/api';

// Fix for default Leaflet icons in React
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

// Map Configuration
const TARANAKI_CENTER: [number, number] = [-39.3, 174.1];
const TARANAKI_BOUNDS: [[number, number], [number, number]] = [
  [-39.95, 173.2],  // Southwest corner
  [-38.65, 175.3]   // Northeast corner
];
const DEFAULT_ZOOM = 10;

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

type Site = HilltopSite;

// Helper to parse WaterML2 response
const parseWaterML2 = (xmlText: string) => {
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(xmlText, "text/xml");
  
  const points: { time: string; value: number }[] = [];
  const measurements = xmlDoc.getElementsByTagName("wml2:MeasurementTVP");
  
  for (let i = 0; i < measurements.length; i++) {
    const timeElem = measurements[i].getElementsByTagName("wml2:time")[0];
    const valueElem = measurements[i].getElementsByTagName("wml2:value")[0];
    if (timeElem && valueElem) {
      points.push({
        time: timeElem.textContent || "",
        value: parseFloat(valueElem.textContent || "0")
      });
    }
  }
  
  // Try to find units
  let units = "";
  const uomElem = xmlDoc.getElementsByTagName("wml2:uom")[0];
  if (uomElem) {
    units = uomElem.getAttribute("code") || "";
  }
  
  return { points, units };
};

const SitePopup: React.FC<{ site: Site }> = ({ site }) => {
  const [popupData, setPopupData] = useState<{ value?: string; units?: string; time?: string; error?: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);

      // Helper to fetch specific property via backend proxy (avoids CORS)
      const fetchProperty = async (property: string) => {
        const url = `${API_BASE_URL}/api/public/hilltop/data?site=${encodeURIComponent(site.name)}&measurement=${encodeURIComponent(property)}&days=1`;

        const response = await fetch(url);
        if (!response.ok) throw new Error("Network response was not ok");
        return await response.json();
      };

      try {
        // Try Flow first
        let data = await fetchProperty("Flow");

        // If no flow data, try Rainfall
        if (!data.data || data.data.length === 0) {
           data = await fetchProperty("Rainfall");
        }

        if (data.data && data.data.length > 0) {
          const latest = data.data[data.data.length - 1];
          setPopupData({
            value: latest.value.toFixed(3),
            units: data.units || '',
            time: new Date(latest.timestamp).toLocaleString('en-NZ')
          });
        } else {
          setPopupData({ error: "No recent data available" });
        }
      } catch (error) {
        console.error("Error fetching SOS data:", error);
        setPopupData({ error: "Failed to fetch data" });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [site.name]);

  return (
    <div className="min-w-[200px] max-w-[280px]">
      {/* Site Name Header */}
      <div className="border-b pb-1.5 mb-2">
        <h3 className="font-bold text-base text-slate-800 leading-tight">{site.name}</h3>
        <span className="text-[10px] text-slate-400">{site.region}</span>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-slate-500 py-2">
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Loading data...
        </div>
      ) : popupData?.error ? (
        <div className="bg-red-50 rounded p-2">
          <div className="flex items-center gap-1.5 text-red-600 text-xs font-medium">
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Data Unavailable
          </div>
          <div className="text-[10px] text-red-400 mt-0.5">{popupData.error}</div>
        </div>
      ) : popupData ? (
        <div>
          {/* Latest Reading Card */}
          <div className="bg-gradient-to-br from-blue-50 to-slate-50 rounded p-2 border border-blue-100">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">Latest Reading</span>
              <span className="text-[9px] bg-green-100 text-green-600 px-1.5 py-0.5 rounded-full font-medium">Live</span>
            </div>

            {/* Value Display - Optimized for large numbers */}
            <div className="flex items-baseline gap-1">
              <span className="text-xl font-bold text-blue-600 leading-none">
                {popupData.value}
              </span>
              <span className="text-xs text-slate-500 font-medium">
                {popupData.units}
              </span>
            </div>

            {/* Timestamp */}
            <div className="mt-1.5 pt-1.5 border-t border-blue-100">
              <div className="flex items-center gap-1 text-[10px] text-slate-400">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {popupData.time}
              </div>
            </div>
          </div>

          {/* Info Footer */}
          <div className="mt-1.5 flex items-center gap-1 text-[9px] text-slate-400">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            Taranaki Regional Council
          </div>
        </div>
      ) : null}
    </div>
  );
};

const TRCMap: React.FC = () => {
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);

  useEffect(() => {
    const fetchSites = async () => {
      try {
        const { sites: fetchedSites, source, message } = await fetchHilltopSites();
        setSites(fetchedSites);
        if (source === 'fallback' && message) {
          setFallbackNotice(message);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchSites();
  }, []);

  // Taranaki Polygon coordinates (lat, lon) - reversed from GeoJSON (lon, lat)
  const taranakiBoundary = taranakiGeoJSON.features[0].geometry.coordinates[0].map(
    coord => [coord[1], coord[0]] as [number, number]
  );

  if (loading) return <div className="p-8 text-center text-slate-500">Loading Map Data...</div>;
  if (error) return <div className="p-8 text-center text-red-500">Error loading map: {error}</div>;

  return (
    <div className="h-screen w-full flex flex-col">
      <div className="bg-white p-4 shadow-sm z-10 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Link to="/" className="p-2 hover:bg-slate-100 rounded-full transition-colors" title="Back to Dashboard">
            <svg className="w-6 h-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </Link>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Taranaki Environmental Monitoring</h1>
            <p className="text-sm text-slate-500">Real-time data from {sites.length} TRC Hilltop sites</p>
          </div>
        </div>
        <div className="text-xs text-slate-400">
          Click a marker to view live telemetry
        </div>
      </div>

      {fallbackNotice && (
        <div className="bg-amber-50 border-t border-b border-amber-200 text-amber-800 text-xs px-4 py-2 text-center">
          {fallbackNotice}
        </div>
      )}
      
      <div className="flex-1 relative" style={{ height: 'calc(100vh - 80px)', zIndex: 0 }}>
        <MapContainer
          center={TARANAKI_CENTER}
          zoom={DEFAULT_ZOOM}
          maxBounds={TARANAKI_BOUNDS}
          maxBoundsViscosity={1.0}
          minZoom={9}
          maxZoom={15}
          scrollWheelZoom={false}
          style={{ height: '100%', width: '100%' }}
          whenReady={(map) => {
            setTimeout(() => {
                map.target.invalidateSize();
            }, 100);
          }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          {/* Taranaki Region Overlay */}
          <Polygon 
            positions={taranakiBoundary}
            pathOptions={{ color: '#f59e0b', fillColor: '#f59e0b', fillOpacity: 0.1, weight: 2 }} 
          />

          {sites.map((site, idx) => (
            <Marker key={idx} position={[site.latitude, site.longitude]}>
              <Popup autoPan={false} className="leaflet-popup-high-z">
                <SitePopup site={site} />
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
};

export default TRCMap;
