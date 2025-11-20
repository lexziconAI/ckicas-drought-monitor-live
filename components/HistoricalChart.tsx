import React from 'react';
import { ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { HistoricalDataPoint } from '../types';

interface HistoricalChartProps {
  data: HistoricalDataPoint[];
  regionName: string;
  title?: string;
}

const HistoricalChart: React.FC<HistoricalChartProps> = ({ data, regionName, title = "7-Day Forecast Trend" }) => {
  return (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 h-full flex flex-col overflow-visible relative z-0">
      <div className="mb-3 flex justify-between items-start">
        <div>
          <h3 className="font-bold text-lg text-slate-800">{title}</h3>
          <p className="text-xs text-slate-500">Conditions for {regionName}</p>
        </div>
        
        {/* Custom Legend / Key */}
        <div className="flex gap-4 text-[10px] mr-32 bg-slate-50 p-1.5 rounded-lg border border-slate-100">
           <div className="flex flex-col gap-1">
              <span className="text-slate-400 font-semibold uppercase tracking-wider text-[9px]">Left Axis (%)</span>
              <div className="flex gap-2">
                 <div className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-300 rounded-sm"></span><span className="text-slate-600">Soil</span></div>
                 <div className="flex items-center gap-1"><span className="w-2 h-2 bg-red-300 rounded-sm"></span><span className="text-slate-600">Risk</span></div>
                 <div className="flex items-center gap-1"><span className="w-3 h-0.5 border-t-2 border-dashed border-sky-500"></span><span className="text-slate-600">Rain</span></div>
              </div>
           </div>
           <div className="w-px bg-slate-200"></div>
           <div className="flex flex-col gap-1">
              <span className="text-orange-400 font-semibold uppercase tracking-wider text-[9px]">Right Axis (°C)</span>
              <div className="flex items-center gap-1"><span className="w-3 h-0.5 bg-orange-500 rounded-full"></span><span className="text-slate-600">Temp</span></div>
           </div>
        </div>
      </div>

      <div className="flex-1 pb-2" style={{ minHeight: '180px', maxHeight: '220px' }}>
        {(!data || data.length === 0) ? (
          <div className="h-full w-full flex items-center justify-center bg-slate-50 rounded-lg border border-dashed border-slate-300">
            <p className="text-slate-400 text-sm font-medium">[No Data Available]</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={data}
              margin={{
                top: 5,
                right: 0,
                left: -10,
                bottom: 5,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fontSize: 11, fill: '#64748b'}} dy={5} />
              
              {/* Left Axis: 0-100 for Risk, Soil, Rain Prob */}
              <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{fontSize: 11, fill: '#64748b'}} domain={[0, 100]} />
              
              {/* Right Axis: Temperature */}
              <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{fontSize: 11, fill: '#f97316'}} unit="°" domain={['auto', 'auto']} />
              
              <Tooltip
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', zIndex: 50 }}
                labelStyle={{ fontWeight: 'bold', color: '#334155' }}
                allowEscapeViewBox={{ x: true, y: true }}
              />
              {/* Legend removed - moved to header */}
              
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

              {/* Lines for specific metrics */}
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
        )}
      </div>
    </div>
  );
};

export default HistoricalChart;
