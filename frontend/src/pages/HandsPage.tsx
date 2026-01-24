/**
 * Hands Page - просмотр истории раздач
 */

import React, { useEffect, useState } from 'react';
import axios from '../services/axiosConfig';
import { addResponsiveStyles } from '../utils/responsiveStyles';

// Initialize responsive styles
if (typeof document !== 'undefined') {
  addResponsiveStyles();
}

interface Hand {
  id: number;
  hand_id: string;
  table_id: string;
  limit_type: string;
  hero_cards: string;
  board_cards: string;
  pot_size: number;
  result: number;
  created_at: string;
}

const HandsPage: React.FC = () => {
  const [hands, setHands] = useState<Hand[]>([]);
  const [loading, setLoading] = useState(true);
  const [limitFilter, setLimitFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  useEffect(() => {
    fetchHands();
  }, [limitFilter, page]);

  const fetchHands = async () => {
    try {
      setLoading(true);
      const params: any = {
        limit: pageSize,
        offset: (page - 1) * pageSize
      };
      if (limitFilter !== 'all') {
        params.limit_type = limitFilter;
      }
      const response = await axios.get('/api/v1/hands/recent', { params });
      setHands(response.data || []);
    } catch (error: any) {
      console.error('Error fetching hands:', error);
      setHands([]);
    } finally {
      setLoading(false);
    }
  };

  const formatCards = (cards: string) => {
    if (!cards) return '-';
    const formatted = cards.match(/.{2}/g) || [];
    return formatted.map((card, i) => {
      const suit = card[1];
      const suitSymbol = { h: '♥', d: '♦', c: '♣', s: '♠' }[suit.toLowerCase()] || suit;
      const color = ['h', 'd'].includes(suit.toLowerCase()) ? '#FF6B6B' : '#FFFFFF';
      return (
        <span key={i} style={{ color, marginRight: '4px' }}>
          {card[0]}{suitSymbol}
        </span>
      );
    });
  };

  const getResultColor = (result: number) => {
    if (result > 0) return '#4CAF50';
    if (result < 0) return '#F44336';
    return '#C5C6C7';
  };

  const totalProfit = hands.reduce((sum, h) => sum + (h.result || 0), 0);

  if (loading && hands.length === 0) {
    return <div style={loadingStyle}>Загрузка раздач...</div>;
  }

  return (
    <div style={pageStyle} className="user-page-container">
      <div style={headerStyle} className="user-page-header">
        <h1 style={{ margin: 0 }}>История раздач</h1>
        <div style={filterGroupStyle}>
          {['all', 'NL2', 'NL5', 'NL10', 'NL25', 'NL50'].map(f => (
            <button
              key={f}
              onClick={() => { setLimitFilter(f); setPage(1); }}
              style={{
                ...filterButtonStyle,
                ...(limitFilter === f ? activeFilterStyle : {})
              }}
            >
              {f === 'all' ? 'ВСЕ' : f}
            </button>
          ))}
        </div>
      </div>

      <div style={summaryStyle} className="hands-summary">
        <div style={summaryItemStyle}>
          <span style={summaryLabelStyle}>Показано раздач</span>
          <span style={summaryValueStyle}>{hands.length}</span>
        </div>
        <div style={summaryItemStyle}>
          <span style={summaryLabelStyle}>Общая прибыль</span>
          <span style={{...summaryValueStyle, color: getResultColor(totalProfit)}}>
            ${totalProfit.toFixed(2)}
          </span>
        </div>
      </div>

      <div style={tableContainerStyle} className="user-table-wrapper hands-table-wrapper">
        <table style={tableStyle}>
          <thead>
            <tr style={tableHeaderStyle}>
              <th style={thStyle}>Время</th>
              <th style={thStyle}>Лимит</th>
              <th style={thStyle}>Карты</th>
              <th style={thStyle}>Борд</th>
              <th style={thStyle}>Банк</th>
              <th style={thStyle}>Результат</th>
            </tr>
          </thead>
          <tbody>
            {hands.map((hand) => (
              <tr key={hand.hand_id} style={tableRowStyle}>
                <td style={tdStyle}>
                  {new Date(hand.created_at).toLocaleString('ru-RU', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </td>
                <td style={tdStyle}>
                  <span style={limitBadgeStyle}>{hand.limit_type}</span>
                </td>
                <td style={{...tdStyle, fontFamily: 'monospace', fontSize: '16px'}}>
                  {formatCards(hand.hero_cards)}
                </td>
                <td style={{...tdStyle, fontFamily: 'monospace', fontSize: '14px'}}>
                  {formatCards(hand.board_cards)}
                </td>
                <td style={tdStyle}>${(hand.pot_size || 0).toFixed(2)}</td>
                <td style={{...tdStyle, color: getResultColor(hand.result || 0), fontWeight: 'bold'}}>
                  {(hand.result || 0) >= 0 ? '+' : ''}${(hand.result || 0).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {hands.length === 0 && (
          <div style={emptyStateStyle}>Раздачи не найдены</div>
        )}
      </div>

      <div style={paginationStyle} className="hands-pagination">
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
          style={{...pageButtonStyle, opacity: page === 1 ? 0.5 : 1}}
        >
          Назад
        </button>
        <span style={{ color: '#C5C6C7' }}>Страница {page}</span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={hands.length < pageSize}
          style={{...pageButtonStyle, opacity: hands.length < pageSize ? 0.5 : 1}}
        >
          Вперед
        </button>
      </div>
    </div>
  );
};

const pageStyle: React.CSSProperties = { padding: '12px' };
const loadingStyle: React.CSSProperties = { textAlign: 'center', padding: '50px', color: '#C5C6C7' };
const headerStyle: React.CSSProperties = { 
  display: 'flex', 
  flexDirection: 'column',
  justifyContent: 'space-between', 
  alignItems: 'flex-start', 
  gap: '12px',
  marginBottom: '24px', 
  padding: '16px', 
  background: '#1F2833', 
  borderRadius: '8px' 
};
const filterGroupStyle: React.CSSProperties = { 
  display: 'flex', 
  flexWrap: 'wrap',
  gap: '8px',
  width: '100%'
};
const filterButtonStyle: React.CSSProperties = { padding: '8px 16px', border: '1px solid #C5C6C7', background: 'transparent', color: '#C5C6C7', borderRadius: '4px', cursor: 'pointer' };
const activeFilterStyle: React.CSSProperties = { background: '#66FCF1', color: '#0B0C10', border: '1px solid #66FCF1' };
const summaryStyle: React.CSSProperties = { 
  display: 'flex', 
  flexDirection: 'column',
  gap: '16px', 
  marginBottom: '20px' 
};

// Add responsive styles
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .hands-summary {
        flex-direction: row !important;
        gap: 20px !important;
      }
    }
  `;
  document.head.appendChild(style);
}
const summaryItemStyle: React.CSSProperties = { flex: 1, padding: '20px', background: '#1F2833', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '10px' };
const summaryLabelStyle: React.CSSProperties = { color: '#C5C6C7', fontSize: '14px' };
const summaryValueStyle: React.CSSProperties = { color: '#66FCF1', fontSize: '24px', fontWeight: 'bold' };
const tableContainerStyle: React.CSSProperties = { 
  background: '#1F2833', 
  borderRadius: '8px', 
  overflow: 'hidden',
  overflowX: 'auto'
};
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse' };
const tableHeaderStyle: React.CSSProperties = { background: '#0B0C10' };
const thStyle: React.CSSProperties = { padding: '15px', textAlign: 'left', color: '#66FCF1', fontWeight: 'bold' };
const tableRowStyle: React.CSSProperties = { borderBottom: '1px solid #45A29E' };
const tdStyle: React.CSSProperties = { padding: '12px 15px', color: '#C5C6C7' };
const limitBadgeStyle: React.CSSProperties = { background: '#45A29E', padding: '4px 10px', borderRadius: '4px', fontSize: '12px' };
const emptyStateStyle: React.CSSProperties = { textAlign: 'center', padding: '50px', color: '#C5C6C7' };
const paginationStyle: React.CSSProperties = { display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '20px', marginTop: '20px' };
const pageButtonStyle: React.CSSProperties = { 
  padding: '10px 20px', 
  background: '#45A29E', 
  border: 'none', 
  borderRadius: '4px', 
  color: '#FFFFFF', 
  cursor: 'pointer',
  minWidth: '100px'
};

export default HandsPage;
