/**
 * Админ страница для управления агентами ботов (физические экземпляры ботов)
 */

import React, { useEffect, useState } from 'react';
import axios from '../services/axiosConfig';
import { addResponsiveStyles } from '../utils/responsiveStyles';

// Initialize responsive styles
if (typeof document !== 'undefined') {
  addResponsiveStyles();
}

interface Agent {
  agent_id: string;
  status: string;
  last_seen: string;
  version: string | null;
  assigned_session_id: number | null;
  heartbeat_lag_seconds: number | null;
}

const AdminAgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commandAgent, setCommandAgent] = useState<string | null>(null);
  const [commandType, setCommandType] = useState<string>('pause');
  const [commandReason, setCommandReason] = useState<string>('');

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await axios.get('/api/v1/agents');
      setAgents(response.data || []);
      setError(null);
    } catch (err: any) {
      console.error('Error fetching agents:', err);
      setAgents([]);
      setError(err.response?.data?.detail || 'Ошибка загрузки агентов');
    } finally {
      setLoading(false);
    }
  };

  const sendCommand = async (agentId: string) => {
    try {
      await axios.post(`/api/v1/agent/${agentId}/command`, {
        command: commandType,
        reason: commandReason
      });
      setCommandAgent(null);
      setCommandReason('');
      const commandNames: {[key: string]: string} = {
        pause: 'Пауза',
        resume: 'Продолжить',
        stop: 'Остановить',
        sit_out: 'Выйти из игры'
      };
      alert(`Команда "${commandNames[commandType] || commandType}" отправлена агенту ${agentId}`);
    } catch (err: any) {
      alert(`Ошибка: ${err.response?.data?.detail || 'Не удалось отправить команду'}`);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return '#4CAF50';
      case 'offline': return '#F44336';
      case 'busy': return '#FFA726';
      default: return '#9E9E9E';
    }
  };

  const formatLastSeen = (lastSeen: string) => {
    if (!lastSeen) return 'Никогда';
    const date = new Date(lastSeen);
    return date.toLocaleString('ru-RU');
  };

  if (loading) {
    return <div style={loadingStyle}>Загрузка агентов...</div>;
  }

  return (
    <div style={pageStyle} className="admin-page-container">
      <div style={headerStyle}>
        <h1 style={{ margin: 0 }}>Управление агентами</h1>
        <p style={{ margin: '5px 0 0 0', color: '#C5C6C7' }}>
          Мониторинг и управление агентами ботов в реальном времени
        </p>
      </div>

      {error && <div style={errorStyle}>{error}</div>}

      {/* Stats Summary */}
      <div style={statsRowStyle} className="admin-stats-grid">
        <div style={statBoxStyle}>
          <div style={statValueStyle}>{agents.length}</div>
          <div style={statLabelStyle}>Всего агентов</div>
        </div>
        <div style={statBoxStyle}>
          <div style={{ ...statValueStyle, color: '#4CAF50' }}>
            {agents.filter(a => a.status === 'online').length}
          </div>
          <div style={statLabelStyle}>Онлайн</div>
        </div>
        <div style={statBoxStyle}>
          <div style={{ ...statValueStyle, color: '#F44336' }}>
            {agents.filter(a => a.status === 'offline').length}
          </div>
          <div style={statLabelStyle}>Оффлайн</div>
        </div>
        <div style={statBoxStyle}>
          <div style={{ ...statValueStyle, color: '#FFA726' }}>
            {agents.filter(a => a.assigned_session_id).length}
          </div>
          <div style={statLabelStyle}>В сессии</div>
        </div>
      </div>

      {/* Agents Grid */}
      <div style={agentsGridStyle} className="admin-list-grid">
        {agents.length === 0 ? (
          <div style={emptyStyle}>Агенты еще не зарегистрированы</div>
        ) : (
          agents.map(agent => (
            <div key={agent.agent_id} style={agentCardStyle}>
              <div style={agentHeaderStyle}>
                <span style={{
                  ...statusDotStyle,
                  background: getStatusColor(agent.status)
                }} />
                <span style={agentIdStyle}>{agent.agent_id}</span>
                <span style={{
                  ...statusBadgeStyle,
                  background: getStatusColor(agent.status)
                }}>
                  {agent.status === 'online' ? 'ОНЛАЙН' : agent.status === 'offline' ? 'ОФФЛАЙН' : agent.status === 'busy' ? 'ЗАНЯТ' : agent.status.toUpperCase()}
                </span>
              </div>

              <div style={agentInfoStyle}>
                <div style={infoRowStyle}>
                  <span style={infoLabelStyle}>Последний раз:</span>
                  <span>{formatLastSeen(agent.last_seen)}</span>
                </div>
                <div style={infoRowStyle}>
                  <span style={infoLabelStyle}>Версия:</span>
                  <span>{agent.version || 'Неизвестно'}</span>
                </div>
                <div style={infoRowStyle}>
                  <span style={infoLabelStyle}>Сессия:</span>
                  <span>{agent.assigned_session_id || 'Нет'}</span>
                </div>
                <div style={infoRowStyle}>
                  <span style={infoLabelStyle}>Задержка heartbeat:</span>
                  <span style={{
                    color: (agent.heartbeat_lag_seconds || 0) > 30 ? '#F44336' : '#4CAF50'
                  }}>
                    {agent.heartbeat_lag_seconds?.toFixed(1) || '0'}с
                  </span>
                </div>
              </div>

              <div style={agentActionsStyle}>
                {commandAgent === agent.agent_id ? (
                  <div style={commandFormStyle}>
                    <select
                      value={commandType}
                      onChange={e => setCommandType(e.target.value)}
                      style={selectStyle}
                      className="admin-input"
                    >
                      <option value="pause">Пауза</option>
                      <option value="resume">Продолжить</option>
                      <option value="stop">Остановить</option>
                      <option value="sit_out">Выйти из игры</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Причина (опционально)"
                      value={commandReason}
                      onChange={e => setCommandReason(e.target.value)}
                      style={inputStyle}
                      className="admin-input"
                    />
                    <div style={buttonRowStyle} className="admin-button-row">
                      <button
                        onClick={() => sendCommand(agent.agent_id)}
                        style={sendButtonStyle}
                      >
                        Отправить
                      </button>
                      <button
                        onClick={() => setCommandAgent(null)}
                        style={cancelButtonStyle}
                      >
                        Отмена
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setCommandAgent(agent.agent_id)}
                    style={commandButtonStyle}
                    className="admin-button"
                    disabled={agent.status === 'offline'}
                  >
                    Отправить команду
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// Styles
const pageStyle: React.CSSProperties = { padding: '12px' };
const loadingStyle: React.CSSProperties = { textAlign: 'center', padding: '50px', color: '#C5C6C7' };
const headerStyle: React.CSSProperties = { marginBottom: '24px', padding: '16px', background: '#1F2833', borderRadius: '8px' };
const errorStyle: React.CSSProperties = { background: '#F44336', color: '#FFFFFF', padding: '15px', borderRadius: '8px', marginBottom: '20px' };

const statsRowStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '24px' };
const statBoxStyle: React.CSSProperties = { background: '#1F2833', padding: '20px', borderRadius: '8px', textAlign: 'center' };
const statValueStyle: React.CSSProperties = { fontSize: '32px', fontWeight: 'bold', color: '#66FCF1' };
const statLabelStyle: React.CSSProperties = { color: '#C5C6C7', marginTop: '5px' };

const agentsGridStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: '1fr', gap: '16px' };
const emptyStyle: React.CSSProperties = { textAlign: 'center', padding: '40px', color: '#C5C6C7', gridColumn: '1 / -1' };

const agentCardStyle: React.CSSProperties = { background: '#1F2833', borderRadius: '8px', padding: '20px' };
const agentHeaderStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px', paddingBottom: '15px', borderBottom: '1px solid #45A29E' };
const statusDotStyle: React.CSSProperties = { width: '12px', height: '12px', borderRadius: '50%' };
const agentIdStyle: React.CSSProperties = { flex: 1, fontWeight: 'bold', fontSize: '16px' };
const statusBadgeStyle: React.CSSProperties = { padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 'bold', color: '#FFFFFF' };

const agentInfoStyle: React.CSSProperties = { marginBottom: '15px' };
const infoRowStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #2C3440' };
const infoLabelStyle: React.CSSProperties = { color: '#C5C6C7' };

const agentActionsStyle: React.CSSProperties = { marginTop: '15px' };
const commandButtonStyle: React.CSSProperties = { width: '100%', padding: '12px', background: '#45A29E', border: 'none', borderRadius: '6px', color: '#FFFFFF', cursor: 'pointer', fontWeight: 'bold' };

const commandFormStyle: React.CSSProperties = { 
  display: 'flex', 
  flexDirection: 'column', 
  gap: '10px',
  width: '100%'
};
const selectStyle: React.CSSProperties = { 
  padding: '10px', 
  background: '#0B0C10', 
  border: '1px solid #45A29E', 
  borderRadius: '6px', 
  color: '#FFFFFF',
  width: '100%'
};
const inputStyle: React.CSSProperties = { 
  padding: '10px', 
  background: '#0B0C10', 
  border: '1px solid #45A29E', 
  borderRadius: '6px', 
  color: '#FFFFFF',
  width: '100%'
};
const buttonRowStyle: React.CSSProperties = { display: 'flex', gap: '10px' };
const sendButtonStyle: React.CSSProperties = { 
  flex: 1, 
  padding: '10px', 
  background: '#4CAF50', 
  border: 'none', 
  borderRadius: '6px', 
  color: '#FFFFFF', 
  cursor: 'pointer', 
  fontWeight: 'bold',
  minWidth: '100px'
};
const cancelButtonStyle: React.CSSProperties = { 
  flex: 1, 
  padding: '10px', 
  background: '#F44336', 
  border: 'none', 
  borderRadius: '6px', 
  color: '#FFFFFF', 
  cursor: 'pointer', 
  fontWeight: 'bold',
  minWidth: '100px'
};

export default AdminAgentsPage;
