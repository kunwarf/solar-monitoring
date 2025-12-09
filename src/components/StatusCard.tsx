import React from 'react';

interface StatusCardProps {
  icon: React.ReactNode;
  title: string;
  status?: string;
  value?: string;
  subtitle?: string;
}

export const StatusCard: React.FC<StatusCardProps> = ({
  icon,
  title,
  status,
  value,
  subtitle
}) => {
  return (
    <div className="bg-gray-100 rounded-lg p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="text-4xl">{icon}</div>
        <div className="text-right">
          <div className="text-sm font-medium text-gray-600">{title}</div>
        </div>
      </div>
      
      {status && (
        <div className="text-lg font-semibold text-gray-800">{status}</div>
      )}
      
      {value && (
        <div className="text-2xl font-bold text-gray-900">{value}</div>
      )}
      
      {subtitle && (
        <div className="text-sm text-gray-600 mt-1">{subtitle}</div>
      )}
    </div>
  );
};
