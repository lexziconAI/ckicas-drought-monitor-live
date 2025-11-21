import React from 'react';
import { ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { HistoricalDataPoint } from '../types';

interface HistoricalChartProps {
  data: HistoricalDataPoint[];
  regionName: string;
  title?: string;
}

const HistoricalChart: React.FC<HistoricalChartProps> = ({ data, regionName, title = "7-Day Forecast Trend" }) => {
  // Early return for no data
  if (!data || data.length === 0) {
    return (
      <div className="h-64 w-full flex items-center justify-center bg-slate-50 rounded-lg border border-dashed border-slate-300">
        <p className="text-slate-400 text-sm font-medium">[No Data Available]</p>
      </div>
    );
  }

  return (
    <div>
      {/* Chart Container - CRITICAL: h-64 (256px) prevents infinite scroll */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data}
            margin={{
              top: 10,
              right: 20,
              left: 0,
              bottom: 25,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: '#64748b' }}
              dy={8}
              height={40}
            />

            {/* Left Axis: 0-100 for Risk, Soil, Rain Prob */}
            <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} domain={[0, 100]} />

            {/* Right Axis: Temperature */}
            <YAxis
              yAxisId="right"
              orientation="right"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: '#f97316' }}
              unit="°"
              domain={['auto', 'auto']}
            />

            <Tooltip
              contentStyle={{
                borderRadius: '8px',
                border: 'none',
                boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'
              }}
              labelStyle={{ fontWeight: 'bold', color: '#334155' }}
            />

            {/* Background Areas */}
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="soil_moisture"
              name="Soil Moisture"
              stackId="1"
              stroke="#3b82f6"
              fill="#93c5fd"
              fillOpacity={0.6}
            />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="risk_score"
              name="Drought Risk"
              stackId="1"
              stroke="#ef4444"
              fill="#fca5a5"
              fillOpacity={0.6}
            />

            {/* Lines */}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="rain_probability"
              name="Rain Prob %"
              stroke="#0ea5e9"
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={false}
            />

            <Line
              yAxisId="right"
              type="monotone"
              dataKey="temp"
              name="Temp (°C)"
              stroke="#f97316"
              strokeWidth={2}
              dot={{ r: 3, fill: '#f97316' }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Legend - Below chart */}
      <div className="w-full mt-4 pt-3 border-t border-slate-100">
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-[10px]">
          {/* Left Axis Group */}
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-semibold uppercase tracking-wider text-[9px]">
              Scale 0-100%:
            </span>
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 bg-blue-300 rounded-sm"></span>
              <span className="text-slate-600">Soil</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 bg-red-300 rounded-sm"></span>
              <span className="text-slate-600">Risk</span>
            </div>
            <div className="flex items-center gap-1">
              <svg width="12" height="2" className="text-sky-500">
                <line x1="0" y1="1" x2="12" y2="1" stroke="currentColor" strokeWidth="2" strokeDasharray="2 2" />
              </svg>
              <span className="text-slate-600">Rain %</span>
            </div>
          </div>

          {/* Divider */}
          <div className="hidden sm:block w-px h-4 bg-slate-200"></div>

          {/* Right Axis Group */}
          <div className="flex items-center gap-2">
            <span className="text-orange-400 font-semibold uppercase tracking-wider text-[9px]">
              Temperature (°C):
            </span>
            <div className="flex items-center gap-1">
              <svg width="12" height="2" className="text-orange-500">
                <line x1="0" y1="1" x2="12" y2="1" stroke="currentColor" strokeWidth="2" />
              </svg>
              <span className="text-slate-600">Temp</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HistoricalChart;
