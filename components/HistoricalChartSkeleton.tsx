import React from 'react';

const HistoricalChartSkeleton: React.FC = () => {
  return (
    <div className="overflow-hidden animate-pulse">
      {/* Chart skeleton - matches actual chart h-64 */}
      <div className="h-64 bg-slate-100 rounded-lg flex items-end justify-between gap-2 px-4 pb-4">
        {/* Simulated chart bars with varying heights */}
        <div className="flex flex-col items-center flex-1">
          <div className="w-full bg-slate-200 rounded-t" style={{ height: '60%' }}></div>
        </div>
        <div className="flex flex-col items-center flex-1">
          <div className="w-full bg-slate-200 rounded-t" style={{ height: '75%' }}></div>
        </div>
        <div className="flex flex-col items-center flex-1">
          <div className="w-full bg-slate-200 rounded-t" style={{ height: '45%' }}></div>
        </div>
        <div className="flex flex-col items-center flex-1">
          <div className="w-full bg-slate-200 rounded-t" style={{ height: '90%' }}></div>
        </div>
        <div className="flex flex-col items-center flex-1">
          <div className="w-full bg-slate-200 rounded-t" style={{ height: '55%' }}></div>
        </div>
        <div className="flex flex-col items-center flex-1">
          <div className="w-full bg-slate-200 rounded-t" style={{ height: '70%' }}></div>
        </div>
        <div className="flex flex-col items-center flex-1">
          <div className="w-full bg-slate-200 rounded-t" style={{ height: '50%' }}></div>
        </div>
      </div>

      {/* Legend skeleton */}
      <div className="w-full mt-4 pt-3 border-t border-slate-100">
        <div className="flex items-center gap-4 justify-center">
          <div className="h-3 bg-slate-200 rounded w-24"></div>
          <div className="h-3 bg-slate-200 rounded w-20"></div>
        </div>
      </div>
    </div>
  );
};

export default HistoricalChartSkeleton;
