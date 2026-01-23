/**
 * Admin страница для управления сессиями
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/api';

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
      const [sessionsData, botsData, tablesData] = await Promise.all([
        apiClient.getRecentSessions(50),
        apiClient.getBots(),
        apiClient.getTables()
      ]);
      setSessions(sessionsData);
      setBots(botsData);
      setTables(tablesData);
    } catch (error) {
      console.error('Error loading data:', error);
      alert('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const loadSessions = async () => {
    try {
      const data = await apiClient.getRecentSessions(50);
      setSessions(data);
    } catch (error) {
      console.error('Error loading sessions:', error);
    }
  };

  const handleStart = async () => {
    try {
      await apiClient.startSession(formData);
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
      await apiClient.pauseSession(sessionId);
      loadSessions();
    } catch (error) {
      console.error('Error pausing session:', error);
      alert('Ошибка паузы сессии');
    }
  };

  const handleStop = async (sessionId: string) => {
    try {
      await apiClient.stopSession(sessionId);
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
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Управление сессиями</h1>
        <button onClick={() => setShowStartForm(!showStartForm)} style={buttonStyle}>
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
            placeholder="Лимит (NL10, NL50, etc.)"
            value={formData.limit}
            onChange={(e) => setFormData({ ...formData, limit: e.target.value })}
            style={inputStyle}
          />
          <button onClick={handleStart} style={buttonStyle} disabled={!formData.bot_id || !formData.table_id}>
            Запустить
          </button>
        </div>
      )}

      <div style={listStyle}>
        {sessions.map((session) => (
          <div key={session.id} style={cardStyle}>
            <div style={cardHeaderStyle}>
              <span style={{ color: '#66FCF1', fontWeight: 'bold' }}>{session.session_id}</span>
              <span style={{
                background: getStatusColor(session.status),
                color: '#0B0C10',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 'bold'
              }}>
                {session.status}
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
            <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
              {session.status === 'running' && (
                <button onClick={() => handlePause(session.session_id)} style={buttonStyle}>
                  Пауза
                </button>
              )}
              {session.status === 'paused' && (
                <button onClick={() => handleStop(session.session_id)} style={buttonStyle}>
                  Остановить
                </button>
              )}
              {session.status !== 'stopped' && (
                <button onClick={() => handleStop(session.session_id)} style={{...buttonStyle, background: '#ff4444'}}>
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
  padding: '20px',
  maxWidth: '1400px',
  margin: '0 auto'
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '30px'
};

const buttonStyle: React.CSSProperties = {
  background: '#66FCF1',
  color: '#0B0C10',
  border: 'none',
  padding: '10px 20px',
  borderRadius: '4px',
  cursor: 'pointer',
  fontWeight: 'bold',
  fontSize: '14px'
};

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

const listStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
  gap: '20px'
};

const cardStyle: React.CSSProperties = {
  background: '#1F2833',
  padding: '20px',
  borderRadius: '8px',
  border: '1px solid #C5C6C7'
};

const cardHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '10px'
};

export default AdminSessionsPage;
