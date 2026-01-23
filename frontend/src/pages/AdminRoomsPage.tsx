/**
 * Admin страница для управления комнатами
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/api';

const AdminRoomsPage: React.FC = () => {
  const [rooms, setRooms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    room_link: '',
    type: 'pokerstars',
    status: 'pending',
    meta: null
  });

  useEffect(() => {
    loadRooms();
  }, []);

  const loadRooms = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getRooms();
      setRooms(data);
    } catch (error) {
      console.error('Error loading rooms:', error);
      alert('Ошибка загрузки комнат');
    } finally {
      setLoading(false);
    }
  };

  const handleOnboard = async () => {
    try {
      await apiClient.onboardRoom({
        room_link: formData.room_link,
        type: formData.type,
        meta: formData.meta
      });
      setShowForm(false);
      setFormData({ room_link: '', type: 'pokerstars', status: 'pending', meta: null });
      loadRooms();
    } catch (error) {
      console.error('Error onboarding room:', error);
      alert('Ошибка добавления комнаты');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return '#45A29E';
      case 'onboarded': return '#66FCF1';
      case 'pending': return '#C5C6C7';
      default: return '#C5C6C7';
    }
  };

  if (loading) {
    return <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>Загрузка...</div>;
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Управление комнатами</h1>
        <button onClick={() => setShowForm(!showForm)} style={buttonStyle}>
          {showForm ? 'Отмена' : '+ Добавить комнату'}
        </button>
      </div>

      {showForm && (
        <div style={formStyle}>
          <h3 style={{ color: '#66FCF1', marginTop: 0 }}>Добавить комнату</h3>
          <input
            type="text"
            placeholder="Ссылка на комнату"
            value={formData.room_link}
            onChange={(e) => setFormData({ ...formData, room_link: e.target.value })}
            style={inputStyle}
          />
          <select
            value={formData.type}
            onChange={(e) => setFormData({ ...formData, type: e.target.value })}
            style={inputStyle}
          >
            <option value="pokerstars">PokerStars</option>
            <option value="ggpoker">GGPoker</option>
            <option value="acr">ACR</option>
            <option value="other">Другое</option>
          </select>
          <button onClick={handleOnboard} style={buttonStyle}>
            Добавить
          </button>
        </div>
      )}

      <div style={listStyle}>
        {rooms.map((room) => (
          <div key={room.id} style={cardStyle}>
            <div style={cardHeaderStyle}>
              <span style={{ color: '#66FCF1', fontWeight: 'bold' }}>{room.type}</span>
              <span style={{ 
                background: getStatusColor(room.status),
                color: '#0B0C10',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 'bold'
              }}>
                {room.status === 'active' ? 'Активна' : room.status === 'onboarded' ? 'Добавлена' : room.status === 'pending' ? 'Ожидает' : room.status}
              </span>
            </div>
            <div style={{ color: '#C5C6C7', fontSize: '14px', marginTop: '8px', wordBreak: 'break-all' }}>
              {room.room_link}
            </div>
            {room.meta && (
              <div style={{ color: '#C5C6C7', fontSize: '12px', marginTop: '8px' }}>
                {JSON.stringify(room.meta)}
              </div>
            )}
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

export default AdminRoomsPage;
