export interface TrcFallbackSite {
  name: string;
  latitude: number;
  longitude: number;
  region: string;
  stationType: 'river' | 'weather';
}

export const TRC_SITES_FALLBACK: TrcFallbackSite[] = [
  { name: 'Patea at Skinner Rd', latitude: -39.578, longitude: 174.286, region: 'Taranaki', stationType: 'river' },
  { name: 'Patea at Stratford', latitude: -39.340, longitude: 174.284, region: 'Taranaki', stationType: 'river' },
  { name: 'Waitara at Bertrand Rd', latitude: -38.993, longitude: 174.243, region: 'Taranaki', stationType: 'river' },
  { name: 'Waitara at Purangi Bridge', latitude: -39.048, longitude: 174.510, region: 'Taranaki', stationType: 'river' },
  { name: 'Waiwhakaiho at Egmont Village', latitude: -39.295, longitude: 174.087, region: 'Taranaki', stationType: 'river' },
  { name: 'Waiwhakaiho at Hillsborough', latitude: -39.115, longitude: 174.090, region: 'Taranaki', stationType: 'river' },
  { name: 'Kapuni at Normanby Rd', latitude: -39.438, longitude: 174.283, region: 'Taranaki', stationType: 'river' },
  { name: 'Kapuni at SH45', latitude: -39.491, longitude: 174.231, region: 'Taranaki', stationType: 'river' },
  { name: 'Kaupokonui at Glenn Rd', latitude: -39.423, longitude: 174.235, region: 'Taranaki', stationType: 'river' },
  { name: 'Kaupokonui at Opunake Rd', latitude: -39.350, longitude: 174.339, region: 'Taranaki', stationType: 'river' },
  { name: 'Manganui at SH3 Midhirst', latitude: -39.308, longitude: 174.229, region: 'Taranaki', stationType: 'river' },
  { name: 'Manganui at Everett Park', latitude: -39.253, longitude: 174.248, region: 'Taranaki', stationType: 'river' },
  { name: 'Stony at Mangatete Bridge', latitude: -39.258, longitude: 174.010, region: 'Taranaki', stationType: 'river' },
  { name: 'Hangatahua at Okato', latitude: -39.200, longitude: 173.883, region: 'Taranaki', stationType: 'river' },
  { name: 'Oakura at Victoria Rd', latitude: -39.143, longitude: 174.019, region: 'Taranaki', stationType: 'river' },
  { name: 'Urenui at Okoki Rd', latitude: -38.986, longitude: 174.369, region: 'Taranaki', stationType: 'river' },
  { name: 'Tongaporutu', latitude: -38.804, longitude: 174.633, region: 'Taranaki', stationType: 'river' },
  { name: 'Waitotara at Township', latitude: -39.748, longitude: 174.615, region: 'Taranaki', stationType: 'river' },
  { name: 'Whenuakura at Nicholson Rd', latitude: -39.706, longitude: 174.655, region: 'Taranaki', stationType: 'river' },
  { name: 'North Egmont at Visitors Centre', latitude: -39.280, longitude: 174.080, region: 'Taranaki', stationType: 'weather' },
  { name: "Dawson Falls", latitude: -39.329, longitude: 174.113, region: 'Taranaki', stationType: 'weather' },
  { name: 'New Plymouth AWS', latitude: -39.054, longitude: 174.074, region: 'Taranaki', stationType: 'weather' },
  { name: 'Eltham Weather Station', latitude: -39.429, longitude: 174.302, region: 'Taranaki', stationType: 'weather' },
  { name: 'Stratford EWS', latitude: -39.333, longitude: 174.283, region: 'Taranaki', stationType: 'weather' },
  { name: 'Normanby AWS', latitude: -39.442, longitude: 174.283, region: 'Taranaki', stationType: 'weather' }
];
