/**
 * Admin страница для управления ботами
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/api';

const AdminBotsPage: React.FC = () => {
  const [bots, setBots] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    alias: '',
    default_style: 'balanced',
    default_limit: 'NL10',
    active: true
  });

  useEffect(() => {
    loadBots();
  }, []);

  const loadBots = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getBots();
      setBots(data);
    } catch (error) {
      console.error('Error loading bots:', error);
      alert('Ошибка загрузки ботов');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await apiClient.createBot(formData);
      setShowForm(false);
      setFormData({ alias: '', default_style: 'balanced', default_limit: 'NL10', active: true });
      loadBots();
    } catch (error) {
      console.error('Error creating bot:', error);
      alert('Ошибка создания бота');
    }
  };

  const handleToggleActive = async (botId: number, currentActive: boolean) => {
    try {
      await apiClient.updateBot(botId, { active: !currentActive });
      loadBots();
    } catch (error) {
      console.error('Error updating bot:', error);
      alert('Ошибка обновления бота');
    }
  };

  if (loading) {
    return <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>Загрузка...</div>;
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Управление ботами</h1>
        <button onClick={() => setShowForm(!showForm)} style={buttonStyle}>
          {showForm ? 'Отмена' : '+ Добавить бота'}
        </button>
      </div>

      {showForm && (
        <div style={formStyle}>
          <h3 style={{ color: '#66FCF1', marginTop: 0 }}>Создать бота</h3>
          <input
            type="text"
            placeholder="Alias (имя бота)"
            value={formData.alias}
            onChange={(e) => setFormData({ ...formData, alias: e.target.value })}
            style={inputStyle}
          />
          <select
            value={formData.default_style}
            onChange={(e) => setFormData({ ...formData, default_style: e.target.value })}
            style={inputStyle}
          >
            <option value="tight">Tight</option>
            <option value="balanced">Balanced</option>
            <option value="loose">Loose</option>
            <option value="aggressive">Aggressive</option>
          </select>
          <select
            value={formData.default_limit}
            onChange={(e) => setFormData({ ...formData, default_limit: e.target.value })}
            style={inputStyle}
          >
            <option value="NL10">NL10</option>
            <option value="NL25">NL25</option>
            <option value="NL50">NL50</option>
            <option value="NL100">NL100</option>
          </select>
          <button onClick={handleCreate} style={buttonStyle}>
            Создать
          </button>
        </div>
      )}

      <div style={listStyle}>
        {bots.map((bot) => (
          <div key={bot.id} style={cardStyle}>
            <div style={cardHeaderStyle}>
              <span style={{ color: '#66FCF1', fontWeight: 'bold', fontSize: '18px' }}>{bot.alias}</span>
              <button
                onClick={() => handleToggleActive(bot.id, bot.active)}
                style={{
                  ...buttonStyle,
                  background: bot.active ? '#45A29E' : '#C5C6C7',
                  fontSize: '12px',
                  padding: '6px 12px'
                }}
              >
                {bot.active ? 'Активен' : 'Неактивен'}
              </button>
            </div>
            <div style={{ color: '#C5C6C7', fontSize: '14px', marginTop: '10px' }}>
              <div>Стиль: {bot.default_style}</div>
              <div>Лимит: {bot.default_limit}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const containerStyle: React.CSSProperties = {
  padding: '20px',
  maxWidth: '1200px',
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
  gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
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

export default AdminBotsPage;
