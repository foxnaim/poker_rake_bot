/**
 * Main Dashboard component with real-time stats and charts
 * Beautiful design with React-icons and Framer Motion animations
 */

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { motion } from 'framer-motion';
import { 
  FaDollarSign, 
  FaChartLine, 
  FaBuilding, 
  FaUsers, 
  FaGamepad,
  FaPlay,
  FaHistory,
  FaBrain,
  FaUserFriends
} from 'react-icons/fa';
import { GiCardPlay, GiPokerHand } from 'react-icons/gi';
import { 
  MdTrendingUp, 
  MdTrendingDown,
  MdCircle
} from 'react-icons/md';
import { 
  BiTrendingUp,
  BiTrendingDown
} from 'react-icons/bi';

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

    // WebSocket for real-time updates
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

      // Generate chart data
      const mockData: ChartData[] = [];
      let cumProfit = 0;
      for (let i = 7; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        const dayProfit = (Math.random() - 0.3) * 20;
        cumProfit += dayProfit;
        mockData.push({
          name: date.toLocaleDateString('ru-RU', { weekday: 'short' }),
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
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={loadingStyle}
      >
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          style={{ fontSize: '48px', marginBottom: '20px' }}
        >
          🎰
        </motion.div>
        <div>Загрузка панели управления...</div>
      </motion.div>
    );
  }

  const profitColor = stats?.total_profit && stats.total_profit >= 0 ? '#10B981' : '#EF4444';
  const winrateColor = stats?.winrate_bb_100 && stats.winrate_bb_100 >= 0 ? '#10B981' : '#EF4444';

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={pageStyle}
    >
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        style={headerStyle}
      >
        <div>
          <h1 style={titleStyle}>Панель управления</h1>
          <p style={subtitleStyle}>Мониторинг покер-бота в реальном времени</p>
        </div>
        <motion.div
          animate={{ 
            scale: isConnected ? [1, 1.1, 1] : 1,
            opacity: isConnected ? [1, 0.7, 1] : 0.5
          }}
          transition={{ 
            duration: 2, 
            repeat: isConnected ? Infinity : 0,
            ease: "easeInOut"
          }}
          style={statusContainerStyle}
        >
          <motion.div
            style={{
              ...statusBadgeStyle,
              background: isConnected ? 'linear-gradient(135deg, #10B981 0%, #059669 100%)' : '#6B7280',
              boxShadow: isConnected ? '0 0 20px rgba(16, 185, 129, 0.5)' : 'none'
            }}
          >
            <MdCircle style={{ fontSize: '8px', marginRight: '6px' }} />
            {isConnected ? 'ОНЛАЙН' : 'ОФФЛАЙН'}
          </motion.div>
        </motion.div>
      </motion.div>

      {/* Stats Cards */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        style={statsGridStyle}
      >
        <StatCard
          label="Всего раздач"
          value={stats?.total_hands?.toLocaleString() || '0'}
          icon={<GiPokerHand />}
          color="#66FCF1"
          delay={0.3}
          trend={stats?.total_hands && stats.total_hands > 0 ? 'up' : 'neutral'}
        />
        <StatCard
          label="Общая прибыль"
          value={`$${stats?.total_profit?.toFixed(2) || '0.00'}`}
          icon={<FaDollarSign />}
          color={profitColor}
          delay={0.4}
          trend={stats?.total_profit && stats.total_profit >= 0 ? 'up' : 'down'}
        />
        <StatCard
          label="Винрейт"
          value={`${stats?.winrate_bb_100?.toFixed(2) || '0.00'} bb/100`}
          icon={<FaChartLine />}
          color={winrateColor}
          delay={0.5}
          trend={stats?.winrate_bb_100 && stats.winrate_bb_100 >= 0 ? 'up' : 'down'}
        />
        <StatCard
          label="Общий рейк"
          value={`$${stats?.total_rake?.toFixed(2) || '0.00'}`}
          icon={<FaBuilding />}
          color="#A855F7"
          delay={0.6}
          trend="neutral"
        />
        <StatCard
          label="Оппоненты"
          value={stats?.total_opponents?.toString() || '0'}
          icon={<FaUsers />}
          color="#3B82F6"
          delay={0.7}
          trend="neutral"
        />
        <StatCard
          label="Активные сессии"
          value={stats?.active_sessions?.toString() || '0'}
          icon={<FaGamepad />}
          color="#10B981"
          delay={0.8}
          trend="neutral"
        />
      </motion.div>

      {/* Charts */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.9 }}
        style={chartsGridStyle}
      >
        <motion.div
          whileHover={{ scale: 1.02, y: -5 }}
          transition={{ duration: 0.2 }}
          style={chartCardStyle}
        >
          <div style={chartHeaderStyle}>
            <h3 style={chartTitleStyle}>
              <FaChartLine style={{ marginRight: '10px', color: '#66FCF1' }} />
              Прибыль по времени
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="profitGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#66FCF1" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#66FCF1" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" opacity={0.3} />
              <XAxis 
                dataKey="name" 
                stroke="#9CA3AF" 
                style={{ fontSize: '12px' }}
              />
              <YAxis 
                stroke="#9CA3AF" 
                style={{ fontSize: '12px' }}
              />
              <Tooltip
                contentStyle={{ 
                  background: '#1F2937', 
                  border: '1px solid #66FCF1',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)'
                }}
                labelStyle={{ color: '#66FCF1', fontWeight: 'bold' }}
              />
              <Area
                type="monotone"
                dataKey="profit"
                stroke="#66FCF1"
                strokeWidth={3}
                fill="url(#profitGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02, y: -5 }}
          transition={{ duration: 0.2 }}
          style={chartCardStyle}
        >
          <div style={chartHeaderStyle}>
            <h3 style={chartTitleStyle}>
              <GiCardPlay style={{ marginRight: '10px', color: '#F59E0B' }} />
              Сыгранные раздачи
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" opacity={0.3} />
              <XAxis 
                dataKey="name" 
                stroke="#9CA3AF" 
                style={{ fontSize: '12px' }}
              />
              <YAxis 
                stroke="#9CA3AF" 
                style={{ fontSize: '12px' }}
              />
              <Tooltip
                contentStyle={{ 
                  background: '#1F2937', 
                  border: '1px solid #F59E0B',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)'
                }}
                labelStyle={{ color: '#F59E0B', fontWeight: 'bold' }}
              />
              <Line
                type="monotone"
                dataKey="hands"
                stroke="#F59E0B"
                strokeWidth={3}
                dot={{ fill: '#F59E0B', r: 5 }}
                activeDot={{ r: 8 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>
      </motion.div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 1.0 }}
        style={actionsCardStyle}
      >
        <h3 style={actionsTitleStyle}>
          <FaPlay style={{ marginRight: '10px' }} />
          Быстрые действия
        </h3>
        <div style={actionsGridStyle}>
          <ActionButton 
            label="Запустить сессию NL10" 
            icon={<FaPlay />}
            onClick={() => axios.post('/api/v1/session/start', { session_id: `session_${Date.now()}`, limit_type: 'NL10' })} 
          />
          <ActionButton 
            label="Просмотр оппонентов" 
            icon={<FaUserFriends />}
            href="/opponents" 
          />
          <ActionButton 
            label="Статус обучения" 
            icon={<FaBrain />}
            href="/training" 
          />
          <ActionButton 
            label="История раздач" 
            icon={<FaHistory />}
            href="/hands" 
          />
        </div>
      </motion.div>
    </motion.div>
  );
};

