/**
 * Sessions Page - управление игровыми сессиями
 */

import React, { useEffect, useState } from 'react';
import axios from '../services/axiosConfig';
import { addResponsiveStyles } from '../utils/responsiveStyles';

// Initialize responsive styles
if (typeof document !== 'undefined') {
  addResponsiveStyles();
}

interface Session {
  session_id: string;
  limit_type: string;
  period_start: string;
  period_end: string | null;
  hands_played: number;
  winrate_bb_100?: number;
  total_rake?: number;
  profit_bb_100?: number;
  total_profit?: number;
}

const SessionsPage: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeSession, setActiveSession] = useState<Session | null>(null);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/sessions/recent?limit=50');
      const sessionsData = response.data || [];
      setSessions(sessionsData);
      const active = sessionsData.find((s: Session) => !s.period_end);
      setActiveSession(active || null);
    } catch (error: any) {
      console.error('Error fetching sessions:', error);
      setSessions([]);
      setActiveSession(null);
    } finally {
      setLoading(false);
    }
  };

  const startSession = async (limitType: string) => {
    try {
      const sessionId = `session_${Date.now()}`;
      await axios.post('/api/v1/session/start', {
        session_id: sessionId,
        limit_type: limitType
      });
      fetchSessions();
    } catch (error) {
      console.error('Error starting session:', error);
    }
  };

  const endSession = async () => {
    if (!activeSession) return;
    try {
      await axios.post('/api/v1/session/end', { session_id: activeSession.session_id });
      fetchSessions();
    } catch (error) {
      console.error('Error ending session:', error);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('ru-RU');
  };

  const formatDuration = (start: string, end: string | null) => {
    const startDate = new Date(start);
    const endDate = end ? new Date(end) : new Date();
    const minutes = Math.round((endDate.getTime() - startDate.getTime()) / 60000);
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  if (loading) {
    return <div style={loadingStyle}>Загрузка сессий...</div>;
  }

  return (
    <div style={pageStyle} className="user-page-container">
      <div style={headerStyle} className="user-page-header">
        <h1 style={{ margin: 0 }}>Игровые сессии</h1>
        <div style={actionsStyle}>
          {activeSession ? (
            <button onClick={endSession} style={endButtonStyle} className="admin-button">
              Завершить сессию
            </button>
          ) : (
            <div style={startGroupStyle} className="session-start-group">
              {['NL2', 'NL5', 'NL10', 'NL25', 'NL50'].map(limit => (
                <button
                  key={limit}
                  onClick={() => startSession(limit)}
                  style={startButtonStyle}
                >
                  Запустить {limit}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {activeSession && (
        <div style={activeCardStyle}>
          <div style={activeHeaderStyle}>
            <span style={activeBadgeStyle}>ОНЛАЙН</span>
            <h2 style={{ margin: 0 }}>Активная сессия: {activeSession.limit_type}</h2>
          </div>
          <div style={activeStatsStyle} className="session-active-stats">
            <div style={activeStatStyle}>
              <span style={labelStyle}>Длительность</span>
              <span style={valueStyle}>{formatDuration(activeSession.period_start, null)}</span>
            </div>
            <div style={activeStatStyle}>
              <span style={labelStyle}>Раздачи</span>
              <span style={valueStyle}>{activeSession.hands_played || 0}</span>
            </div>
            <div style={activeStatStyle}>
              <span style={labelStyle}>Винрейт</span>
              <span style={valueStyle}>
                {(activeSession.winrate_bb_100 || activeSession.profit_bb_100 || 0).toFixed(2)} bb/100
              </span>
            </div>
            <div style={activeStatStyle}>
              <span style={labelStyle}>Рейк</span>
              <span style={valueStyle}>${(activeSession.total_rake || 0).toFixed(2)}</span>
            </div>
          </div>
        </div>
      )}

      <div style={tableContainerStyle} className="user-table-wrapper sessions-table-wrapper">
        <h3 style={{ margin: '0 0 20px 0', color: '#66FCF1' }}>История сессий</h3>
        <table style={tableStyle}>
          <thead>
            <tr style={tableHeaderStyle}>
              <th style={thStyle}>Дата</th>
              <th style={thStyle}>Лимит</th>
              <th style={thStyle}>Длительность</th>
              <th style={thStyle}>Раздачи</th>
              <th style={thStyle}>Винрейт</th>
              <th style={thStyle}>Рейк</th>
              <th style={thStyle}>Статус</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((session) => (
              <tr key={session.session_id} style={tableRowStyle}>
                <td style={tdStyle}>{formatDate(session.period_start)}</td>
                <td style={tdStyle}><span style={limitBadgeStyle}>{session.limit_type}</span></td>
                <td style={tdStyle}>{formatDuration(session.period_start, session.period_end)}</td>
                <td style={tdStyle}>{session.hands_played}</td>
                <td style={tdStyle}>
                  {(session.winrate_bb_100 || session.profit_bb_100 || 0).toFixed(2)} bb/100
                </td>
                <td style={tdStyle}>${(session.total_rake || 0).toFixed(2)}</td>
                <td style={tdStyle}>
                  {!session.period_end ? (
                    <span style={liveBadgeStyle}>ОНЛАЙН</span>
                  ) : (
                    <span style={completedBadgeStyle}>Завершена</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const pageStyle: React.CSSProperties = { padding: '12px' };
const loadingStyle: React.CSSProperties = { textAlign: 'center', padding: '50px', color: '#C5C6C7' };
const headerStyle: React.CSSProperties = { 
  display: 'flex', 
  flexDirection: 'column',
  justifyContent: 'space-between', 
  alignItems: 'flex-start', 
  gap: '12px',
  marginBottom: '24px', 
  padding: '16px', 
  background: '#1F2833', 
  borderRadius: '8px' 
};
const actionsStyle: React.CSSProperties = { display: 'flex', gap: '10px' };
const startGroupStyle: React.CSSProperties = { 
  display: 'flex', 
  flexDirection: 'column',
  gap: '10px',
  width: '100%'
};

// Add responsive styles
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .session-start-group {
        flex-direction: row !important;
      }
    }
  `;
  document.head.appendChild(style);
}
const startButtonStyle: React.CSSProperties = { 
  padding: '10px 20px', 
  background: '#45A29E', 
  border: 'none', 
  borderRadius: '4px', 
  color: '#FFFFFF', 
  cursor: 'pointer', 
  fontWeight: 'bold',
  width: '100%'
};
const endButtonStyle: React.CSSProperties = { 
  padding: '10px 20px', 
  background: '#F44336', 
  border: 'none', 
  borderRadius: '4px', 
  color: '#FFFFFF', 
  cursor: 'pointer', 
  fontWeight: 'bold',
  width: '100%'
};
const activeCardStyle: React.CSSProperties = { background: 'linear-gradient(135deg, #1F2833 0%, #0B0C10 100%)', border: '2px solid #66FCF1', borderRadius: '12px', padding: '25px', marginBottom: '30px' };
const activeHeaderStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '20px' };
const activeBadgeStyle: React.CSSProperties = { background: '#4CAF50', color: '#FFFFFF', padding: '5px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: 'bold' };
const activeStatsStyle: React.CSSProperties = { 
  display: 'grid', 
  gridTemplateColumns: 'repeat(2, 1fr)', 
  gap: '16px' 
};

// Add responsive stats grid
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 768px) {
      .session-active-stats {
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 20px !important;
      }
    }
  `;
  document.head.appendChild(style);
}
const activeStatStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '5px' };
const labelStyle: React.CSSProperties = { color: '#C5C6C7', fontSize: '14px' };
const valueStyle: React.CSSProperties = { color: '#66FCF1', fontSize: '24px', fontWeight: 'bold' };
const tableContainerStyle: React.CSSProperties = { 
  background: '#1F2833', 
  borderRadius: '8px', 
  padding: '16px',
  overflowX: 'auto'
};

// Add responsive table wrapper class
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (max-width: 639px) {
      .sessions-table-wrapper table {
        font-size: 12px !important;
        min-width: 600px;
      }
      .sessions-table-wrapper th,
      .sessions-table-wrapper td {
        padding: 8px 4px !important;
      }
    }
  `;
  document.head.appendChild(style);
}
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse' };
const tableHeaderStyle: React.CSSProperties = { background: '#0B0C10' };
const thStyle: React.CSSProperties = { padding: '15px', textAlign: 'left', color: '#66FCF1', fontWeight: 'bold' };
const tableRowStyle: React.CSSProperties = { borderBottom: '1px solid #45A29E' };
const tdStyle: React.CSSProperties = { padding: '12px 15px', color: '#C5C6C7' };
const limitBadgeStyle: React.CSSProperties = { background: '#45A29E', padding: '4px 10px', borderRadius: '4px', fontSize: '12px' };
const liveBadgeStyle: React.CSSProperties = { color: '#4CAF50', fontWeight: 'bold' };
const completedBadgeStyle: React.CSSProperties = { color: '#C5C6C7' };

export default SessionsPage;
