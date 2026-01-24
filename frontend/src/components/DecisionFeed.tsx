/**
 * Компонент для отображения ленты решений
 */

import React from 'react';

interface DecisionMessage {
  type: string;
  timestamp: string;
  data?: any;
}

interface DecisionFeedProps {
  messages: DecisionMessage[];
}

const DecisionFeed: React.FC<DecisionFeedProps> = ({ messages }) => {
  const decisionMessages = messages.filter(m => m.type === 'decision').slice(-10).reverse();

  return (
    <div className="decision-feed" style={cardStyle}>
      <h2 style={titleStyle}>Последние решения</h2>
      
      <div style={feedStyle}>
        {decisionMessages.length === 0 ? (
          <div style={emptyStyle}>Решений пока нет</div>
        ) : (
          decisionMessages.map((msg, idx) => (
            <DecisionItem key={idx} message={msg} />
          ))
        )}
      </div>
    </div>
  );
};

interface DecisionItemProps {
  message: DecisionMessage;
}

const DecisionItem: React.FC<DecisionItemProps> = ({ message }) => {
  const { data } = message;
  const time = new Date(message.timestamp).toLocaleTimeString('ru-RU');

  return (
    <div style={itemStyle}>
      <div style={itemHeaderStyle}>
        <span style={timeStyle}>{time}</span>
        <span style={actionStyle}>{data?.action || 'неизвестно'}</span>
      </div>
      {data?.amount && (
        <div style={amountStyle}>Сумма: {data.amount}</div>
      )}
      <div style={metaStyle}>
        {data?.limit_type} • {data?.street === 'preflop' ? 'Префлоп' : data?.street === 'flop' ? 'Флоп' : data?.street === 'turn' ? 'Тёрн' : data?.street === 'river' ? 'Ривер' : data?.street} • {data?.latency_ms}мс
      </div>
    </div>
  );
};

const cardStyle: React.CSSProperties = {
  background: '#1F2833',
  padding: '16px',
  borderRadius: '8px',
  border: '1px solid #C5C6C7',
  maxHeight: '500px',
  overflowY: 'auto'
};

// Add responsive padding
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 768px) {
      .decision-feed {
        padding: 20px !important;
      }
    }
  `;
  document.head.appendChild(style);
}

const titleStyle: React.CSSProperties = {
  color: '#66FCF1',
  marginTop: 0,
  marginBottom: '20px'
};

const feedStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '10px'
};

const emptyStyle: React.CSSProperties = {
  color: '#888',
  textAlign: 'center',
  padding: '20px'
};

const itemStyle: React.CSSProperties = {
  background: '#0B0C10',
  padding: '15px',
  borderRadius: '4px',
  border: '1px solid #C5C6C7'
};

const itemHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  marginBottom: '8px'
};

const timeStyle: React.CSSProperties = {
  color: '#888',
  fontSize: '12px'
};

const actionStyle: React.CSSProperties = {
  color: '#66FCF1',
  fontWeight: 'bold',
  textTransform: 'uppercase'
};

const amountStyle: React.CSSProperties = {
  color: '#FFFFFF',
  fontSize: '14px',
  marginBottom: '4px'
};

const metaStyle: React.CSSProperties = {
  color: '#888',
  fontSize: '12px'
};

export default DecisionFeed;
