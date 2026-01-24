/**
 * Admin страница для управления комнатами
 */

import React, { useState, useEffect } from 'react';
import api from '../services/axiosConfig';
import { addResponsiveStyles } from '../utils/responsiveStyles';

// Initialize responsive styles
if (typeof document !== 'undefined') {
  addResponsiveStyles();
}

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
      const response = await api.get('/api/v1/admin/rooms');
      const data = response.data;
      setRooms(data || []);
    } catch (error: any) {
      console.error('Error loading rooms:', error);
      setRooms([]);
      alert('Ошибка загрузки комнат');
    } finally {
      setLoading(false);
    }
  };

  const handleOnboard = async () => {
    try {
      await api.post('/api/v1/admin/rooms', {
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
    <div style={containerStyle} className="admin-page-container">
      <div style={headerStyle} className="admin-page-header">
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Управление комнатами</h1>
        <button onClick={() => setShowForm(!showForm)} style={buttonStyle} className="admin-button">
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
            className="admin-input"
          />
          <select
            value={formData.type}
            onChange={(e) => setFormData({ ...formData, type: e.target.value })}
            style={inputStyle}
            className="admin-input"
          >
            <option value="pokerstars">PokerStars</option>
            <option value="ggpoker">GGPoker</option>
            <option value="acr">ACR</option>
            <option value="other">Другое</option>
          </select>
          <button onClick={handleOnboard} style={buttonStyle} className="admin-button">
            Добавить
          </button>
        </div>
      )}

      <div style={listStyle} className="admin-list-grid">
        {rooms.map((room) => (
          <div key={room.id} style={cardStyle} className="admin-card">
            <div style={cardHeaderStyle} className="admin-card-header admin-rooms-card-header">
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
  padding: '12px',
  maxWidth: '1200px',
  margin: '0 auto',
  width: '100%'
};

// Add responsive padding
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .admin-page-container {
        padding: 16px !important;
      }
    }
    @media (min-width: 768px) {
      .admin-page-container {
        padding: 20px !important;
      }
    }
  `;
  document.head.appendChild(style);
}

const headerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: '12px',
  marginBottom: '24px'
};

// Add responsive styles
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .admin-page-header {
        flex-direction: row !important;
        align-items: center !important;
        margin-bottom: 28px !important;
      }
    }
    @media (min-width: 768px) {
      .admin-page-header {
        margin-bottom: 30px !important;
      }
    }
  `;
  document.head.appendChild(style);
}

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

// Add responsive grid
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .admin-list-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 18px !important;
      }
    }
    @media (min-width: 1024px) {
      .admin-list-grid {
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)) !important;
        gap: 20px !important;
      }
    }
  `;
  document.head.appendChild(style);
}

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
