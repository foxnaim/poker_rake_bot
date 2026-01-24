/**
 * Admin страница для управления моделями рейка
 */

import React, { useState, useEffect } from 'react';
import api from '../services/axiosConfig';
import { addResponsiveStyles } from '../utils/responsiveStyles';

// Initialize responsive styles
if (typeof document !== 'undefined') {
  addResponsiveStyles();
}

const AdminRakeModelsPage: React.FC = () => {
  const [models, setModels] = useState<any[]>([]);
  const [rooms, setRooms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingModel, setEditingModel] = useState<any | null>(null);
  const [roomFilter, setRoomFilter] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    room_id: null as number | null,
    limit_type: null as string | null,
    percent: 5.0,
    cap: null as number | null,
    min_pot: 0,
    params: null
  });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadModels();
  }, [roomFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [modelsRes, roomsRes] = await Promise.all([
        api.get("/api/v1/admin/rake-models"),
        api.get("/api/v1/admin/rooms")
      ]);
      setModels(modelsRes.data || []);
      setRooms(roomsRes.data || []);
    } catch (error: any) {
      console.error('Error loading data:', error);
      setModels([]);
      setRooms([]);
      alert('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async () => {
    try {
      const response = roomFilter
        ? await api.get(`/api/v1/admin/rake-models?room_id=${roomFilter}`)
        : await api.get("/api/v1/admin/rake-models");
      setModels(response.data || []);
    } catch (error: any) {
      console.error('Error loading models:', error);
      setModels([]);
      alert('Ошибка загрузки моделей');
    }
  };

  const handleCreate = async () => {
    try {
      await api.post("/api/v1/admin/rake-models", formData);
      setShowForm(false);
      resetForm();
      loadModels();
    } catch (error: any) {
      console.error('Error creating model:', error);
      alert(error.message || 'Ошибка создания модели');
    }
  };

  const handleUpdate = async () => {
    if (!editingModel) return;
    
    try {
      await api.patch(`/api/v1/admin/rake-models/${editingModel.id}`, formData);
      setEditingModel(null);
      resetForm();
      loadModels();
    } catch (error: any) {
      console.error('Error updating model:', error);
      alert(error.message || 'Ошибка обновления модели');
    }
  };

  const handleEdit = (model: any) => {
    setEditingModel(model);
    setFormData({
      room_id: model.room_id,
      limit_type: model.limit_type,
      percent: model.percent,
      cap: model.cap,
      min_pot: model.min_pot || 0,
      params: model.params
    });
    setShowForm(true);
  };

  const handleDelete = async (modelId: number) => {
    if (!window.confirm('Удалить эту модель рейка?')) return;
    
    try {
      await api.delete(`/api/v1/admin/rake-models/${modelId}`);
      loadModels();
    } catch (error) {
      console.error('Error deleting model:', error);
      alert('Ошибка удаления модели');
    }
  };

  const resetForm = () => {
    setFormData({
      room_id: null,
      limit_type: null,
      percent: 5.0,
      cap: null,
      min_pot: 0,
      params: null
    });
  };

  const filteredModels = roomFilter 
    ? models.filter(m => m.room_id === roomFilter)
    : models;

  if (loading) {
    return <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>Загрузка...</div>;
  }

  return (
    <div style={containerStyle} className="admin-page-container">
      <div style={headerStyle} className="admin-page-header">
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Управление моделями рейка</h1>
        <button onClick={() => {
          setShowForm(!showForm);
          setEditingModel(null);
          resetForm();
        }} style={buttonStyle} className="admin-button">
          {showForm ? 'Отмена' : '+ Создать модель'}
        </button>
      </div>

      <div style={filtersStyle} className="admin-form-row">
        <label style={{ color: '#C5C6C7', marginRight: '10px' }}>Фильтр по комнате:</label>
        <select
          value={roomFilter || ''}
          onChange={(e) => setRoomFilter(e.target.value ? parseInt(e.target.value) : null)}
          style={selectStyle}
          className="admin-input admin-select-filter"
        >
          <option value="">Все комнаты</option>
          {rooms.map(room => (
            <option key={room.id} value={room.id}>
              {room.type} - {room.room_link.substring(0, 50)}...
            </option>
          ))}
        </select>
      </div>

      {showForm && (
        <div style={formStyle}>
          <h3 style={{ color: '#66FCF1', marginTop: 0 }}>
            {editingModel ? 'Редактировать модель' : 'Создать модель'}
          </h3>
          <select
            value={formData.room_id || ''}
            onChange={(e) => setFormData({ ...formData, room_id: e.target.value ? parseInt(e.target.value) : null })}
            style={inputStyle}
            className="admin-input"
            disabled={!!editingModel}
          >
            <option value="">Все комнаты (NULL)</option>
            {rooms.map(room => (
              <option key={room.id} value={room.id}>
                {room.type} - {room.room_link.substring(0, 50)}...
              </option>
            ))}
          </select>
          <select
            value={formData.limit_type || ''}
            onChange={(e) => setFormData({ ...formData, limit_type: e.target.value || null })}
            style={inputStyle}
            className="admin-input"
          >
            <option value="">Все лимиты (NULL)</option>
            <option value="NL10">NL10</option>
            <option value="NL25">NL25</option>
            <option value="NL50">NL50</option>
            <option value="NL100">NL100</option>
            <option value="NL200">NL200</option>
          </select>
          <div style={rowStyle}>
            <div style={colStyle} className="admin-form-col">
              <label style={{ color: '#C5C6C7', fontSize: '12px', marginBottom: '5px' }}>Процент рейка (%)</label>
              <input
                type="number"
                step="0.01"
                value={formData.percent}
                onChange={(e) => setFormData({ ...formData, percent: parseFloat(e.target.value) })}
                style={inputStyle}
                className="admin-input"
              />
            </div>
            <div style={colStyle} className="admin-form-col">
              <label style={{ color: '#C5C6C7', fontSize: '12px', marginBottom: '5px' }}>Макс. рейк (Cap)</label>
              <input
                type="number"
                step="0.01"
                placeholder="Опционально"
                value={formData.cap || ''}
                onChange={(e) => setFormData({ ...formData, cap: e.target.value ? parseFloat(e.target.value) : null })}
                style={inputStyle}
                className="admin-input"
              />
            </div>
            <div style={colStyle} className="admin-form-col">
              <label style={{ color: '#C5C6C7', fontSize: '12px', marginBottom: '5px' }}>Мин. банк</label>
              <input
                type="number"
                step="0.01"
                value={formData.min_pot}
                onChange={(e) => setFormData({ ...formData, min_pot: parseFloat(e.target.value) })}
                style={inputStyle}
                className="admin-input"
              />
            </div>
          </div>
          <button 
            onClick={editingModel ? handleUpdate : handleCreate} 
            style={buttonStyle}
            className="admin-button"
          >
            {editingModel ? 'Сохранить' : 'Создать'}
          </button>
        </div>
      )}

      <div style={listStyle} className="admin-list-grid">
        {filteredModels.map((model) => {
          const room = rooms.find(r => r.id === model.room_id);
          return (
            <div key={model.id} style={cardStyle} className="admin-card">
              <div style={cardHeaderStyle} className="admin-card-header">
                <div>
                  <span style={{ color: '#66FCF1', fontWeight: 'bold', fontSize: '18px' }}>
                    {model.room_id ? (room?.type || `Комната ${model.room_id}`) : 'Глобальная'}
                    {model.limit_type && ` - ${model.limit_type}`}
                  </span>
                </div>
                <div>
                  <button
                    onClick={() => handleEdit(model)}
                    style={{...buttonStyle, fontSize: '12px', padding: '6px 12px', marginRight: '8px', width: 'auto'}}
                    className="admin-button"
                  >
                    Редактировать
                  </button>
                  <button
                    onClick={() => handleDelete(model.id)}
                    style={{...buttonStyle, background: '#ff4444', fontSize: '12px', padding: '6px 12px', width: 'auto'}}
                    className="admin-button"
                  >
                    Удалить
                  </button>
                </div>
              </div>
              <div style={{ color: '#C5C6C7', fontSize: '14px', marginTop: '10px' }}>
                <div>Процент: {model.percent}%</div>
                {model.cap && <div>Макс. рейк: ${model.cap.toFixed(2)}</div>}
                <div>Мин. банк: ${model.min_pot?.toFixed(2) || '0.00'}</div>
                {model.params && (
                  <div style={{ fontSize: '12px', marginTop: '8px', opacity: 0.7 }}>
                    Параметры: {JSON.stringify(model.params)}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {filteredModels.length === 0 && (
          <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>
            Нет моделей рейка {roomFilter ? 'для выбранной комнаты' : ''}
          </div>
        )}
      </div>
    </div>
  );
};

const containerStyle: React.CSSProperties = {
  padding: '12px',
  maxWidth: '1200px',
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

// Add responsive button group
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
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

// Add responsive styles
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .admin-form-row {
        flex-direction: row !important;
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

export default AdminRakeModelsPage;
