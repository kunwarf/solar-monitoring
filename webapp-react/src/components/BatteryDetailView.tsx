import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { TelemetryData, TelemetryResponse } from '../types/telemetry';
import { generateDemoTelemetry } from '../utils/demoData';
import { ChevronDown } from 'lucide-react';

interface BatteryDetailViewProps {
  inverterId?: string;
  refreshInterval?: number;
}

interface BatteryData {
  power: number;
  voltage: number;
  current: number;
  capacity: number;
  temperature: number;
  soc: number;
  soh: number;
  cellVoltage: {
    highest: number;
    average: number;
    lowest: number;
  };
  cellImbalance: {
    highest: number;
    average: number;
    lowest: number;
  };
}

interface IndividualBatteryData extends BatteryData {
  temperatureMOS: number;
  temperature1: number;
  temperature2: number;
  cycles: number;
  chargeCapacity: number;
}

export const BatteryDetailView: React.FC<BatteryDetailViewProps> = ({
  inverterId = 'senergy1',
  refreshInterval = 5000
}) => {
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [expandedSections, setExpandedSections] = useState<{
    overall: boolean;
    battery1: boolean;
    battery2: boolean;
  }>({
    overall: false,
    battery1: false,
    battery2: false,
  });

  const fetchTelemetry = async () => {
    try {
      const response: TelemetryResponse = await api.get(`/api/now?inverter_id=${inverterId}`);
      setTelemetry(response.now);
      setIsDemoMode(false);
    } catch (err) {
      setTelemetry(generateDemoTelemetry());
      setIsDemoMode(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, refreshInterval);
    return () => clearInterval(interval);
  }, [inverterId, refreshInterval]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg">Loading battery data...</div>
      </div>
    );
  }

  if (!telemetry) {
    return (
      <div className="text-center p-8 text-gray-500">
        No battery data available
      </div>
    );
  }

  // Generate demo battery data
  const generateBatteryData = (): BatteryData => {
    const baseVoltage = telemetry.batt_voltage_v || 53.2;
    const baseCurrent = telemetry.batt_current_a || -0.4;
    const baseSOC = telemetry.batt_soc_pct || 99;
    
    return {
      power: telemetry.batt_power_w || -20,
      voltage: baseVoltage,
      current: baseCurrent,
      capacity: 840,
      temperature: telemetry.batt_temp_c || 35.3,
      soc: baseSOC,
      soh: 100,
      cellVoltage: {
        highest: 3.331,
        average: 3.327,
        lowest: 3.305
      },
      cellImbalance: {
        highest: 0.026,
        average: 0.016,
        lowest: 0.005
      }
    };
  };

  const generateIndividualBatteryData = (batteryNum: number): IndividualBatteryData => {
    const baseData = generateBatteryData();
    const variation = batteryNum === 1 ? 0 : 0.1;
    
    return {
      ...baseData,
      capacity: 280,
      soc: baseData.soc - (batteryNum === 2 ? 1 : 0),
      power: batteryNum === 1 ? 0 : baseData.power,
      current: batteryNum === 1 ? 0 : baseData.current,
      temperature: baseData.temperature + variation,
      temperatureMOS: baseData.temperature + variation,
      temperature1: baseData.temperature - 2.1 + variation,
      temperature2: baseData.temperature - 2.8 + variation,
      cycles: 41,
      chargeCapacity: 276 - (batteryNum === 2 ? 2 : 0),
      cellVoltage: {
        highest: 3.331,
        average: 3.327 - (batteryNum === 2 ? 0.013 : 0),
        lowest: 3.305 + (batteryNum === 1 ? 0.009 : 0)
      },
      cellImbalance: {
        highest: batteryNum === 1 ? 0.017 : 0.026,
        average: 0.016,
        lowest: 0.005
      }
    };
  };

  const overallBattery = generateBatteryData();
  const battery1 = generateIndividualBatteryData(1);
  const battery2 = generateIndividualBatteryData(2);

  const HorizontalBarChart: React.FC<{
    title: string;
    data: { label: string; value: number; color: string }[];
    maxValue: number;
    unit: string;
  }> = ({ title, data, maxValue, unit }) => {
    return (
      <div className="bg-white rounded-lg p-4 shadow-sm">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="space-y-3">
          {data.map((item, index) => {
            const percentage = Math.min((Math.abs(item.value) / maxValue) * 100, 100);
            return (
              <div key={index} className="flex items-center">
                <div className="w-16 text-sm text-gray-600">{item.label}</div>
                <div className="flex-1 mx-4">
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div
                      className={`h-4 rounded-full transition-all duration-300 ${item.color}`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
                <div className="w-20 text-sm font-medium text-right">
                  {item.value.toFixed(1)} {unit}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const BatteryParameter: React.FC<{
    label: string;
    value: string | number;
    unit?: string;
  }> = ({ label, value, unit }) => (
    <div className="flex justify-between py-2 border-b border-gray-100">
      <span className="text-gray-600">{label}:</span>
      <span className="font-medium">
        {value} {unit && <span className="text-gray-500">{unit}</span>}
      </span>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard &gt; Battery</h1>
        {isDemoMode && (
          <div className="text-sm text-orange-600 font-medium">
            🎭 Demo Mode - Using simulated data
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Section - Detailed Data */}
        <div className="space-y-6">
          {/* Overall Battery */}
          <div className="bg-white rounded-lg p-6 shadow-sm">
            <h2 className="text-xl font-semibold mb-4">Overall Battery</h2>
            <div className="space-y-1">
              <BatteryParameter label="Power" value={overallBattery.power} unit="W" />
              <BatteryParameter label="Voltage" value={overallBattery.voltage} unit="V" />
              <BatteryParameter label="Current" value={overallBattery.current} unit="A" />
              <BatteryParameter label="Capacity" value={overallBattery.capacity} unit="Ah" />
              <BatteryParameter label="Temperature" value={overallBattery.temperature} unit="°C" />
              <BatteryParameter label="State of charge" value={overallBattery.soc} unit="%" />
              <BatteryParameter label="State of health" value={overallBattery.soh} unit="%" />
              
              <div className="pt-2">
                <button
                  onClick={() => setExpandedSections(prev => ({ ...prev, overall: !prev.overall }))}
                  className="flex items-center justify-between w-full text-sm font-medium text-gray-700 mb-2 hover:text-gray-900 transition-colors"
                >
                  <span>Cell voltage:</span>
                  <ChevronDown 
                    className={`w-4 h-4 transition-transform duration-300 ${expandedSections.overall ? 'rotate-180' : ''}`}
                  />
                </button>
                <div 
                  className={`ml-4 space-y-1 overflow-hidden transition-all duration-300 ease-in-out ${
                    expandedSections.overall ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                  }`}
                >
                  <BatteryParameter label="3.331 V (highest)" value="" />
                  <BatteryParameter label="3.327 V (average)" value="" />
                  <BatteryParameter label="3.305 V (lowest)" value="" />
                </div>
              </div>
              
              <div className="pt-2">
                <div className="text-sm font-medium text-gray-700 mb-2">Cell imbalance:</div>
                <div className="ml-4 space-y-1">
                  <BatteryParameter label="0.026 V (highest)" value="" />
                  <BatteryParameter label="0.016 V (average)" value="" />
                  <BatteryParameter label="0.005 V (lowest)" value="" />
                </div>
              </div>
            </div>
          </div>

          {/* Individual Batteries */}
          <div className="bg-white rounded-lg p-6 shadow-sm">
            <h2 className="text-xl font-semibold mb-4">Individual Batteries</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Battery 1 */}
              <div>
                <h3 className="text-lg font-medium mb-3">Battery 1</h3>
                <div className="space-y-1">
                  <BatteryParameter label="Capacity" value={battery1.capacity} unit="Ah" />
                  <BatteryParameter label="State of charge" value={battery1.soc} unit="%" />
                  <BatteryParameter label="State of health" value={battery1.soh} unit="%" />
                  <BatteryParameter label="Power" value={battery1.power} unit="W" />
                  <BatteryParameter label="Current" value={battery1.current} unit="A" />
                  <BatteryParameter label="Voltage" value={battery1.voltage} unit="V" />
                  <BatteryParameter label="Temperature" value={battery1.temperature} unit="°C" />
                  <BatteryParameter label="Temperature MOS" value={battery1.temperatureMOS} unit="°C" />
                  <BatteryParameter label="Temperature 1" value={battery1.temperature1} unit="°C" />
                  <BatteryParameter label="Temperature 2" value={battery1.temperature2} unit="°C" />
                  <BatteryParameter label="Cycles" value={battery1.cycles} />
                  <BatteryParameter label="Charge capacity" value={battery1.chargeCapacity} unit="Ah" />
                  
                  <div className="pt-2">
                    <button
                      onClick={() => setExpandedSections(prev => ({ ...prev, battery1: !prev.battery1 }))}
                      className="flex items-center justify-between w-full text-sm font-medium text-gray-700 mb-2 hover:text-gray-900 transition-colors"
                    >
                      <span>Cell voltage:</span>
                      <ChevronDown 
                        className={`w-4 h-4 transition-transform duration-300 ${expandedSections.battery1 ? 'rotate-180' : ''}`}
                      />
                    </button>
                    <div 
                      className={`ml-4 space-y-1 overflow-hidden transition-all duration-300 ease-in-out ${
                        expandedSections.battery1 ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                      }`}
                    >
                      <BatteryParameter label="3.331 V (highest)" value="" />
                      <BatteryParameter label="0.017 V (imbalance)" value="" />
                      <BatteryParameter label="3.314 V (lowest)" value="" />
                    </div>
                  </div>
                </div>
              </div>

              {/* Battery 2 */}
              <div>
                <h3 className="text-lg font-medium mb-3">Battery 2</h3>
                <div className="space-y-1">
                  <BatteryParameter label="Capacity" value={battery2.capacity} unit="Ah" />
                  <BatteryParameter label="State of charge" value={battery2.soc} unit="%" />
                  <BatteryParameter label="State of health" value={battery2.soh} unit="%" />
                  <BatteryParameter label="Power" value={battery2.power} unit="W" />
                  <BatteryParameter label="Current" value={battery2.current} unit="A" />
                  <BatteryParameter label="Voltage" value={battery2.voltage} unit="V" />
                  <BatteryParameter label="Temperature" value={battery2.temperature} unit="°C" />
                  <BatteryParameter label="Temperature MOS" value={battery2.temperatureMOS} unit="°C" />
                  <BatteryParameter label="Temperature 1" value={battery2.temperature1} unit="°C" />
                  <BatteryParameter label="Temperature 2" value={battery2.temperature2} unit="°C" />
                  <BatteryParameter label="Cycles" value={battery2.cycles} />
                  <BatteryParameter label="Charge capacity" value={battery2.chargeCapacity} unit="Ah" />
                  
                  <div className="pt-2">
                    <button
                      onClick={() => setExpandedSections(prev => ({ ...prev, battery2: !prev.battery2 }))}
                      className="flex items-center justify-between w-full text-sm font-medium text-gray-700 mb-2 hover:text-gray-900 transition-colors"
                    >
                      <span>Cell voltage:</span>
                      <ChevronDown 
                        className={`w-4 h-4 transition-transform duration-300 ${expandedSections.battery2 ? 'rotate-180' : ''}`}
                      />
                    </button>
                    <div 
                      className={`ml-4 space-y-1 overflow-hidden transition-all duration-300 ease-in-out ${
                        expandedSections.battery2 ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                      }`}
                    >
                      <BatteryParameter label="3.331 V (highest)" value="" />
                      <BatteryParameter label="0.026 V (imbalance)" value="" />
                      <BatteryParameter label="3.305 V (lowest)" value="" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Section - Bar Charts */}
        <div className="space-y-6">
          {/* Power Chart */}
          <HorizontalBarChart
            title="Power"
            data={[
              { label: "Battery 1", value: battery1.power, color: "bg-blue-500" },
              { label: "Battery 2", value: battery2.power, color: "bg-green-500" },
              { label: "Overall", value: overallBattery.power, color: "bg-orange-500" }
            ]}
            maxValue={3.333}
            unit="W"
          />

          {/* State of Charge Chart */}
          <HorizontalBarChart
            title="State of Charge"
            data={[
              { label: "Battery 1", value: battery1.soc, color: "bg-blue-500" },
              { label: "Battery 2", value: battery2.soc, color: "bg-green-500" },
              { label: "Overall", value: overallBattery.soc, color: "bg-orange-500" }
            ]}
            maxValue={100}
            unit="%"
          />

          {/* Voltage Chart */}
          <HorizontalBarChart
            title="Voltage"
            data={[
              { label: "Battery 1", value: battery1.voltage, color: "bg-blue-500" },
              { label: "Battery 2", value: battery2.voltage, color: "bg-green-500" },
              { label: "Overall", value: overallBattery.voltage, color: "bg-orange-500" }
            ]}
            maxValue={100}
            unit="V"
          />

          {/* Temperature Chart */}
          <HorizontalBarChart
            title="Temperature"
            data={[
              { label: "Battery 1", value: battery1.temperature, color: "bg-blue-500" },
              { label: "Battery 2", value: battery2.temperature, color: "bg-green-500" },
              { label: "Overall", value: overallBattery.temperature, color: "bg-orange-500" }
            ]}
            maxValue={50}
            unit="°C"
          />

          {/* Cell Imbalance Chart */}
          <HorizontalBarChart
            title="Cell Imbalance"
            data={[
              { label: "Battery 1", value: battery1.cellImbalance.highest, color: "bg-blue-500" },
              { label: "Battery 2", value: battery2.cellImbalance.highest, color: "bg-green-500" },
              { label: "Overall", value: overallBattery.cellImbalance.highest, color: "bg-orange-500" }
            ]}
            maxValue={0.2}
            unit="V"
          />
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 text-center text-sm text-gray-500">
        Last updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  );
};
