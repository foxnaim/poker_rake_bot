/**
 * Opponents Page - управление профилями оппонентов
 */

import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface OpponentProfile {
  opponent_id: string;
  vpip: number;
  pfr: number;
  three_bet_pct: number;
  aggression_factor: number;
  hands_played: number;
  classification: string;
}

const OpponentsPage: React.FC = () => {
  const [opponents, setOpponents] = useState<OpponentProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    fetchOpponents();
  }, [filter]);

  const fetchOpponents = async () => {
    try {
      setLoading(true);
      const params: any = { limit: 100, min_hands: 10 };
      if (filter !== 'all') {
        params.classification = filter;
      }
      
      const response = await axios.get('/api/v1/opponents', { params });
      setOpponents(response.data);
    } catch (error) {
      console.error('Error fetching opponents:', error);
    } finally {
      setLoading(false);
    }
  };

  const getClassificationColor = (classification: string) => {
    const colors: {[key: string]: string} = {
      fish: '#FF6B6B',
      nit: '#4ECDC4',
      tag: '#45B7D1',
      lag: '#FFA07A',
      calling_station: '#DDA15E',
      unknown: '#8E8E8E'
    };
    return colors[classification] || colors.unknown;
  };

  const getClassificationLabel = (classification: string) => {
    const labels: {[key: string]: string} = {
      fish: '🐟 Рыба',
      nit: '🛡️ Нитовый',
      tag: '💪 TAG',
      lag: '🔥 LAG',
      calling_station: '📞 Коллинг-станция',
      unknown: '❓ Неизвестно'
    };
    return labels[classification] || labels.unknown;
  };

  if (loading) {
    return <div style={loadingStyle}>Загрузка профилей...</div>;
  }

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <h1 style={{ margin: 0 }}>👥 Профили оппонентов</h1>
        <div style={filterGroupStyle}>
          {['all', 'fish', 'nit', 'tag', 'lag', 'calling_station'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                ...filterButtonStyle,
                ...(filter === f ? activeFilterStyle : {})
              }}
            >
              {f === 'all' ? 'ВСЕ' : f === 'fish' ? 'РЫБА' : f === 'nit' ? 'НИТ' : f === 'tag' ? 'TAG' : f === 'lag' ? 'LAG' : f === 'calling_station' ? 'КОЛЛИНГ-СТАНЦИЯ' : f.toUpperCase().replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <div style={statsCardStyle}>
        <div style={statItemStyle}>
          <span style={statLabelStyle}>Всего профилей</span>
          <span style={statValueStyle}>{opponents.length}</span>
        </div>
        <div style={statItemStyle}>
          <span style={statLabelStyle}>Среднее раздач</span>
          <span style={statValueStyle}>
            {opponents.length > 0 ? Math.round(opponents.reduce((acc, o) => acc + (o.hands_played || 0), 0) / opponents.length) : 0}
          </span>
        </div>
      </div>

      <div style={tableContainerStyle}>
        <table style={tableStyle}>
          <thead>
            <tr style={tableHeaderStyle}>
              <th style={thStyle}>Игрок</th>
              <th style={thStyle}>Тип</th>
              <th style={thStyle}>VPIP</th>
              <th style={thStyle}>PFR</th>
              <th style={thStyle}>3-Бет%</th>
              <th style={thStyle}>AF</th>
              <th style={thStyle}>Раздачи</th>
            </tr>
          </thead>
          <tbody>
            {opponents.map((opponent) => (
              <tr key={opponent.opponent_id} style={tableRowStyle}>
                <td style={tdStyle}>{opponent.opponent_id}</td>
                <td style={tdStyle}>
                  <span style={{
                    ...badgeStyle,
                    background: getClassificationColor(opponent.classification)
                  }}>
                    {getClassificationLabel(opponent.classification)}
                  </span>
                </td>
                <td style={tdStyle}>{opponent.vpip.toFixed(1)}%</td>
                <td style={tdStyle}>{opponent.pfr.toFixed(1)}%</td>
                <td style={tdStyle}>{opponent.three_bet_pct.toFixed(1)}%</td>
                <td style={tdStyle}>{opponent.aggression_factor.toFixed(2)}</td>
                <td style={tdStyle}>{opponent.hands_played}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {opponents.length === 0 && (
          <div style={emptyStateStyle}>
            Оппоненты не найдены для этого фильтра
          </div>
        )}
      </div>
    </div>
  );
};

// Styles
const pageStyle: React.CSSProperties = {
  padding: '20px'
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '30px',
  padding: '20px',
  background: '#1F2833',
  borderRadius: '8px'
};

const filterGroupStyle: React.CSSProperties = {
  display: 'flex',
  gap: '10px'
};

const filterButtonStyle: React.CSSProperties = {
  padding: '8px 16px',
  border: '1px solid #C5C6C7',
  background: 'transparent',
  color: '#C5C6C7',
  borderRadius: '4px',
  cursor: 'pointer',
  transition: 'all 0.3s'
};

const activeFilterStyle: React.CSSProperties = {
  background: '#66FCF1',
  color: '#0B0C10',
  border: '1px solid #66FCF1'
};

const statsCardStyle: React.CSSProperties = {
  display: 'flex',
  gap: '20px',
  marginBottom: '20px'
};

const statItemStyle: React.CSSProperties = {
  flex: 1,
  padding: '20px',
  background: '#1F2833',
  borderRadius: '8px',
  display: 'flex',
  flexDirection: 'column',
  gap: '10px'
};

const statLabelStyle: React.CSSProperties = {
  color: '#C5C6C7',
  fontSize: '14px'
};

const statValueStyle: React.CSSProperties = {
  color: '#66FCF1',
  fontSize: '28px',
  fontWeight: 'bold'
};

const tableContainerStyle: React.CSSProperties = {
  background: '#1F2833',
  borderRadius: '8px',
  overflow: 'hidden'
};

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse'
};

const tableHeaderStyle: React.CSSProperties = {
  background: '#0B0C10'
};

const thStyle: React.CSSProperties = {
  padding: '15px',
  textAlign: 'left',
  color: '#66FCF1',
  fontWeight: 'bold',
  borderBottom: '2px solid #C5C6C7'
};

const tableRowStyle: React.CSSProperties = {
  borderBottom: '1px solid #45A29E'
};

const tdStyle: React.CSSProperties = {
  padding: '12px 15px',
  color: '#C5C6C7'
};

const badgeStyle: React.CSSProperties = {
  padding: '4px 12px',
  borderRadius: '12px',
  fontSize: '12px',
  fontWeight: 'bold',
  color: '#FFFFFF',
  display: 'inline-block'
};

const loadingStyle: React.CSSProperties = {
  textAlign: 'center',
  padding: '50px',
  color: '#C5C6C7',
  fontSize: '18px'
};

const emptyStateStyle: React.CSSProperties = {
  textAlign: 'center',
  padding: '50px',
  color: '#C5C6C7'
};

export default OpponentsPage;
