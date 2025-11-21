import React, { useState, useEffect } from 'react';

const IrrigationEfficiencyOptimizer: React.FC = () => {
  const [hectares, setHectares] = useState(100);
  const [currentEfficiency, setCurrentEfficiency] = useState(70);
  const [targetEfficiency, setTargetEfficiency] = useState(85);
  const [results, setResults] = useState<any>(null);

  useEffect(() => {
    calculateSavings();
  }, [hectares, currentEfficiency, targetEfficiency]);

  const calculateSavings = () => {
    // Realistic NZ irrigation parameters
    // Typical application: 25mm per week during irrigation season
    // This meets crop evapotranspiration needs (5-7mm/day peak)
    const weekly_application_mm = 25;

    // Current water use - inefficient systems need to apply more to deliver same effective amount
    const current_applied_mm = weekly_application_mm;
    const current_effective_mm = current_applied_mm * (currentEfficiency / 100);

    // Target water use - efficient system needs less water for same effective delivery
    const target_applied_mm = current_effective_mm / (targetEfficiency / 100);

    // Savings
    const saved_mm_per_week = current_applied_mm - target_applied_mm;
    const saved_liters_per_week = saved_mm_per_week * hectares * 10000; // 1mm on 1ha = 10,000L
    const annual_saved_liters = saved_liters_per_week * 26; // 26 week season (Oct-Mar in NZ)

    // Cost savings
    // NZ water costs: $0.50-$3/1000L depending on source (bore, river, scheme)
    // Using $1.50/1000L as reasonable average for pumped irrigation
    const cost_per_1000L = 1.5;
    const annual_cost_savings = (annual_saved_liters / 1000) * cost_per_1000L;

    // Typical upgrade costs in NZ
    const upgrade_cost_per_ha = 5000; // NZD per hectare for modern pivot/drip system
    const total_upgrade_cost = upgrade_cost_per_ha * hectares;
    const payback_years = total_upgrade_cost / annual_cost_savings;

    setResults({
      saved_mm_per_week,
      saved_liters_per_week,
      annual_saved_liters,
      annual_cost_savings,
      total_upgrade_cost,
      payback_years,
      efficiency_gain: targetEfficiency - currentEfficiency
    });
  };

  if (!results) return null;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-6">
        <h3 className="text-xl font-bold text-gray-800 mb-2">🚜 Irrigation Efficiency Optimizer</h3>
        <p className="text-sm text-gray-600">
          Calculate water and cost savings from upgrading irrigation systems. Real NZ agriculture data.
        </p>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Farm Size: {hectares} ha
          </label>
          <input
            type="range"
            min="10"
            max="500"
            step="10"
            value={hectares}
            onChange={(e) => setHectares(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>10 ha</span>
            <span>500 ha</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Current Efficiency: {currentEfficiency}%
          </label>
          <input
            type="range"
            min="50"
            max="90"
            step="5"
            value={currentEfficiency}
            onChange={(e) => setCurrentEfficiency(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>50%</span>
            <span>90%</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Target Efficiency: {targetEfficiency}%
          </label>
          <input
            type="range"
            min="60"
            max="95"
            step="5"
            value={targetEfficiency}
            onChange={(e) => setTargetEfficiency(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>60%</span>
            <span>95%</span>
          </div>
        </div>
      </div>

      {/* Results Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-xs text-gray-600 uppercase font-semibold">Water Saved/Week</div>
          <div className="text-2xl font-bold text-blue-600">
            {(results.saved_liters_per_week / 1000).toFixed(0)}k L
          </div>
          <div className="text-xs text-gray-500 mt-1">{results.saved_mm_per_week.toFixed(1)} mm equivalent</div>
        </div>

        <div className="bg-green-50 p-4 rounded-lg">
          <div className="text-xs text-gray-600 uppercase font-semibold">Annual Savings</div>
          <div className="text-2xl font-bold text-green-600">
            ${results.annual_cost_savings.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",")}
          </div>
          <div className="text-xs text-gray-500 mt-1">{(results.annual_saved_liters / 1000000).toFixed(1)}M liters saved</div>
        </div>

        <div className="bg-orange-50 p-4 rounded-lg">
          <div className="text-xs text-gray-600 uppercase font-semibold">Upgrade Cost</div>
          <div className="text-2xl font-bold text-orange-600">
            ${results.total_upgrade_cost.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",")}
          </div>
          <div className="text-xs text-gray-500 mt-1">${(results.total_upgrade_cost / hectares).toFixed(0)}/hectare</div>
        </div>

        <div className={`${results.payback_years <= 5 ? 'bg-green-50' : results.payback_years <= 10 ? 'bg-yellow-50' : 'bg-red-50'} p-4 rounded-lg`}>
          <div className="text-xs text-gray-600 uppercase font-semibold">Payback Period</div>
          <div className={`text-2xl font-bold ${results.payback_years <= 5 ? 'text-green-600' : results.payback_years <= 10 ? 'text-yellow-600' : 'text-red-600'}`}>
            {results.payback_years.toFixed(1)} years
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {results.payback_years <= 5 ? 'Excellent ROI' : results.payback_years <= 10 ? 'Good ROI' : 'Long payback'}
          </div>
        </div>
      </div>

      {/* Efficiency Comparison Bars */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold mb-3">Efficiency Comparison</h4>
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Current System</span>
              <span className="font-semibold">{currentEfficiency}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-orange-500 h-4 rounded-full transition-all duration-300"
                style={{ width: `${currentEfficiency}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Target System</span>
              <span className="font-semibold text-green-600">{targetEfficiency}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-green-500 h-4 rounded-full transition-all duration-300"
                style={{ width: `${targetEfficiency}%` }}
              />
            </div>
          </div>

          <div className="text-center text-sm text-gray-600 pt-2">
            <strong className="text-blue-600">+{results.efficiency_gain}%</strong> efficiency gain
          </div>
        </div>
      </div>

      {/* Technology Options */}
      <div className="bg-gray-50 p-4 rounded-lg mb-4">
        <h4 className="font-semibold text-sm mb-3">Irrigation Technology Guide:</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="bg-white p-3 rounded">
            <strong className="text-orange-600">Border Dyke (60-70%)</strong>
            <p className="text-gray-600 mt-1">Traditional flooding method, lowest efficiency</p>
          </div>
          <div className="bg-white p-3 rounded">
            <strong className="text-yellow-600">Centre Pivot (75-85%)</strong>
            <p className="text-gray-600 mt-1">Good coverage, moderate efficiency</p>
          </div>
          <div className="bg-white p-3 rounded">
            <strong className="text-green-600">Drip/Micro (85-95%)</strong>
            <p className="text-gray-600 mt-1">Highest efficiency, targeted delivery</p>
          </div>
        </div>
      </div>

      {/* Educational Note */}
      <div className="bg-purple-50 p-4 rounded-lg">
        <p className="text-sm text-gray-700">
          <strong>💡 Systems Thinking:</strong> This is a <em>leverage point</em> in the drought system - small changes in irrigation
          efficiency have cascading effects. More efficient irrigation means less water demand, which reduces pressure on aquifers,
          which improves resilience. Notice the <em>investment threshold</em> - systems with good ROI (payback &lt;5 years) are
          economically viable, creating a positive feedback loop where water savings fund further improvements.
        </p>
      </div>
    </div>
  );
};

export default IrrigationEfficiencyOptimizer;
