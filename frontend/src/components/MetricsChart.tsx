/**
 * Компонент для отображения графиков метрик
 */

import React from 'react';

interface MetricsChartProps {
  stats: {
    winrate_nl10: number;
    winrate_nl50: number;
    hands_per_hour: number;
    avg_latency_ms: number;
    requests_per_sec: number;
  };
}

const MetricsChart: React.FC<MetricsChartProps> = ({ stats }) => {
  return (
    <div className="metrics-chart" style={cardStyle}>
      <h2 style={titleStyle}>Метрики производительности</h2>
      
      <div style={chartContainerStyle}>
        <MetricBar label="Задержка" value={stats.avg_latency_ms} max={200} unit="мс" />
        <MetricBar label="Раздач/час" value={stats.hands_per_hour} max={100} unit="" />
        <MetricBar label="Запросов/сек" value={stats.requests_per_sec} max={10} unit="" />
      </div>
    </div>
  );
};

interface MetricBarProps {
  label: string;
  value: number;
  max: number;
  unit: string;
}

const MetricBar: React.FC<MetricBarProps> = ({ label, value, max, unit }) => {
  const percentage = Math.min((value / max) * 100, 100);
  const color = percentage > 80 ? '#ff4444' : percentage > 60 ? '#ffaa00' : '#44ff44';

  return (
    <div style={barContainerStyle}>
      <div style={barLabelStyle}>
        <span>{label}</span>
        <span>{value.toFixed(1)} {unit}</span>
      </div>
      <div style={barBackgroundStyle}>
        <div 
          style={{
            ...barFillStyle,
            width: `${percentage}%`,
            background: color
          }}
        />
      </div>
    </div>
  );
};

const cardStyle: React.CSSProperties = {
  background: '#1F2833',
  padding: '20px',
  borderRadius: '8px',
  border: '1px solid #C5C6C7'
};

const titleStyle: React.CSSProperties = {
  color: '#66FCF1',
  marginTop: 0,
  marginBottom: '20px'
};

const chartContainerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '20px'
};

const barContainerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px'
};

const barLabelStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  color: '#CCCCCC',
  fontSize: '14px'
};

const barBackgroundStyle: React.CSSProperties = {
  width: '100%',
  height: '20px',
  background: '#0B0C10',
  borderRadius: '4px',
  overflow: 'hidden'
};

const barFillStyle: React.CSSProperties = {
  height: '100%',
  transition: 'width 0.3s ease'
};

export default MetricsChart;
