/**
 * Admin страница для просмотра Audit Log
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/api';

interface AuditEntry {
  id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  admin_key: string;
  old_values: any;
  new_values: any;
  created_at: string;
  ip_address?: string;
}

interface AuditSummary {
  total_entries: number;
  actions: Record<string, number>;
  entity_types: Record<string, number>;
  recent_activity: {
    last_24h: number;
    last_7d: number;
    last_30d: number;
  };
}

const AdminAuditPage: React.FC = () => {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    action: '',
    entity_type: '',
    limit: 100
  });
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [entriesData, summaryData] = await Promise.all([
        apiClient.getAuditLog(filters.limit, filters.action || undefined, filters.entity_type || undefined),
        apiClient.getAuditSummary()
      ]);
      setEntries(entriesData);
      setSummary(summaryData);
    } catch (error) {
      console.error('Error loading audit data:', error);
      alert('Ошибка загрузки данных аудита');
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = () => {
    loadData();
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'create': return '#45A29E';
      case 'update': return '#66FCF1';
      case 'delete': return '#ff4444';
      case 'start_session': return '#45A29E';
      case 'stop_session': return '#C5C6C7';
      case 'pause_session': return '#FFD700';
      default: return '#C5C6C7';
    }
  };

  const getEntityIcon = (entityType: string) => {
    switch (entityType) {
      case 'bot': return 'B';
      case 'room': return 'R';
      case 'table': return 'T';
      case 'bot_session': return 'S';
      case 'bot_config': return 'C';
      case 'rake_model': return '$';
      case 'api_key': return 'K';
      default: return '?';
    }
  };

  if (loading) {
    return <div style={{ color: '#C5C6C7', textAlign: 'center', padding: '40px' }}>Загрузка...</div>;
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={{ color: '#66FCF1', margin: 0 }}>Журнал аудита</h1>
        <button onClick={loadData} style={buttonStyle}>
          Обновить
        </button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div style={summaryGridStyle}>
          <div style={summaryCardStyle}>
            <div style={{ fontSize: '32px', color: '#66FCF1', fontWeight: 'bold' }}>
              {summary.total_entries}
            </div>
            <div style={{ color: '#C5C6C7', fontSize: '14px' }}>Всего записей</div>
          </div>
          <div style={summaryCardStyle}>
            <div style={{ fontSize: '32px', color: '#45A29E', fontWeight: 'bold' }}>
              {summary.recent_activity.last_24h}
            </div>
            <div style={{ color: '#C5C6C7', fontSize: '14px' }}>За 24 часа</div>
          </div>
          <div style={summaryCardStyle}>
            <div style={{ fontSize: '32px', color: '#45A29E', fontWeight: 'bold' }}>
              {summary.recent_activity.last_7d}
            </div>
            <div style={{ color: '#C5C6C7', fontSize: '14px' }}>За 7 дней</div>
          </div>
          <div style={summaryCardStyle}>
            <div style={{ fontSize: '32px', color: '#45A29E', fontWeight: 'bold' }}>
              {summary.recent_activity.last_30d}
            </div>
            <div style={{ color: '#C5C6C7', fontSize: '14px' }}>За 30 дней</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div style={filterStyle}>
        <select
          value={filters.action}
          onChange={(e) => setFilters({ ...filters, action: e.target.value })}
          style={inputStyle}
        >
          <option value="">Все действия</option>
          <option value="create">Создать</option>
          <option value="update">Обновить</option>
          <option value="delete">Удалить</option>
          <option value="start_session">Запустить сессию</option>
          <option value="stop_session">Остановить сессию</option>
          <option value="pause_session">Приостановить сессию</option>
        </select>
        <select
          value={filters.entity_type}
          onChange={(e) => setFilters({ ...filters, entity_type: e.target.value })}
          style={inputStyle}
        >
          <option value="">Все сущности</option>
          <option value="bot">Бот</option>
          <option value="room">Комната</option>
          <option value="table">Стол</option>
          <option value="bot_session">Сессия бота</option>
          <option value="bot_config">Конфиг бота</option>
          <option value="rake_model">Модель рейка</option>
          <option value="api_key">API Ключ</option>
        </select>
        <select
          value={filters.limit}
          onChange={(e) => setFilters({ ...filters, limit: parseInt(e.target.value) })}
          style={inputStyle}
        >
          <option value={50}>50 записей</option>
          <option value={100}>100 записей</option>
          <option value={200}>200 записей</option>
          <option value={500}>500 записей</option>
        </select>
        <button onClick={handleFilter} style={buttonStyle}>
          Применить
        </button>
      </div>

      {/* Entries List */}
      <div style={tableContainerStyle}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Время</th>
              <th style={thStyle}>Действие</th>
              <th style={thStyle}>Сущность</th>
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Admin</th>
              <th style={thStyle}>Детали</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id} style={trStyle}>
                <td style={tdStyle}>{formatDate(entry.created_at)}</td>
                <td style={tdStyle}>
                  <span style={{
                    background: getActionColor(entry.action),
                    color: '#0B0C10',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 'bold'
                  }}>
                    {entry.action}
                  </span>
                </td>
                <td style={tdStyle}>
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <span style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: '#1F2833',
                      border: '1px solid #66FCF1',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '12px',
                      fontWeight: 'bold',
                      color: '#66FCF1'
                    }}>
                      {getEntityIcon(entry.entity_type)}
                    </span>
                    {entry.entity_type}
                  </span>
                </td>
                <td style={tdStyle}>{entry.entity_id}</td>
                <td style={tdStyle}>
                  <span style={{ color: '#C5C6C7', fontSize: '12px' }}>
                    {entry.admin_key ? `...${entry.admin_key.slice(-8)}` : '-'}
                  </span>
                </td>
                <td style={tdStyle}>
                  <button
                    onClick={() => setSelectedEntry(entry)}
                    style={{
                      ...buttonStyle,
                      padding: '4px 12px',
                      fontSize: '12px'
                    }}
                  >
                    Подробнее
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detail Modal */}
      {selectedEntry && (
        <div style={modalOverlayStyle} onClick={() => setSelectedEntry(null)}>
          <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ color: '#66FCF1', margin: 0 }}>Детали записи #{selectedEntry.id}</h2>
              <button
                onClick={() => setSelectedEntry(null)}
                style={{ ...buttonStyle, background: '#C5C6C7' }}
              >
                Закрыть
              </button>
            </div>

            <div style={detailGridStyle}>
              <div style={detailItemStyle}>
                <label style={detailLabelStyle}>Время:</label>
                <span>{formatDate(selectedEntry.created_at)}</span>
              </div>
              <div style={detailItemStyle}>
                <label style={detailLabelStyle}>Действие:</label>
                <span style={{
                  background: getActionColor(selectedEntry.action),
                  color: '#0B0C10',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 'bold'
                }}>
                  {selectedEntry.action}
                </span>
              </div>
              <div style={detailItemStyle}>
                <label style={detailLabelStyle}>Сущность:</label>
                <span>{selectedEntry.entity_type} #{selectedEntry.entity_id}</span>
              </div>
              <div style={detailItemStyle}>
                <label style={detailLabelStyle}>Админ ключ:</label>
                <span style={{ color: '#C5C6C7' }}>{selectedEntry.admin_key || '-'}</span>
              </div>
              {selectedEntry.ip_address && (
                <div style={detailItemStyle}>
                  <label style={detailLabelStyle}>IP:</label>
                  <span>{selectedEntry.ip_address}</span>
                </div>
              )}
            </div>

            {selectedEntry.old_values && (
              <div style={{ marginTop: '20px' }}>
                <h3 style={{ color: '#ff4444', fontSize: '14px', marginBottom: '10px' }}>Старые значения:</h3>
                <pre style={preStyle}>{JSON.stringify(selectedEntry.old_values, null, 2)}</pre>
              </div>
            )}

            {selectedEntry.new_values && (
              <div style={{ marginTop: '20px' }}>
                <h3 style={{ color: '#45A29E', fontSize: '14px', marginBottom: '10px' }}>Новые значения:</h3>
                <pre style={preStyle}>{JSON.stringify(selectedEntry.new_values, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>
      )}
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

const summaryGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(4, 1fr)',
  gap: '20px',
  marginBottom: '30px'
};

const summaryCardStyle: React.CSSProperties = {
  background: '#1F2833',
  padding: '20px',
  borderRadius: '8px',
  border: '1px solid #C5C6C7',
  textAlign: 'center'
};

const filterStyle: React.CSSProperties = {
  display: 'flex',
  gap: '15px',
  marginBottom: '20px',
  background: '#1F2833',
  padding: '20px',
  borderRadius: '8px',
  border: '1px solid #C5C6C7',
  alignItems: 'center'
};

const inputStyle: React.CSSProperties = {
  padding: '10px',
  background: '#0B0C10',
  border: '1px solid #C5C6C7',
  borderRadius: '4px',
  color: '#FFFFFF',
  fontSize: '14px',
  minWidth: '150px'
};

const tableContainerStyle: React.CSSProperties = {
  background: '#1F2833',
  borderRadius: '8px',
  border: '1px solid #C5C6C7',
  overflow: 'hidden'
};

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse'
};

