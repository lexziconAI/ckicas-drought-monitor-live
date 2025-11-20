import { Region } from './types';

export const API_BASE_URL = 'http://localhost:9101';

// FALLBACK KEYS (Used when backend is offline)
export const GOOGLE_API_KEY = 'AIzaSyCFe1c5oJi9D8gSm5b8InhvoIydmdDj9NE';
export const OPENWEATHER_API_KEY = 'd7ab6944b5791f6c502a506a6049165f';

export const NZ_REGIONS: Region[] = [
  { name: 'Northland', lat: -35.7, lon: 174.3, baseRisk: 25 },
  { name: 'Auckland', lat: -36.8, lon: 174.7, baseRisk: 15 },
  { name: 'Waikato', lat: -37.7, lon: 175.2, baseRisk: 55 },
  { name: 'Bay of Plenty', lat: -37.7, lon: 176.2, baseRisk: 45 },
  { name: 'Gisborne', lat: -38.6, lon: 178.0, baseRisk: 62 },
  { name: "Hawke's Bay", lat: -39.5, lon: 176.8, baseRisk: 58 },
  { name: 'Taranaki', lat: -39.1, lon: 174.1, baseRisk: 38 },
  { name: 'Manawatu-Wanganui', lat: -40.0, lon: 175.7, baseRisk: 42 },
  { name: 'Wellington', lat: -41.3, lon: 174.8, baseRisk: 28 },
  { name: 'Tasman', lat: -41.3, lon: 173.0, baseRisk: 35 },
  { name: 'Nelson', lat: -41.3, lon: 173.3, baseRisk: 32 },
  { name: 'Marlborough', lat: -41.5, lon: 173.9, baseRisk: 48 },
  { name: 'West Coast', lat: -42.4, lon: 171.2, baseRisk: 20 },
  { name: 'Canterbury', lat: -43.5, lon: 171.2, baseRisk: 65 },
  { name: 'Otago', lat: -45.0, lon: 170.5, baseRisk: 55 },
  { name: 'Southland', lat: -46.4, lon: 168.4, baseRisk: 35 }
];

export const RISK_COLORS = {
  Low: '#22c55e', // green-500
  Medium: '#eab308', // yellow-500
  High: '#f97316', // orange-500
  Critical: '#ef4444', // red-500
};