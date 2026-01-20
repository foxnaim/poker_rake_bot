/**
 * Main Dashboard component with real-time stats and charts
 */

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

interface Stats {
  total_hands: number;
  total_decisions: number;
  total_sessions: number;
  active_sessions: number;
  total_opponents: number;
  total_profit: number;
  total_rake: number;
  winrate_bb_100: number;
}

interface ChartData {
  name: string;
  profit: number;
  hands: number;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);

    // WebSocket for real-time updates (optional - may not be available)
    let ws: WebSocket | null = null;
    try {
      const wsUrl = process.env.NODE_ENV === 'production'
        ? `ws://${window.location.host}/ws/live`
        : 'ws://localhost:8000/ws/live';
      ws = new WebSocket(wsUrl);
      ws.onopen = () => setIsConnected(true);
      ws.onclose = () => setIsConnected(false);
      ws.onerror = () => setIsConnected(false);
    } catch (e) {
      console.log('WebSocket not available');
    }

    return () => {
      clearInterval(interval);
      if (ws) ws.close();
    };
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/v1/stats');
      setStats(response.data);

      // Generate chart data (mock for now, would come from real API)
      const mockData: ChartData[] = [];
      let cumProfit = 0;
      for (let i = 7; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        const dayProfit = (Math.random() - 0.3) * 20;
        cumProfit += dayProfit;
        mockData.push({
          name: date.toLocaleDateString('en-US', { weekday: 'short' }),
          profit: Math.round(cumProfit * 100) / 100,
          hands: Math.floor(Math.random() * 500) + 100
        });
      }
      setChartData(mockData);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={loadingStyle}>Loading dashboard...</div>;
  }

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <div>
          <h1 style={{ margin: 0 }}>Dashboard</h1>
          <p style={{ margin: '5px 0 0 0', color: '#C5C6C7' }}>Real-time poker bot monitoring</p>
        </div>
        <div style={statusStyle}>
          <span style={{
            ...statusBadgeStyle,
            background: isConnected ? '#4CAF50' : '#F44336'
          }}>
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>
      </div>

      {/* Stats Cards */}
      <div style={statsGridStyle}>
        <StatCard
          label="Total Hands"
          value={stats?.total_hands?.toLocaleString() || '0'}
          icon="🃏"
          color="#66FCF1"
        />
        <StatCard
          label="Total Profit"
          value={`$${stats?.total_profit?.toFixed(2) || '0.00'}`}
          icon="💰"
          color={stats?.total_profit && stats.total_profit >= 0 ? '#4CAF50' : '#F44336'}
        />
        <StatCard
          label="Winrate"
          value={`${stats?.winrate_bb_100?.toFixed(2) || '0.00'} bb/100`}
          icon="📈"
          color="#FFA726"
        />
        <StatCard
          label="Total Rake"
          value={`$${stats?.total_rake?.toFixed(2) || '0.00'}`}
          icon="🏦"
          color="#AB47BC"
        />
        <StatCard
          label="Opponents"
          value={stats?.total_opponents?.toString() || '0'}
          icon="👥"
          color="#42A5F5"
        />
        <StatCard
          label="Active Sessions"
          value={stats?.active_sessions?.toString() || '0'}
          icon="🎮"
          color="#66BB6A"
        />
      </div>

      {/* Charts */}
      <div style={chartsGridStyle}>
        <div style={chartCardStyle}>
          <h3 style={chartTitleStyle}>Profit Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#45A29E" />
              <XAxis dataKey="name" stroke="#C5C6C7" />
              <YAxis stroke="#C5C6C7" />
              <Tooltip
                contentStyle={{ background: '#1F2833', border: '1px solid #45A29E' }}
                labelStyle={{ color: '#66FCF1' }}
              />
              <Area
                type="monotone"
                dataKey="profit"
                stroke="#66FCF1"
                fill="url(#profitGradient)"
              />
              <defs>
                <linearGradient id="profitGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#66FCF1" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#66FCF1" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={chartCardStyle}>
          <h3 style={chartTitleStyle}>Hands Played</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#45A29E" />
              <XAxis dataKey="name" stroke="#C5C6C7" />
              <YAxis stroke="#C5C6C7" />
              <Tooltip
                contentStyle={{ background: '#1F2833', border: '1px solid #45A29E' }}
                labelStyle={{ color: '#66FCF1' }}
              />
              <Line
                type="monotone"
                dataKey="hands"
                stroke="#FFA726"
                strokeWidth={2}
                dot={{ fill: '#FFA726' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={actionsCardStyle}>
        <h3 style={{ margin: '0 0 20px 0', color: '#66FCF1' }}>Quick Actions</h3>
        <div style={actionsGridStyle}>
          <ActionButton label="Start NL10 Session" onClick={() => axios.post('/api/v1/session/start', { session_id: `session_${Date.now()}`, limit_type: 'NL10' })} />
          <ActionButton label="View Opponents" href="/opponents" />
          <ActionButton label="Training Status" href="/training" />
          <ActionButton label="Hand History" href="/hands" />
        </div>
      </div>
    </div>
  );
};

// StatCard component
const StatCard: React.FC<{label: string; value: string; icon: string; color: string}> = ({ label, value, icon, color }) => (
  <div style={statCardStyle}>
    <div style={statIconStyle}>{icon}</div>
    <div>
      <div style={statLabelStyle}>{label}</div>
      <div style={{...statValueStyle, color}}>{value}</div>
    </div>
  </div>
);

// ActionButton component
const ActionButton: React.FC<{label: string; onClick?: () => void; href?: string}> = ({ label, onClick, href }) => {
  if (href) {
    return (
      <a href={href} style={actionButtonStyle}>
        {label}
      </a>
    );
  }
  return (
    <button onClick={onClick} style={actionButtonStyle}>
      {label}
    </button>
  );
};

// Styles
const pageStyle: React.CSSProperties = { padding: '20px' };
const loadingStyle: React.CSSProperties = { textAlign: 'center', padding: '50px', color: '#C5C6C7' };
const headerStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px', padding: '20px', background: '#1F2833', borderRadius: '8px' };
const statusStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '10px' };
const statusBadgeStyle: React.CSSProperties = { padding: '8px 16px', borderRadius: '20px', fontSize: '12px', fontWeight: 'bold', color: '#FFFFFF' };
const statsGridStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '20px', marginBottom: '30px' };
const statCardStyle: React.CSSProperties = { background: '#1F2833', borderRadius: '8px', padding: '20px', display: 'flex', alignItems: 'center', gap: '15px' };
const statIconStyle: React.CSSProperties = { fontSize: '32px' };
const statLabelStyle: React.CSSProperties = { color: '#C5C6C7', fontSize: '14px', marginBottom: '5px' };
const statValueStyle: React.CSSProperties = { fontSize: '24px', fontWeight: 'bold' };
const chartsGridStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px', marginBottom: '30px' };
const chartCardStyle: React.CSSProperties = { background: '#1F2833', borderRadius: '8px', padding: '20px' };
const chartTitleStyle: React.CSSProperties = { margin: '0 0 20px 0', color: '#66FCF1' };
const actionsCardStyle: React.CSSProperties = { background: '#1F2833', borderRadius: '8px', padding: '25px' };
const actionsGridStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' };
const actionButtonStyle: React.CSSProperties = { padding: '15px 20px', background: '#45A29E', border: 'none', borderRadius: '8px', color: '#FFFFFF', cursor: 'pointer', fontWeight: 'bold', textDecoration: 'none', textAlign: 'center', display: 'block' };

export default Dashboard;
