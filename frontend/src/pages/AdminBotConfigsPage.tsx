/**
 * Admin страница для управления конфигурациями ботов
 */

import React, { useState, useEffect } from 'react';
import api from '../services/axiosConfig';
import { addResponsiveStyles } from '../utils/responsiveStyles';

// Initialize responsive styles
if (typeof document !== 'undefined') {
  addResponsiveStyles();
}

const AdminBotConfigsPage: React.FC = () => {
  const [configs, setConfigs] = useState<any[]>([]);
  const [bots, setBots] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingConfig, setEditingConfig] = useState<any | null>(null);
  const [botFilter, setBotFilter] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    bot_id: 0,
    name: '',
    target_vpip: 20.0,
    target_pfr: 15.0,
    target_af: 2.0,
    exploit_weights: {
      preflop: 0.3,
      flop: 0.4,
      turn: 0.5,
      river: 0.6
    },
    max_winrate_cap: null as number | null,
    anti_pattern_params: null,
    limit_types: null as string[] | null,
    is_default: false
  });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadConfigs();
  }, [botFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [configsRes, botsRes] = await Promise.all([
        api.get("/api/v1/admin/bot-configs"),
        api.get("/api/v1/admin/bots")
      ]);
      setConfigs(configsRes.data || []);
      setBots(botsRes.data || []);
    } catch (error: any) {
      console.error('Error loading data:', error);
      setConfigs([]);
      setBots([]);
      alert('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const loadConfigs = async () => {
    try {
      const response = botFilter
        ? await api.get(`/api/v1/admin/bot-configs?bot_id=${botFilter}`)
        : await api.get("/api/v1/admin/bot-configs");
      setConfigs(response.data || []);
    } catch (error: any) {
      console.error('Error loading configs:', error);
      setConfigs([]);
      alert('Ошибка загрузки конфигов');
    }
  };

  const handleCreate = async () => {
    try {
      await api.post("/api/v1/admin/bot-configs", formData);
      setShowForm(false);
      resetForm();
      loadConfigs();
    } catch (error: any) {
      console.error('Error creating config:', error);
      alert(error.message || 'Ошибка создания конфига');
    }
  };

  const handleUpdate = async () => {
    if (!editingConfig) return;
    
    try {
      await api.patch(`/api/v1/admin/bot-configs/${editingConfig.id}`, formData);
      setEditingConfig(null);
      resetForm();
      loadConfigs();
    } catch (error: any) {
      console.error('Error updating config:', error);
      alert(error.message || 'Ошибка обновления конфига');
    }
  };

  const handleEdit = (config: any) => {
    setEditingConfig(config);
    setFormData({
      bot_id: config.bot_id,
      name: config.name,
      target_vpip: config.target_vpip,
      target_pfr: config.target_pfr,
      target_af: config.target_af,
      exploit_weights: config.exploit_weights,
      max_winrate_cap: config.max_winrate_cap,
      anti_pattern_params: config.anti_pattern_params,
      limit_types: config.limit_types,
      is_default: config.is_default
    });
    setShowForm(true);
  };

  const handleDelete = async (configId: number) => {
    if (!window.confirm('Удалить этот конфиг?')) return;
    
    try {
      await api.delete(`/api/v1/admin/bot-configs/${configId}`);
      loadConfigs();
    } catch (error) {
      console.error('Error deleting config:', error);
      alert('Ошибка удаления конфига');
    }
  };

  const resetForm = () => {
    setFormData({
      bot_id: 0,
      name: '',
      target_vpip: 20.0,
      target_pfr: 15.0,
      target_af: 2.0,
      exploit_weights: {
        preflop: 0.3,
        flop: 0.4,
        turn: 0.5,
        river: 0.6
      },
      max_winrate_cap: null,
      anti_pattern_params: null,
      limit_types: null,
      is_default: false
    });
  };

  const filteredConfigs = botFilter 
    ? configs.filter(c => c.bot_id === botFilter)
    : configs;

  if (loading) {
    return <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>Загрузка...</div>;
  }

  return (
    <div style={containerStyle} className="admin-page-container">
      <div style={headerStyle} className="admin-page-header">
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Управление конфигурациями ботов</h1>
        <button onClick={() => {
          setShowForm(!showForm);
          setEditingConfig(null);
          resetForm();
        }} style={buttonStyle} className="admin-button">
          {showForm ? 'Отмена' : '+ Создать конфиг'}
        </button>
      </div>

      <div style={filtersStyle}>
        <label style={{ color: '#C5C6C7', marginRight: '10px' }}>Фильтр по боту:</label>
        <select
          value={botFilter || ''}
          onChange={(e) => setBotFilter(e.target.value ? parseInt(e.target.value) : null)}
          style={selectStyle}
        >
          <option value="">Все боты</option>
          {bots.map(bot => (
            <option key={bot.id} value={bot.id}>{bot.alias}</option>
          ))}
        </select>
      </div>

      {showForm && (
        <div style={formStyle}>
          <h3 style={{ color: '#66FCF1', marginTop: 0 }}>
            {editingConfig ? 'Редактировать конфиг' : 'Создать конфиг'}
          </h3>
          <select
            value={formData.bot_id}
            onChange={(e) => setFormData({ ...formData, bot_id: parseInt(e.target.value) })}
            style={inputStyle}
            className="admin-input"
            disabled={!!editingConfig}
          >
            <option value={0}>Выберите бота</option>
            {bots.map(bot => (
              <option key={bot.id} value={bot.id}>{bot.alias}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Название конфига"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            style={inputStyle}
          />
          <div style={rowStyle}>
            <div style={colStyle} className="admin-form-col">
              <label style={{ color: '#C5C6C7', fontSize: '12px', marginBottom: '5px' }}>Целевой VPIP</label>
              <input
                type="number"
                step="0.1"
                value={formData.target_vpip}
                onChange={(e) => setFormData({ ...formData, target_vpip: parseFloat(e.target.value) })}
                style={inputStyle}
                className="admin-input"
              />
            </div>
            <div style={colStyle} className="admin-form-col">
              <label style={{ color: '#C5C6C7', fontSize: '12px', marginBottom: '5px' }}>Целевой PFR</label>
              <input
                type="number"
                step="0.1"
                value={formData.target_pfr}
                onChange={(e) => setFormData({ ...formData, target_pfr: parseFloat(e.target.value) })}
                style={inputStyle}
                className="admin-input"
              />
            </div>
            <div style={colStyle} className="admin-form-col">
              <label style={{ color: '#C5C6C7', fontSize: '12px', marginBottom: '5px' }}>Целевой AF</label>
              <input
                type="number"
                step="0.1"
                value={formData.target_af}
                onChange={(e) => setFormData({ ...formData, target_af: parseFloat(e.target.value) })}
                style={inputStyle}
                className="admin-input"
              />
            </div>
          </div>
          <div style={sectionStyle}>
            <label style={{ color: '#66FCF1', marginBottom: '10px', display: 'block' }}>Веса эксплойта:</label>
            {Object.entries(formData.exploit_weights).map(([street, weight]) => {
              const streetNames: {[key: string]: string} = {
                preflop: 'Префлоп',
                flop: 'Флоп',
                turn: 'Тёрн',
                river: 'Ривер'
              };
              return (
              <div key={street} style={rowStyle} className="admin-form-row">
                <label style={{ color: '#C5C6C7', width: '100%', marginBottom: '4px' }}>{streetNames[street] || street}:</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={weight}
                  onChange={(e) => setFormData({
                    ...formData,
                    exploit_weights: {
                      ...formData.exploit_weights,
                      [street]: parseFloat(e.target.value)
                    }
                  })}
                  style={{...inputStyle, width: '100%'}}
                  className="admin-input"
                />
              </div>
            );
            })}
          </div>
          <input
            type="number"
            placeholder="Макс. винрейт (bb/100, опционально)"
            value={formData.max_winrate_cap || ''}
            onChange={(e) => setFormData({ 
              ...formData, 
              max_winrate_cap: e.target.value ? parseFloat(e.target.value) : null 
            })}
            style={inputStyle}
            className="admin-input"
          />
          <label style={{ color: '#C5C6C7', display: 'flex', alignItems: 'center', marginTop: '10px' }}>
            <input
              type="checkbox"
              checked={formData.is_default}
              onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
              style={{ marginRight: '10px' }}
            />
            Использовать как конфиг по умолчанию
          </label>
          <button 
            onClick={editingConfig ? handleUpdate : handleCreate} 
            style={buttonStyle}
            className="admin-button"
            disabled={!formData.bot_id || !formData.name}
          >
            {editingConfig ? 'Сохранить' : 'Создать'}
          </button>
        </div>
      )}

      <div style={listStyle} className="admin-list-grid">
        {filteredConfigs.map((config) => {
          const bot = bots.find(b => b.id === config.bot_id);
          return (
            <div key={config.id} style={cardStyle} className="admin-card">
              <div style={cardHeaderStyle} className="admin-card-header">
                <div>
                  <span style={{ color: '#66FCF1', fontWeight: 'bold', fontSize: '18px' }}>
                    {config.name}
                    {config.is_default && (
                      <span style={{ 
                        background: '#45A29E', 
                        color: '#0B0C10',
                        padding: '2px 6px',
                        borderRadius: '3px',
                        fontSize: '10px',
                        marginLeft: '8px'
                      }}>
                        ПО УМОЛЧАНИЮ
                      </span>
                    )}
                  </span>
                  <div style={{ color: '#C5C6C7', fontSize: '12px', marginTop: '4px' }}>
                    Бот: {bot?.alias || `ID ${config.bot_id}`}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }} className="admin-button-group">
                  <button
                    onClick={() => handleEdit(config)}
                    style={{...buttonStyle, fontSize: '12px', padding: '6px 12px', width: '100%'}}
                    className="admin-button"
                  >
                    Редактировать
                  </button>
                  <button
                    onClick={() => handleDelete(config.id)}
                    style={{...buttonStyle, background: '#ff4444', fontSize: '12px', padding: '6px 12px', width: '100%'}}
                    className="admin-button"
                  >
                    Удалить
                  </button>
                </div>
              </div>
              <div style={{ color: '#C5C6C7', fontSize: '14px', marginTop: '10px' }}>
                <div>VPIP: {config.target_vpip}% | PFR: {config.target_pfr}% | AF: {config.target_af}</div>
                <div style={{ fontSize: '12px', marginTop: '8px' }}>
                  Веса эксплойта: {JSON.stringify(config.exploit_weights)}
                </div>
                {config.max_winrate_cap && (
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>
                    Макс. винрейт: {config.max_winrate_cap} bb/100
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {filteredConfigs.length === 0 && (
          <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>
            Нет конфигов {botFilter ? 'для выбранного бота' : ''}
          </div>
        )}
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

const filtersStyle: React.CSSProperties = {
  marginBottom: '20px',
  padding: '15px',
  background: '#1F2833',
  borderRadius: '8px',
  border: '1px solid #C5C6C7',
  display: 'flex',
  flexDirection: 'column',
  gap: '10px',
  alignItems: 'stretch'
};

const selectStyle: React.CSSProperties = {
  padding: '8px 12px',
  background: '#0B0C10',
  border: '1px solid #C5C6C7',
  borderRadius: '4px',
  color: '#FFFFFF',
  fontSize: '14px',
  minWidth: '100%',
  width: '100%'
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

const rowStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '10px',
  marginBottom: '10px'
};

const colStyle: React.CSSProperties = {
  flex: 1,
  width: '100%'
};

const sectionStyle: React.CSSProperties = {
  background: '#0B0C10',
  padding: '15px',
  borderRadius: '4px',
  marginBottom: '10px'
};

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

// Add responsive styles
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .admin-card-header {
        flex-direction: row !important;
        align-items: flex-start !important;
      }
      .admin-button-group {
        flex-direction: row !important;
        width: auto !important;
      }
      .admin-button-group .admin-button {
        width: auto !important;
      }
    }
  `;
  document.head.appendChild(style);
}

export default AdminBotConfigsPage;
