/**
 * Главный компонент Dashboard
 * Real-time мониторинг покерного бота
 */

import React, { useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import LiveStats from './LiveStats';
import DecisionFeed from './DecisionFeed';
import MetricsChart from './MetricsChart';

interface DashboardStats {
  winrate_nl10: number;
  winrate_nl50: number;
  hands_per_hour: number;
  avg_latency_ms: number;
  requests_per_sec: number;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    winrate_nl10: 0,
    winrate_nl50: 0,
    hands_per_hour: 0,
    avg_latency_ms: 0,
    requests_per_sec: 0
  });

  const { messages, isConnected } = useWebSocket('ws://localhost:8000/ws/live');

  useEffect(() => {
    // Обрабатываем сообщения от WebSocket
    messages.forEach((message) => {
      if (message.type === 'stats') {
        setStats(message.metrics);
      }
    });
  }, [messages]);

  return (
    <div className="dashboard" style={dashboardStyle}>
      <header style={headerStyle}>
        <h1>🎰 Poker Rake Bot Dashboard</h1>
        <div className="status" style={statusStyle}>
          <span className={isConnected ? 'connected' : 'disconnected'}>
            {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
        </div>
      </header>

      <div className="stats-grid" style={gridStyle}>
        <LiveStats stats={stats} />
        <DecisionFeed messages={messages} />
        <MetricsChart stats={stats} />
      </div>
    </div>
  );
};

const dashboardStyle: React.CSSProperties = {
  minHeight: '100vh',
  background: '#0B0C10',
  color: '#FFFFFF',
  padding: '20px',
  fontFamily: 'sans-serif'
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '30px',
  padding: '20px',
  background: '#1F2833',
  borderRadius: '8px',
  border: '1px solid #C5C6C7'
};

const statusStyle: React.CSSProperties = {
  fontSize: '14px'
};

const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
  gap: '20px'
};

export default Dashboard;
