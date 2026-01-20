/**
 * Sessions Page - управление игровыми сессиями
 */

import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface Session {
  session_id: string;
  limit_type: string;
  period_start: string;
  period_end: string | null;
  hands_played: number;
  winrate_bb_100: number;
  total_rake: number;
  is_active: boolean;
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
      const response = await axios.get('/api/v1/sessions/recent?limit=50');
      setSessions(response.data);
      const active = response.data.find((s: Session) => s.is_active);
      setActiveSession(active || null);
    } catch (error) {
      console.error('Error fetching sessions:', error);
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
    return <div style={loadingStyle}>Loading sessions...</div>;
  }

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <h1 style={{ margin: 0 }}>Game Sessions</h1>
        <div style={actionsStyle}>
          {activeSession ? (
            <button onClick={endSession} style={endButtonStyle}>
              End Session
            </button>
          ) : (
            <div style={startGroupStyle}>
              {['NL2', 'NL5', 'NL10', 'NL25', 'NL50'].map(limit => (
                <button
                  key={limit}
                  onClick={() => startSession(limit)}
                  style={startButtonStyle}
                >
                  Start {limit}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {activeSession && (
        <div style={activeCardStyle}>
          <div style={activeHeaderStyle}>
            <span style={activeBadgeStyle}>LIVE</span>
            <h2 style={{ margin: 0 }}>Active Session: {activeSession.limit_type}</h2>
          </div>
          <div style={activeStatsStyle}>
            <div style={activeStatStyle}>
              <span style={labelStyle}>Duration</span>
              <span style={valueStyle}>{formatDuration(activeSession.period_start, null)}</span>
            </div>
            <div style={activeStatStyle}>
              <span style={labelStyle}>Hands</span>
              <span style={valueStyle}>{activeSession.hands_played}</span>
            </div>
            <div style={activeStatStyle}>
              <span style={labelStyle}>Winrate</span>
              <span style={valueStyle}>
                {activeSession.winrate_bb_100.toFixed(2)} bb/100
              </span>
            </div>
            <div style={activeStatStyle}>
              <span style={labelStyle}>Rake</span>
              <span style={valueStyle}>${activeSession.total_rake.toFixed(2)}</span>
            </div>
          </div>
        </div>
      )}

      <div style={tableContainerStyle}>
        <h3 style={{ margin: '0 0 20px 0', color: '#66FCF1' }}>Session History</h3>
        <table style={tableStyle}>
          <thead>
            <tr style={tableHeaderStyle}>
              <th style={thStyle}>Date</th>
              <th style={thStyle}>Limit</th>
              <th style={thStyle}>Duration</th>
              <th style={thStyle}>Hands</th>
              <th style={thStyle}>Winrate</th>
              <th style={thStyle}>Rake</th>
              <th style={thStyle}>Status</th>
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
                  {session.winrate_bb_100.toFixed(2)} bb/100
                </td>
                <td style={tdStyle}>${session.total_rake.toFixed(2)}</td>
                <td style={tdStyle}>
                  {session.is_active ? (
                    <span style={liveBadgeStyle}>LIVE</span>
                  ) : (
                    <span style={completedBadgeStyle}>Completed</span>
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

const pageStyle: React.CSSProperties = { padding: '20px' };
const loadingStyle: React.CSSProperties = { textAlign: 'center', padding: '50px', color: '#C5C6C7' };
const headerStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px', padding: '20px', background: '#1F2833', borderRadius: '8px' };
const actionsStyle: React.CSSProperties = { display: 'flex', gap: '10px' };
const startGroupStyle: React.CSSProperties = { display: 'flex', gap: '10px' };
const startButtonStyle: React.CSSProperties = { padding: '10px 20px', background: '#45A29E', border: 'none', borderRadius: '4px', color: '#FFFFFF', cursor: 'pointer', fontWeight: 'bold' };
const endButtonStyle: React.CSSProperties = { padding: '10px 20px', background: '#F44336', border: 'none', borderRadius: '4px', color: '#FFFFFF', cursor: 'pointer', fontWeight: 'bold' };
const activeCardStyle: React.CSSProperties = { background: 'linear-gradient(135deg, #1F2833 0%, #0B0C10 100%)', border: '2px solid #66FCF1', borderRadius: '12px', padding: '25px', marginBottom: '30px' };
const activeHeaderStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '20px' };
const activeBadgeStyle: React.CSSProperties = { background: '#4CAF50', color: '#FFFFFF', padding: '5px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: 'bold' };
const activeStatsStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' };
const activeStatStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '5px' };
const labelStyle: React.CSSProperties = { color: '#C5C6C7', fontSize: '14px' };
const valueStyle: React.CSSProperties = { color: '#66FCF1', fontSize: '24px', fontWeight: 'bold' };
const tableContainerStyle: React.CSSProperties = { background: '#1F2833', borderRadius: '8px', padding: '20px' };
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse' };
const tableHeaderStyle: React.CSSProperties = { background: '#0B0C10' };
const thStyle: React.CSSProperties = { padding: '15px', textAlign: 'left', color: '#66FCF1', fontWeight: 'bold' };
const tableRowStyle: React.CSSProperties = { borderBottom: '1px solid #45A29E' };
const tdStyle: React.CSSProperties = { padding: '12px 15px', color: '#C5C6C7' };
const limitBadgeStyle: React.CSSProperties = { background: '#45A29E', padding: '4px 10px', borderRadius: '4px', fontSize: '12px' };
const liveBadgeStyle: React.CSSProperties = { color: '#4CAF50', fontWeight: 'bold' };
const completedBadgeStyle: React.CSSProperties = { color: '#C5C6C7' };

export default SessionsPage;
