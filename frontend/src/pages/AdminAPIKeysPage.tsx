/**
 * Admin страница для управления API ключами
 */

import React, { useState, useEffect } from 'react';
import api from '../services/axiosConfig';
import { addResponsiveStyles } from '../utils/responsiveStyles';

// Initialize responsive styles
if (typeof document !== 'undefined') {
  addResponsiveStyles();
}

const AdminAPIKeysPage: React.FC = () => {
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    client_name: '',
    permissions: ['decide_only', 'log_only'] as string[],
    rate_limit_per_minute: 120,
    is_admin: false
  });

  useEffect(() => {
    loadKeys();
  }, []);

  const loadKeys = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/admin/api-keys');
      setKeys(response.data || []);
    } catch (error: any) {
      console.error('Error loading keys:', error);
      setKeys([]);
      alert('Ошибка загрузки API ключей');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const permissions = formData.is_admin
        ? ['admin', ...formData.permissions]
        : formData.permissions;

      const response = await api.post('/api/v1/admin/api-keys', {
        client_name: formData.client_name,
        permissions: permissions,
        rate_limit_per_minute: formData.rate_limit_per_minute
      });

      alert(`API ключ создан!\n\nAPI ключ: ${response.data.api_key}\nAPI секрет: ${response.data.api_secret}\n\nСохраните эти данные!`);
      setShowForm(false);
      setFormData({
        client_name: '',
        permissions: ['decide_only', 'log_only'],
        rate_limit_per_minute: 120,
        is_admin: false
      });
      loadKeys();
    } catch (error: any) {
      console.error('Error creating key:', error);
      alert(error.message || 'Ошибка создания API ключа');
    }
  };

  const handleToggle = async (keyId: number, currentActive: boolean) => {
    try {
      await api.patch(`/api/v1/admin/api-keys/${keyId}/toggle`);
      loadKeys();
    } catch (error) {
      console.error('Error toggling key:', error);
      alert('Ошибка изменения статуса ключа');
    }
  };

  const handleDelete = async (keyId: number) => {
    if (!window.confirm('Удалить этот API ключ?')) return;

    try {
      await api.delete(`/api/v1/admin/api-keys/${keyId}`);
      loadKeys();
    } catch (error) {
      console.error('Error deleting key:', error);
      alert('Ошибка удаления ключа');
    }
  };

  const hasPermission = (permissions: string[], perm: string) => {
    return permissions.includes(perm) || permissions.includes('admin');
  };

  if (loading) {
    return <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>Загрузка...</div>;
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle} className="admin-page-header admin-api-keys-header">
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Управление API ключами</h1>
        <button onClick={() => setShowForm(!showForm)} style={buttonStyle} className="admin-button">
          {showForm ? 'Отмена' : '+ Создать API ключ'}
        </button>
      </div>

      {showForm && (
        <div style={formStyle}>
          <h3 style={{ color: '#66FCF1', marginTop: 0 }}>Создать API ключ</h3>
          <input
            type="text"
            placeholder="Название клиента"
            value={formData.client_name}
            onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
            style={inputStyle}
            className="admin-input"
          />
          <div style={rowStyle} className="admin-form-row">
            <label style={{ color: '#C5C6C7', display: 'flex', alignItems: 'center', marginRight: '20px' }}>
              <input
                type="checkbox"
                checked={formData.permissions.includes('decide_only')}
                onChange={(e) => {
                  const perms = e.target.checked
                    ? [...formData.permissions, 'decide_only']
                    : formData.permissions.filter(p => p !== 'decide_only');
                  setFormData({ ...formData, permissions: perms });
                }}
                style={{ marginRight: '8px' }}
              />
              Только решения
            </label>
            <label style={{ color: '#C5C6C7', display: 'flex', alignItems: 'center', marginRight: '20px' }}>
              <input
                type="checkbox"
                checked={formData.permissions.includes('log_only')}
                onChange={(e) => {
                  const perms = e.target.checked
                    ? [...formData.permissions, 'log_only']
                    : formData.permissions.filter(p => p !== 'log_only');
                  setFormData({ ...formData, permissions: perms });
                }}
                style={{ marginRight: '8px' }}
              />
              Только логирование
            </label>
            <label style={{ color: '#C5C6C7', display: 'flex', alignItems: 'center' }}>
              <input
                type="checkbox"
                checked={formData.is_admin}
                onChange={(e) => setFormData({ ...formData, is_admin: e.target.checked })}
                style={{ marginRight: '8px' }}
              />
              Администратор
            </label>
          </div>
          <input
            type="number"
            placeholder="Лимит запросов (в минуту)"
            value={formData.rate_limit_per_minute}
            onChange={(e) => setFormData({ ...formData, rate_limit_per_minute: parseInt(e.target.value) })}
            style={inputStyle}
            className="admin-input"
            min="1"
          />
          <button onClick={handleCreate} style={buttonStyle} className="admin-button" disabled={!formData.client_name}>
            Создать
          </button>
        </div>
      )}

      <div style={listStyle} className="admin-list-grid">
        {keys.map((key) => (
          <div key={key.key_id} style={cardStyle} className="admin-card">
            <div style={cardHeaderStyle} className="admin-card-header admin-api-keys-card-header">
              <div>
                <span style={{ color: '#66FCF1', fontWeight: 'bold', fontSize: '18px' }}>
                  {key.client_name}
                </span>
                <div style={{ color: '#C5C6C7', fontSize: '12px', marginTop: '4px' }}>
                  {key.api_key.substring(0, 30)}...
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }} className="admin-button-group">
                <button
                  onClick={() => handleToggle(key.key_id, key.is_active)}
                  style={{
                    ...buttonStyle,
                    background: key.is_active ? '#45A29E' : '#C5C6C7',
                    fontSize: '12px',
                    padding: '6px 12px',
                    width: '100%'
                  }}
                  className="admin-button"
                >
                  {key.is_active ? 'Активен' : 'Неактивен'}
                </button>
                <button
                  onClick={() => handleDelete(key.key_id)}
                  style={{...buttonStyle, background: '#ff4444', fontSize: '12px', padding: '6px 12px', width: '100%'}}
                  className="admin-button"
                >
                  Удалить
                </button>
              </div>
            </div>
            <div style={{ color: '#C5C6C7', fontSize: '14px', marginTop: '10px' }}>
              <div>Права: {key.permissions.join(', ')}</div>
              <div>Лимит запросов: {key.rate_limit_per_minute} запросов/мин</div>
              <div style={{ fontSize: '12px', marginTop: '4px', opacity: 0.7 }}>
                Создан: {new Date(key.created_at).toLocaleString('ru-RU')}
              </div>
            </div>
          </div>
        ))}
        {keys.length === 0 && (
          <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>
            Нет API ключей
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

// Add responsive card header
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .admin-api-keys-card-header {
        flex-direction: row !important;
        align-items: flex-start !important;
      }
    }
  `;
  document.head.appendChild(style);
}

export default AdminAPIKeysPage;