const thStyle: React.CSSProperties = {
  background: '#0B0C10',
  color: '#66FCF1',
  padding: '15px',
  textAlign: 'left',
  borderBottom: '1px solid #C5C6C7',
  fontWeight: 'bold'
};

const trStyle: React.CSSProperties = {
  borderBottom: '1px solid #2a2f38'
};

const tdStyle: React.CSSProperties = {
  padding: '12px 15px',
  color: '#FFFFFF',
  verticalAlign: 'middle'
};

const modalOverlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: 'rgba(0, 0, 0, 0.8)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000
};

const modalStyle: React.CSSProperties = {
  background: '#1F2833',
  padding: '30px',
  borderRadius: '8px',
  border: '1px solid #66FCF1',
  maxWidth: '700px',
  width: '90%',
  maxHeight: '80vh',
  overflow: 'auto'
};

const detailGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, 1fr)',
  gap: '15px'
};

const detailItemStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '5px'
};

const detailLabelStyle: React.CSSProperties = {
  color: '#C5C6C7',
  fontSize: '12px',
  textTransform: 'uppercase'
};

const preStyle: React.CSSProperties = {
  background: '#0B0C10',
  padding: '15px',
  borderRadius: '4px',
  overflow: 'auto',
  fontSize: '12px',
  color: '#C5C6C7',
  maxHeight: '200px'
};

export default AdminAuditPage;
