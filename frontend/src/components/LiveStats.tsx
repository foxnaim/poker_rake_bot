/**
 * Компонент для отображения live статистики
 */

import React from 'react';

interface LiveStatsProps {
  stats: {
    winrate_nl10: number;
    winrate_nl50: number;
    hands_per_hour: number;
    avg_latency_ms: number;
    requests_per_sec: number;
  };
}

const LiveStats: React.FC<LiveStatsProps> = ({ stats }) => {
  return (
    <div className="live-stats" style={cardStyle}>
      <h2 style={titleStyle}>Статистика в реальном времени</h2>
      
      <div style={statsContainerStyle}>
        <StatItem label="Винрейт NL10" value={`${stats.winrate_nl10.toFixed(2)} bb/100`} />
        <StatItem label="Винрейт NL50" value={`${stats.winrate_nl50.toFixed(2)} bb/100`} />
        <StatItem label="Раздач/час" value={stats.hands_per_hour.toFixed(0)} />
        <StatItem label="Средняя задержка" value={`${stats.avg_latency_ms.toFixed(0)} мс`} />
        <StatItem label="Запросов/сек" value={stats.requests_per_sec.toFixed(1)} />
      </div>
    </div>
  );
};

interface StatItemProps {
  label: string;
  value: string;
}

const StatItem: React.FC<StatItemProps> = ({ label, value }) => (
  <div style={statItemStyle}>
    <span style={labelStyle}>{label}:</span>
    <span style={valueStyle}>{value}</span>
  </div>
);

const cardStyle: React.CSSProperties = {
  background: '#1F2833',
  padding: '16px',
  borderRadius: '8px',
  border: '1px solid #C5C6C7'
};

// Add responsive padding
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 768px) {
      .live-stats {
        padding: 20px !important;
      }
    }
  `;
  document.head.appendChild(style);
}

const titleStyle: React.CSSProperties = {
  color: '#66FCF1',
  marginTop: 0,
  marginBottom: '20px'
};

const statsContainerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '15px'
};

const statItemStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '10px',
  background: '#0B0C10',
  borderRadius: '4px'
};

const labelStyle: React.CSSProperties = {
  color: '#CCCCCC'
};

const valueStyle: React.CSSProperties = {
  color: '#FFFFFF',
  fontWeight: 'bold'
};

export default LiveStats;
