/**
 * Admin страница для управления моделями рейка
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/api';

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
      const [modelsData, roomsData] = await Promise.all([
        apiClient.getRakeModels(),
        apiClient.getRooms()
      ]);
      setModels(modelsData);
      setRooms(roomsData);
    } catch (error) {
      console.error('Error loading data:', error);
      alert('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async () => {
    try {
      const data = roomFilter 
        ? await apiClient.getRakeModels(roomFilter)
        : await apiClient.getRakeModels();
      setModels(data);
    } catch (error) {
      console.error('Error loading models:', error);
      alert('Ошибка загрузки моделей');
    }
  };

  const handleCreate = async () => {
    try {
      await apiClient.createRakeModel(formData);
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
      await apiClient.updateRakeModel(editingModel.id, formData);
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
      await apiClient.deleteRakeModel(modelId);
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
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Управление моделями рейка</h1>
        <button onClick={() => {
          setShowForm(!showForm);
          setEditingModel(null);
          resetForm();
        }} style={buttonStyle}>
          {showForm ? 'Отмена' : '+ Создать модель'}
        </button>
      </div>

      <div style={filtersStyle}>
        <label style={{ color: '#C5C6C7', marginRight: '10px' }}>Фильтр по комнате:</label>
        <select
          value={roomFilter || ''}
          onChange={(e) => setRoomFilter(e.target.value ? parseInt(e.target.value) : null)}
          style={selectStyle}
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
          >
            <option value="">Все лимиты (NULL)</option>
            <option value="NL10">NL10</option>
            <option value="NL25">NL25</option>
            <option value="NL50">NL50</option>
            <option value="NL100">NL100</option>
            <option value="NL200">NL200</option>
          </select>
          <div style={rowStyle}>
            <div style={colStyle}>
              <label style={{ color: '#C5C6C7', fontSize: '12px', marginBottom: '5px' }}>Процент рейка (%)</label>
              <input
                type="number"
                step="0.01"
                value={formData.percent}
                onChange={(e) => setFormData({ ...formData, percent: parseFloat(e.target.value) })}
                style={inputStyle}
              />
            </div>
            <div style={colStyle}>
              <label style={{ color: '#C5C6C7', fontSize: '12px', marginBottom: '5px' }}>Cap (макс. рейк)</label>
              <input
                type="number"
                step="0.01"
                placeholder="Опционально"
                value={formData.cap || ''}
                onChange={(e) => setFormData({ ...formData, cap: e.target.value ? parseFloat(e.target.value) : null })}
                style={inputStyle}
              />
            </div>
            <div style={colStyle}>
              <label style={{ color: '#C5C6C7', fontSize: '12px', marginBottom: '5px' }}>Мин. банк</label>
              <input
                type="number"
                step="0.01"
                value={formData.min_pot}
                onChange={(e) => setFormData({ ...formData, min_pot: parseFloat(e.target.value) })}
                style={inputStyle}
              />
            </div>
          </div>
          <button 
            onClick={editingModel ? handleUpdate : handleCreate} 
            style={buttonStyle}
          >
            {editingModel ? 'Сохранить' : 'Создать'}
          </button>
        </div>
      )}

      <div style={listStyle}>
        {filteredModels.map((model) => {
          const room = rooms.find(r => r.id === model.room_id);
          return (
            <div key={model.id} style={cardStyle}>
              <div style={cardHeaderStyle}>
                <div>
                  <span style={{ color: '#66FCF1', fontWeight: 'bold', fontSize: '18px' }}>
                    {model.room_id ? (room?.type || `Комната ${model.room_id}`) : 'Глобальная'}
                    {model.limit_type && ` - ${model.limit_type}`}
                  </span>
                </div>
                <div>
                  <button
                    onClick={() => handleEdit(model)}
                    style={{...buttonStyle, fontSize: '12px', padding: '6px 12px', marginRight: '8px'}}
                  >
                    Редактировать
                  </button>
                  <button
                    onClick={() => handleDelete(model.id)}
                    style={{...buttonStyle, background: '#ff4444', fontSize: '12px', padding: '6px 12px'}}
                  >
                    Удалить
                  </button>
                </div>
              </div>
              <div style={{ color: '#C5C6C7', fontSize: '14px', marginTop: '10px' }}>
                <div>Процент: {model.percent}%</div>
                {model.cap && <div>Cap: ${model.cap.toFixed(2)}</div>}
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

const filtersStyle: React.CSSProperties = {
  marginBottom: '20px',
  padding: '15px',
  background: '#1F2833',
  borderRadius: '8px',
  border: '1px solid #C5C6C7'
};

const selectStyle: React.CSSProperties = {
  padding: '8px 12px',
  background: '#0B0C10',
  border: '1px solid #C5C6C7',
  borderRadius: '4px',
  color: '#FFFFFF',
  fontSize: '14px',
  minWidth: '300px'
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

const rowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '10px',
  marginBottom: '10px'
};

const colStyle: React.CSSProperties = {
  flex: 1
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
  alignItems: 'flex-start',
  marginBottom: '10px'
};

export default AdminRakeModelsPage;
