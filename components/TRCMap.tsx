import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polygon } from 'react-leaflet';
import L from 'leaflet';
import taranakiGeoJSON from '../data/taranaki.json';
import { API_BASE_URL } from '../constants';

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

interface Site {
  name: string;
  latitude: number;
  longitude: number;
  region: string;
}

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
      
      // Helper to fetch specific property
      const fetchProperty = async (property: string) => {
        const url = new URL("https://extranet.trc.govt.nz/getdata/merged.hts");
        url.searchParams.set("Service", "SOS");
        url.searchParams.set("Request", "GetObservation");
        url.searchParams.set("FeatureOfInterest", site.name);
        url.searchParams.set("ObservedProperty", property);
        
        const response = await fetch(url.toString());
        if (!response.ok) throw new Error("Network response was not ok");
        return await response.text();
      };

      try {
        // Try Flow first
        let xmlText = await fetchProperty("Flow");
        let data = parseWaterML2(xmlText);

        // If no flow data, try Rainfall
        if (!data.points.length) {
           xmlText = await fetchProperty("Rainfall");
           data = parseWaterML2(xmlText);
        }

        if (data.points.length > 0) {
          const latest = data.points[data.points.length - 1];
          setPopupData({
            value: latest.value.toFixed(3),
            units: data.units,
            time: new Date(latest.time).toLocaleString('en-NZ')
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
    <div className="min-w-[250px]">
      <h3 className="font-bold text-lg border-b pb-1 mb-2">{site.name}</h3>
      
      {loading ? (
        <div className="text-sm text-slate-500">Loading live data...</div>
      ) : popupData?.error ? (
        <div className="text-sm text-red-500">{popupData.error}</div>
      ) : popupData ? (
        <div className="bg-slate-50 p-2 rounded border">
          <div className="text-xs text-slate-500 mb-1">Latest Reading</div>
          <div className="text-2xl font-bold text-blue-600">
            {popupData.value} 
            <span className="text-sm font-normal text-slate-600 ml-1">{popupData.units}</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            {popupData.time}
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

  useEffect(() => {
    const fetchSites = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/public/hilltop/sites`);
        if (!response.ok) throw new Error('Failed to fetch sites');
        const data = await response.json();
        setSites(data.sites);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
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
        <div>
          <h1 className="text-xl font-bold text-slate-800">Taranaki Environmental Monitoring</h1>
          <p className="text-sm text-slate-500">Real-time data from {sites.length} TRC Hilltop sites</p>
        </div>
        <div className="text-xs text-slate-400">
          Click a marker to view live telemetry
        </div>
      </div>
      
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
