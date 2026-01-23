/**
 * Admin страница для управления столами
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/api';

const AdminTablesPage: React.FC = () => {
  const [tables, setTables] = useState<any[]>([]);
  const [rooms, setRooms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [roomFilter, setRoomFilter] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    room_id: 0,
    limit_type: 'NL10',
    max_players: 6,
    meta: null
  });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadTables();
  }, [roomFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [tablesData, roomsData] = await Promise.all([
        apiClient.getTables(),
        apiClient.getRooms()
      ]);
      setTables(tablesData);
      setRooms(roomsData);
    } catch (error) {
      console.error('Error loading data:', error);
      alert('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const loadTables = async () => {
    try {
      const data = roomFilter 
        ? await apiClient.getTables(roomFilter)
        : await apiClient.getTables();
      setTables(data);
    } catch (error) {
      console.error('Error loading tables:', error);
      alert('Ошибка загрузки столов');
    }
  };

  const handleCreate = async () => {
    try {
      await apiClient.createTable(formData);
      setShowForm(false);
      setFormData({ room_id: 0, limit_type: 'NL10', max_players: 6, meta: null });
      loadTables();
    } catch (error: any) {
      console.error('Error creating table:', error);
      alert(error.message || 'Ошибка создания стола');
    }
  };

  const handleDelete = async (tableId: number) => {
    if (!window.confirm('Удалить этот стол?')) return;
    
    try {
      await apiClient.deleteTable(tableId);
      loadTables();
    } catch (error) {
      console.error('Error deleting table:', error);
      alert('Ошибка удаления стола');
    }
  };

  if (loading) {
    return <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>Загрузка...</div>;
  }

  const filteredTables = roomFilter 
    ? tables.filter(t => t.room_id === roomFilter)
    : tables;

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Управление столами</h1>
        <button onClick={() => setShowForm(!showForm)} style={buttonStyle}>
          {showForm ? 'Отмена' : '+ Создать стол'}
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
          <h3 style={{ color: '#66FCF1', marginTop: 0 }}>Создать стол</h3>
          <select
            value={formData.room_id}
            onChange={(e) => setFormData({ ...formData, room_id: parseInt(e.target.value) })}
            style={inputStyle}
          >
            <option value={0}>Выберите комнату</option>
            {rooms.map(room => (
              <option key={room.id} value={room.id}>
                {room.type} - {room.room_link.substring(0, 50)}...
              </option>
            ))}
          </select>
          <select
            value={formData.limit_type}
            onChange={(e) => setFormData({ ...formData, limit_type: e.target.value })}
            style={inputStyle}
          >
            <option value="NL10">NL10</option>
            <option value="NL25">NL25</option>
            <option value="NL50">NL50</option>
            <option value="NL100">NL100</option>
            <option value="NL200">NL200</option>
          </select>
          <input
            type="number"
            placeholder="Максимум игроков"
            value={formData.max_players}
            onChange={(e) => setFormData({ ...formData, max_players: parseInt(e.target.value) })}
            style={inputStyle}
            min="2"
            max="10"
          />
          <button onClick={handleCreate} style={buttonStyle} disabled={!formData.room_id}>
            Создать
          </button>
        </div>
      )}

      <div style={listStyle}>
        {filteredTables.map((table) => {
          const room = rooms.find(r => r.id === table.room_id);
          return (
            <div key={table.id} style={cardStyle}>
              <div style={cardHeaderStyle}>
                <div>
                  <span style={{ color: '#66FCF1', fontWeight: 'bold', fontSize: '18px' }}>
                    {table.limit_type}
                  </span>
                  <div style={{ color: '#C5C6C7', fontSize: '12px', marginTop: '4px' }}>
                    Room: {room?.type || `ID ${table.room_id}`}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(table.id)}
                  style={{...buttonStyle, background: '#ff4444', fontSize: '12px', padding: '6px 12px'}}
                >
                  Удалить
                </button>
              </div>
              <div style={{ color: '#C5C6C7', fontSize: '14px', marginTop: '10px' }}>
                <div>Макс. игроков: {table.max_players}</div>
                {table.meta && (
                  <div style={{ fontSize: '12px', marginTop: '8px', opacity: 0.7 }}>
                    {JSON.stringify(table.meta)}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {filteredTables.length === 0 && (
          <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>
            Нет столов {roomFilter ? 'в выбранной комнате' : ''}
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
  alignItems: 'flex-start',
  marginBottom: '10px'
};

export default AdminTablesPage;
