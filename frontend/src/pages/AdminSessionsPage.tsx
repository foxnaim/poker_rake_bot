/**
 * Admin страница для управления сессиями
 */

import React, { useState, useEffect } from 'react';
import api from '../services/axiosConfig';
import { addResponsiveStyles } from '../utils/responsiveStyles';

// Initialize responsive styles
if (typeof document !== 'undefined') {
  addResponsiveStyles();
}

const AdminSessionsPage: React.FC = () => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [bots, setBots] = useState<any[]>([]);
  const [tables, setTables] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showStartForm, setShowStartForm] = useState(false);
  const [formData, setFormData] = useState({
    bot_id: 0,
    table_id: 0,
    limit: 'NL10',
    style: '',
    bot_config_id: null
  });

  useEffect(() => {
    loadData();
    const interval = setInterval(loadSessions, 5000); // Обновление каждые 5 секунд
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [sessionsRes, botsRes, tablesRes] = await Promise.all([
        api.get("/api/v1/admin/sessions/recent"),
        api.get("/api/v1/admin/bots"),
        api.get("/api/v1/admin/tables")
      ]);
      setSessions(sessionsRes.data || []);
      setBots(botsRes.data || []);
      setTables(tablesRes.data || []);
    } catch (error: any) {
      console.error('Error loading data:', error);
      setSessions([]);
      setBots([]);
      setTables([]);
      alert('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const loadSessions = async () => {
    try {
      const response = await api.get('/api/v1/admin/sessions/recent');
      setSessions(response.data || []);
    } catch (error: any) {
      console.error('Error loading sessions:', error);
      setSessions([]);
    }
  };

  const handleStart = async () => {
    try {
      await api.post("/api/v1/admin/sessions/start", formData);
      setShowStartForm(false);
      setFormData({ bot_id: 0, table_id: 0, limit: 'NL10', style: '', bot_config_id: null });
      loadSessions();
    } catch (error) {
      console.error('Error starting session:', error);
      alert('Ошибка запуска сессии');
    }
  };

  const handlePause = async (sessionId: string) => {
    try {
      await api.post(`/api/v1/admin/sessions/${sessionId}/pause`);
      loadSessions();
    } catch (error) {
      console.error('Error pausing session:', error);
      alert('Ошибка паузы сессии');
    }
  };

  const handleStop = async (sessionId: string) => {
    try {
      await api.post(`/api/v1/admin/sessions/${sessionId}/stop`);
      loadSessions();
    } catch (error) {
      console.error('Error stopping session:', error);
      alert('Ошибка остановки сессии');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return '#45A29E';
      case 'paused': return '#C5C6C7';
      case 'stopped': return '#1F2833';
      case 'error': return '#ff4444';
      default: return '#C5C6C7';
    }
  };

  if (loading) {
    return <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>Загрузка...</div>;
  }

  return (
    <div style={containerStyle} className="admin-page-container">
      <div style={headerStyle} className="admin-page-header">
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Управление сессиями</h1>
        <button onClick={() => setShowStartForm(!showStartForm)} style={buttonStyle} className="admin-button">
          {showStartForm ? 'Отмена' : '+ Запустить сессию'}
        </button>
      </div>

      {showStartForm && (
        <div style={formStyle}>
          <h3 style={{ color: '#66FCF1', marginTop: 0 }}>Запустить сессию</h3>
          <select
            value={formData.bot_id}
            onChange={(e) => setFormData({ ...formData, bot_id: parseInt(e.target.value) })}
            style={inputStyle}
            className="admin-input"
          >
            <option value={0}>Выберите бота</option>
            {bots.filter(b => b.active).map(bot => (
              <option key={bot.id} value={bot.id}>{bot.alias}</option>
            ))}
          </select>
          <select
            value={formData.table_id}
            onChange={(e) => setFormData({ ...formData, table_id: parseInt(e.target.value) })}
            style={inputStyle}
            className="admin-input"
          >
            <option value={0}>Выберите стол</option>
            {tables.map(table => (
              <option key={table.id} value={table.id}>
                Комната {table.room_id} - {table.limit_type}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Лимит (NL10, NL50 и т.д.)"
            value={formData.limit}
            onChange={(e) => setFormData({ ...formData, limit: e.target.value })}
            style={inputStyle}
            className="admin-input"
          />
          <button onClick={handleStart} style={buttonStyle} className="admin-button" disabled={!formData.bot_id || !formData.table_id}>
            Запустить
          </button>
        </div>
      )}

      <div style={listStyle} className="admin-list-grid">
        {sessions.map((session) => (
            <div key={session.id} style={cardStyle} className="admin-card">
              <div style={cardHeaderStyle} className="admin-card-header admin-session-card-header">
              <span style={{ color: '#66FCF1', fontWeight: 'bold' }}>{session.session_id}</span>
              <span style={{
                background: getStatusColor(session.status),
                color: '#0B0C10',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 'bold'
              }}>
                {session.status === 'running' ? 'Запущена' : session.status === 'paused' ? 'Приостановлена' : session.status === 'stopped' ? 'Остановлена' : session.status === 'error' ? 'Ошибка' : session.status}
              </span>
            </div>
            <div style={{ color: '#C5C6C7', fontSize: '14px', marginTop: '10px' }}>
              <div>Бот ID: {session.bot_id}</div>
              <div>Стол ID: {session.table_id}</div>
              <div>Рук сыграно: {session.hands_played}</div>
              <div>Профит: ${session.profit?.toFixed(2) || '0.00'}</div>
              <div>Винрейт: {session.bb_100?.toFixed(2) || '0.00'} bb/100</div>
              {session.last_error && (
                <div style={{ color: '#ff4444', marginTop: '8px' }}>
                  Ошибка: {session.last_error}
                </div>
              )}
            </div>
            <div style={{ marginTop: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }} className="admin-button-group">
              {session.status === 'running' && (
                <button onClick={() => handlePause(session.session_id)} style={buttonStyle} className="admin-button">
                  Пауза
                </button>
              )}
              {session.status === 'paused' && (
                <button onClick={() => handleStop(session.session_id)} style={buttonStyle} className="admin-button">
                  Остановить
                </button>
              )}
              {session.status !== 'stopped' && (
                <button onClick={() => handleStop(session.session_id)} style={{...buttonStyle, background: '#ff4444'}} className="admin-button">
                  Стоп
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const containerStyle: React.CSSProperties = {
  padding: '12px',
  maxWidth: '1400px',
  margin: '0 auto',
  width: '100%'
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: '12px',
  marginBottom: '24px'
};

const buttonStyle: React.CSSProperties = {
  background: '#66FCF1',
  color: '#0B0C10',
  border: 'none',
  padding: '10px 20px',
  borderRadius: '4px',
  cursor: 'pointer',
  fontWeight: 'bold',
  fontSize: '14px',
  width: '100%'
};

// Add responsive button group
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .admin-button-group {
        flex-direction: row !important;
      }
      .admin-button-group .admin-button {
        width: auto !important;
      }
    }
  `;
  document.head.appendChild(style);
}

const formStyle: React.CSSProperties = {
  background: '#1F2833',
  padding: '20px',
  borderRadius: '8px',
  marginBottom: '30px',
  border: '1px solid #C5C6C7'
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px',
  marginBottom: '10px',
  background: '#0B0C10',
  border: '1px solid #C5C6C7',
  borderRadius: '4px',
  color: '#FFFFFF',
  fontSize: '14px'
};

// Add responsive font size for mobile
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (max-width: 639px) {
      .admin-input {
        font-size: 16px !important;
      }
    }
  `;
  document.head.appendChild(style);
}

const listStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr',
  gap: '16px'
};

const cardStyle: React.CSSProperties = {
  background: '#1F2833',
  padding: '20px',
  borderRadius: '8px',
  border: '1px solid #C5C6C7'
};

const cardHeaderStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: '12px',
  marginBottom: '10px'
};

export default AdminSessionsPage;