// StatCard component with animations
const StatCard: React.FC<{
  label: string; 
  value: string; 
  icon: React.ReactNode; 
  color: string;
  delay: number;
  trend?: 'up' | 'down' | 'neutral';
}> = ({ label, value, icon, color, delay, trend = 'neutral' }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.9, y: 20 }}
    animate={{ opacity: 1, scale: 1, y: 0 }}
    transition={{ duration: 0.4, delay }}
    whileHover={{ 
      scale: 1.05, 
      y: -8,
      boxShadow: `0 10px 30px ${color}40`
    }}
    style={{
      ...statCardStyle,
      borderLeft: `4px solid ${color}`,
      boxShadow: `0 4px 15px ${color}20`
    }}
  >
    <motion.div
      animate={{ rotate: [0, 10, -10, 0] }}
      transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
      style={{ ...statIconStyle, color }}
    >
      {icon}
    </motion.div>
    <div style={{ flex: 1 }}>
      <div style={statLabelStyle}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{...statValueStyle, color}}>{value}</div>
        {trend === 'up' && (
          <motion.div
            animate={{ y: [0, -3, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <BiTrendingUp style={{ color: '#10B981', fontSize: '20px' }} />
          </motion.div>
        )}
        {trend === 'down' && (
          <motion.div
            animate={{ y: [0, 3, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <BiTrendingDown style={{ color: '#EF4444', fontSize: '20px' }} />
          </motion.div>
        )}
      </div>
    </div>
  </motion.div>
);

// ActionButton component with animations
const ActionButton: React.FC<{
  label: string; 
  onClick?: () => void; 
  href?: string;
  icon: React.ReactNode;
}> = ({ label, onClick, href, icon }) => {
  const button = (
    <motion.button
      whileHover={{ scale: 1.05, y: -2 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      style={actionButtonStyle}
    >
      <motion.div
        animate={{ rotate: [0, 360] }}
        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        style={{ marginRight: '10px' }}
      >
        {icon}
      </motion.div>
      {label}
    </motion.button>
  );

  if (href) {
    return (
      <motion.a
        whileHover={{ scale: 1.05, y: -2 }}
        whileTap={{ scale: 0.95 }}
        href={href}
        style={actionButtonStyle}
      >
        <motion.div
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          style={{ marginRight: '10px' }}
        >
          {icon}
        </motion.div>
        {label}
      </motion.a>
    );
  }

  return button;
};

// Styles
const pageStyle: React.CSSProperties = { 
  padding: '24px',
  minHeight: '100vh'
};

const loadingStyle: React.CSSProperties = { 
  textAlign: 'center', 
  padding: '100px 20px', 
  color: '#9CA3AF',
  fontSize: '18px'
};

const headerStyle: React.CSSProperties = { 
  display: 'flex', 
  justifyContent: 'space-between', 
  alignItems: 'flex-start', 
  marginBottom: '32px', 
  padding: '28px 32px', 
  background: 'linear-gradient(135deg, #1F2937 0%, #111827 100%)',
  borderRadius: '16px',
  boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)',
  border: '1px solid #374151'
};

const titleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '32px',
  fontWeight: '700',
  background: 'linear-gradient(135deg, #66FCF1 0%, #45A29E 100%)',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  backgroundClip: 'text'
};

const subtitleStyle: React.CSSProperties = {
  margin: '8px 0 0 0',
  color: '#9CA3AF',
  fontSize: '16px',
  fontWeight: '400'
};

const statusContainerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px'
};

const statusBadgeStyle: React.CSSProperties = {
  padding: '10px 20px',
  borderRadius: '24px',
  fontSize: '13px',
  fontWeight: '700',
  color: '#FFFFFF',
  display: 'flex',
  alignItems: 'center',
  letterSpacing: '0.5px',
  textTransform: 'uppercase'
};

const statsGridStyle: React.CSSProperties = { 
  display: 'grid', 
  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', 
  gap: '24px', 
  marginBottom: '32px' 
};

const statCardStyle: React.CSSProperties = { 
  background: 'linear-gradient(135deg, #1F2937 0%, #111827 100%)',
  borderRadius: '16px', 
  padding: '24px', 
  display: 'flex', 
  alignItems: 'center', 
  gap: '20px',
  border: '1px solid #374151',
  transition: 'all 0.3s ease',
  cursor: 'pointer'
};

const statIconStyle: React.CSSProperties = { 
  fontSize: '40px',
  filter: 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3))'
};

const statLabelStyle: React.CSSProperties = { 
  color: '#9CA3AF', 
  fontSize: '14px', 
  marginBottom: '8px',
  fontWeight: '500',
  textTransform: 'uppercase',
  letterSpacing: '0.5px'
};

const statValueStyle: React.CSSProperties = { 
  fontSize: '28px', 
  fontWeight: '700',
  lineHeight: '1.2'
};

const chartsGridStyle: React.CSSProperties = { 
  display: 'grid', 
  gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', 
  gap: '24px', 
  marginBottom: '32px' 
};

const chartCardStyle: React.CSSProperties = { 
  background: 'linear-gradient(135deg, #1F2937 0%, #111827 100%)',
  borderRadius: '16px', 
  padding: '28px',
  border: '1px solid #374151',
  boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)'
};

const chartHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  marginBottom: '24px',
  paddingBottom: '16px',
  borderBottom: '1px solid #374151'
};

