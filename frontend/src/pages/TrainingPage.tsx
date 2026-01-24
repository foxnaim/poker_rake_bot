/**
 * Training Page - управление обучением MCCFR
 */

import React, { useEffect, useState } from 'react';
import axios from '../services/axiosConfig';
import { addResponsiveStyles } from '../utils/responsiveStyles';

// Initialize responsive styles
if (typeof document !== 'undefined') {
  addResponsiveStyles();
}

interface TrainingStatus {
  is_running: boolean;
  format: string | null;
  current_iteration: number | null;
  total_iterations: number | null;
  start_time: string | null;
  estimated_completion: string | null;
}

interface Checkpoint {
  checkpoint_id: string;
  format: string;
  training_iterations: number;
  created_at: string;
  is_active: boolean;
}

const TrainingPage: React.FC = () => {
  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFormat, setSelectedFormat] = useState('NL10');
  const [iterations, setIterations] = useState(100000);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    await Promise.all([fetchStatus(), fetchCheckpoints()]);
    setLoading(false);
  };

  const fetchStatus = async () => {
    try {
      const response = await axios.get('/api/v1/training/status');
      setStatus(response.data || null);
    } catch (error: any) {
      console.error('Error fetching training status:', error);
      setStatus(null);
    }
  };

  const fetchCheckpoints = async () => {
    try {
      const response = await axios.get('/api/v1/checkpoints');
      setCheckpoints(response.data || []);
    } catch (error: any) {
      console.error('Error fetching checkpoints:', error);
      setCheckpoints([]);
    }
  };

  const startTraining = async () => {
    try {
      await axios.post('/api/v1/training/start', {
        format: selectedFormat,
        iterations: iterations
      });
      fetchStatus();
    } catch (error) {
      console.error('Error starting training:', error);
    }
  };

  const stopTraining = async () => {
    try {
      await axios.post('/api/v1/training/stop');
      fetchStatus();
    } catch (error) {
      console.error('Error stopping training:', error);
    }
  };

  const activateCheckpoint = async (checkpointId: string) => {
    try {
      await axios.post(`/api/v1/checkpoint/${checkpointId}/activate`);
      fetchCheckpoints();
    } catch (error) {
      console.error('Error activating checkpoint:', error);
    }
  };

  const formatTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  const formatNumber = (num: number) => {
    return num.toLocaleString('ru-RU');
  };

  if (loading) {
    return <div style={loadingStyle}>Загрузка данных обучения...</div>;
  }

  return (
    <div style={pageStyle} className="user-page-container">
      <div style={headerStyle}>
        <h1 style={{ margin: 0 }}>Обучение MCCFR</h1>
      </div>

      {/* Training Controls */}
      <div style={controlsCardStyle}>
        <h3 style={{ margin: '0 0 20px 0', color: '#66FCF1' }}>Управление обучением</h3>

        {status?.is_running ? (
          <div>
            <div style={progressContainerStyle}>
              <div style={progressHeaderStyle}>
                <span>Обучение {status.format}</span>
                <span>{status.total_iterations ? ((status.current_iteration || 0) / status.total_iterations * 100).toFixed(1) : 0}%</span>
              </div>
              <div style={progressBarBgStyle}>
                <div style={{...progressBarStyle, width: `${status.total_iterations ? ((status.current_iteration || 0) / status.total_iterations * 100) : 0}%`}}></div>
              </div>
              <div style={progressStatsStyle} className="training-progress-stats">
                <span>Итерация: {formatNumber(status.current_iteration || 0)} / {formatNumber(status.total_iterations || 0)}</span>
                <span>Начато: {status.start_time ? new Date(status.start_time).toLocaleTimeString('ru-RU') : '-'}</span>
                <span>Осталось: {status.estimated_completion ? new Date(status.estimated_completion).toLocaleTimeString('ru-RU') : '-'}</span>
              </div>
            </div>
            <button onClick={stopTraining} style={stopButtonStyle}>
              Остановить обучение
            </button>
          </div>
        ) : (
          <div style={startFormStyle} className="training-start-form">
            <div style={formGroupStyle}>
              <label style={labelStyle}>Формат:</label>
              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
                style={selectStyle}
                className="admin-input"
              >
                {['NL2', 'NL5', 'NL10', 'NL25', 'NL50', 'NL100'].map(f => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
            <div style={formGroupStyle}>
              <label style={labelStyle}>Итерации:</label>
              <input
                type="number"
                value={iterations}
                onChange={(e) => setIterations(Number(e.target.value))}
                style={inputStyle}
                className="admin-input"
                min={1000}
                max={10000000}
                step={10000}
              />
            </div>
            <button onClick={startTraining} style={startButtonStyle} className="admin-button">
              Запустить обучение
            </button>
          </div>
        )}
      </div>

      {/* Checkpoints */}
      <div style={checkpointsCardStyle} className="training-checkpoints">
        <h3 style={{ margin: '0 0 20px 0', color: '#66FCF1' }}>Чекпоинты</h3>
        <div style={checkpointsGridStyle} className="admin-list-grid">
          {checkpoints.map((cp) => (
            <div key={cp.checkpoint_id} style={{
              ...checkpointCardStyle,
              border: cp.is_active ? '2px solid #66FCF1' : '1px solid #45A29E'
            }}>
              <div style={checkpointHeaderStyle}>
                <span style={formatBadgeStyle}>{cp.format}</span>
                {cp.is_active && <span style={activeBadgeStyle}>АКТИВЕН</span>}
              </div>
              <div style={checkpointBodyStyle}>
                <div style={checkpointStatStyle}>
                  <span style={statLabelStyle}>Итерации</span>
                  <span style={statValueStyle}>{formatNumber(cp.training_iterations)}</span>
                </div>
                <div style={checkpointStatStyle}>
                  <span style={statLabelStyle}>Создан</span>
                  <span style={statValueStyle}>{new Date(cp.created_at).toLocaleDateString('ru-RU')}</span>
                </div>
              </div>
              {!cp.is_active && (
                <button
                  onClick={() => activateCheckpoint(cp.checkpoint_id)}
                  style={activateButtonStyle}
                  className="admin-button"
                >
                  Активировать
                </button>
              )}
            </div>
          ))}
          {checkpoints.length === 0 && (
            <div style={emptyStateStyle}>Чекпоинты отсутствуют. Запустите обучение для создания.</div>
          )}
        </div>
      </div>
    </div>
  );
};

const pageStyle: React.CSSProperties = { padding: '12px' };
const loadingStyle: React.CSSProperties = { textAlign: 'center', padding: '50px', color: '#C5C6C7' };
const headerStyle: React.CSSProperties = { marginBottom: '24px', padding: '16px', background: '#1F2833', borderRadius: '8px' };
const controlsCardStyle: React.CSSProperties = { background: '#1F2833', borderRadius: '8px', padding: '20px', marginBottom: '24px' };

// Add responsive padding
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .training-header {
        padding: 20px !important;
        margin-bottom: 28px !important;
      }
      .training-controls {
        padding: 24px !important;
        margin-bottom: 28px !important;
      }
    }
    @media (min-width: 768px) {
      .training-header {
        padding: 20px !important;
        margin-bottom: 30px !important;
      }
      .training-controls {
        padding: 25px !important;
        margin-bottom: 30px !important;
      }
    }
    @media (min-width: 640px) {
      .training-start-form {
        flex-direction: row !important;
        align-items: flex-end !important;
      }
    }
  `;
  document.head.appendChild(style);
}
const progressContainerStyle: React.CSSProperties = { marginBottom: '20px' };
const progressHeaderStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', marginBottom: '10px', color: '#C5C6C7' };
const progressBarBgStyle: React.CSSProperties = { background: '#0B0C10', borderRadius: '10px', height: '20px', overflow: 'hidden' };
const progressBarStyle: React.CSSProperties = { background: 'linear-gradient(90deg, #45A29E, #66FCF1)', height: '100%', borderRadius: '10px', transition: 'width 0.5s' };
const progressStatsStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', marginTop: '10px', color: '#C5C6C7', fontSize: '14px' };
const startFormStyle: React.CSSProperties = { 
  display: 'flex', 
  flexDirection: 'column',
  gap: '16px', 
  alignItems: 'stretch' 
};
const formGroupStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '8px' };
const labelStyle: React.CSSProperties = { color: '#C5C6C7', fontSize: '14px' };
const selectStyle: React.CSSProperties = { 
  padding: '10px 15px', 
  background: '#0B0C10', 
  border: '1px solid #45A29E', 
  borderRadius: '4px', 
  color: '#FFFFFF', 
  fontSize: '16px',
  width: '100%'
};
const inputStyle: React.CSSProperties = { 
  padding: '10px 15px', 
  background: '#0B0C10', 
  border: '1px solid #45A29E', 
  borderRadius: '4px', 
  color: '#FFFFFF', 
  fontSize: '16px', 
  width: '100%'
};
const startButtonStyle: React.CSSProperties = { 
  padding: '12px 30px', 
  background: '#45A29E', 
  border: 'none', 
  borderRadius: '4px', 
  color: '#FFFFFF', 
  cursor: 'pointer', 
  fontWeight: 'bold', 
  fontSize: '16px',
  width: '100%'
};
const stopButtonStyle: React.CSSProperties = { 
  padding: '12px 30px', 
  background: '#F44336', 
  border: 'none', 
  borderRadius: '4px', 
  color: '#FFFFFF', 
  cursor: 'pointer', 
  fontWeight: 'bold', 
  fontSize: '16px',
  width: '100%'
};
const checkpointsCardStyle: React.CSSProperties = { 
  background: '#1F2833', 
  borderRadius: '8px', 
  padding: '20px' 
};

// Add responsive padding
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 768px) {
      .training-checkpoints {
        padding: 25px !important;
      }
    }
  `;
  document.head.appendChild(style);
}
const checkpointsGridStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: '1fr', gap: '16px' };
const checkpointCardStyle: React.CSSProperties = { background: '#0B0C10', borderRadius: '8px', padding: '20px' };
const checkpointHeaderStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' };
const formatBadgeStyle: React.CSSProperties = { background: '#45A29E', padding: '4px 12px', borderRadius: '4px', fontSize: '14px', fontWeight: 'bold' };
const activeBadgeStyle: React.CSSProperties = { background: '#66FCF1', color: '#0B0C10', padding: '4px 12px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' };
const checkpointBodyStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '15px' };
const checkpointStatStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between' };
const statLabelStyle: React.CSSProperties = { color: '#C5C6C7', fontSize: '14px' };
const statValueStyle: React.CSSProperties = { color: '#FFFFFF', fontWeight: 'bold' };
const activateButtonStyle: React.CSSProperties = { width: '100%', padding: '10px', background: 'transparent', border: '1px solid #66FCF1', borderRadius: '4px', color: '#66FCF1', cursor: 'pointer', fontWeight: 'bold' };
const emptyStateStyle: React.CSSProperties = { color: '#C5C6C7', textAlign: 'center', padding: '40px', gridColumn: '1 / -1' };

export default TrainingPage;