const chartTitleStyle: React.CSSProperties = { 
  margin: 0, 
  color: '#F3F4F6',
  fontSize: '20px',
  fontWeight: '600',
  display: 'flex',
  alignItems: 'center'
};

const actionsCardStyle: React.CSSProperties = { 
  background: 'linear-gradient(135deg, #1F2937 0%, #111827 100%)',
  borderRadius: '16px', 
  padding: '32px',
  border: '1px solid #374151',
  boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)'
};

const actionsTitleStyle: React.CSSProperties = {
  margin: '0 0 24px 0',
  color: '#66FCF1',
  fontSize: '22px',
  fontWeight: '600',
  display: 'flex',
  alignItems: 'center'
};

const actionsGridStyle: React.CSSProperties = { 
  display: 'grid', 
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', 
  gap: '16px' 
};

const actionButtonStyle: React.CSSProperties = { 
  padding: '16px 24px', 
  background: 'linear-gradient(135deg, #45A29E 0%, #66FCF1 100%)',
  border: 'none', 
  borderRadius: '12px', 
  color: '#0B0C10', 
  cursor: 'pointer', 
  fontWeight: '700',
  fontSize: '15px',
  textDecoration: 'none', 
  textAlign: 'center', 
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  boxShadow: '0 4px 15px rgba(102, 252, 241, 0.3)',
  transition: 'all 0.3s ease'
};

export default Dashboard;
