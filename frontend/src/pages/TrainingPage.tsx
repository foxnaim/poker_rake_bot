/**
 * Training Page - управление обучением MCCFR
 */

import React, { useEffect, useState } from 'react';
import axios from 'axios';

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
      setStatus(response.data);
    } catch (error) {
      console.error('Error fetching training status:', error);
    }
  };

  const fetchCheckpoints = async () => {
    try {
      const response = await axios.get('/api/v1/checkpoints');
      setCheckpoints(response.data);
    } catch (error) {
      console.error('Error fetching checkpoints:', error);
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
    return num.toLocaleString('en-US');
  };

  if (loading) {
    return <div style={loadingStyle}>Loading training data...</div>;
  }

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <h1 style={{ margin: 0 }}>MCCFR Training</h1>
      </div>

      {/* Training Controls */}
      <div style={controlsCardStyle}>
        <h3 style={{ margin: '0 0 20px 0', color: '#66FCF1' }}>Training Controls</h3>

        {status?.is_running ? (
          <div>
            <div style={progressContainerStyle}>
              <div style={progressHeaderStyle}>
                <span>Training {status.format}</span>
                <span>{status.total_iterations ? ((status.current_iteration || 0) / status.total_iterations * 100).toFixed(1) : 0}%</span>
              </div>
              <div style={progressBarBgStyle}>
                <div style={{...progressBarStyle, width: `${status.total_iterations ? ((status.current_iteration || 0) / status.total_iterations * 100) : 0}%`}}></div>
              </div>
              <div style={progressStatsStyle}>
                <span>Iteration: {formatNumber(status.current_iteration || 0)} / {formatNumber(status.total_iterations || 0)}</span>
                <span>Started: {status.start_time ? new Date(status.start_time).toLocaleTimeString() : '-'}</span>
                <span>ETA: {status.estimated_completion ? new Date(status.estimated_completion).toLocaleTimeString() : '-'}</span>
              </div>
            </div>
            <button onClick={stopTraining} style={stopButtonStyle}>
              Stop Training
            </button>
          </div>
        ) : (
          <div style={startFormStyle}>
            <div style={formGroupStyle}>
              <label style={labelStyle}>Format:</label>
              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
                style={selectStyle}
              >
                {['NL2', 'NL5', 'NL10', 'NL25', 'NL50', 'NL100'].map(f => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
            <div style={formGroupStyle}>
              <label style={labelStyle}>Iterations:</label>
              <input
                type="number"
                value={iterations}
                onChange={(e) => setIterations(Number(e.target.value))}
                style={inputStyle}
                min={1000}
                max={10000000}
                step={10000}
              />
            </div>
            <button onClick={startTraining} style={startButtonStyle}>
              Start Training
            </button>
          </div>
        )}
      </div>

      {/* Checkpoints */}
      <div style={checkpointsCardStyle}>
        <h3 style={{ margin: '0 0 20px 0', color: '#66FCF1' }}>Checkpoints</h3>
        <div style={checkpointsGridStyle}>
          {checkpoints.map((cp) => (
            <div key={cp.checkpoint_id} style={{
              ...checkpointCardStyle,
              border: cp.is_active ? '2px solid #66FCF1' : '1px solid #45A29E'
            }}>
              <div style={checkpointHeaderStyle}>
                <span style={formatBadgeStyle}>{cp.format}</span>
                {cp.is_active && <span style={activeBadgeStyle}>ACTIVE</span>}
              </div>
              <div style={checkpointBodyStyle}>
                <div style={checkpointStatStyle}>
                  <span style={statLabelStyle}>Iterations</span>
                  <span style={statValueStyle}>{formatNumber(cp.training_iterations)}</span>
                </div>
                <div style={checkpointStatStyle}>
                  <span style={statLabelStyle}>Created</span>
                  <span style={statValueStyle}>{new Date(cp.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              {!cp.is_active && (
                <button
                  onClick={() => activateCheckpoint(cp.checkpoint_id)}
                  style={activateButtonStyle}
                >
                  Activate
                </button>
              )}
            </div>
          ))}
          {checkpoints.length === 0 && (
            <div style={emptyStateStyle}>No checkpoints yet. Start training to create one.</div>
          )}
        </div>
      </div>
    </div>
  );
};

const pageStyle: React.CSSProperties = { padding: '20px' };
const loadingStyle: React.CSSProperties = { textAlign: 'center', padding: '50px', color: '#C5C6C7' };
const headerStyle: React.CSSProperties = { marginBottom: '30px', padding: '20px', background: '#1F2833', borderRadius: '8px' };
const controlsCardStyle: React.CSSProperties = { background: '#1F2833', borderRadius: '8px', padding: '25px', marginBottom: '30px' };
const progressContainerStyle: React.CSSProperties = { marginBottom: '20px' };
const progressHeaderStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', marginBottom: '10px', color: '#C5C6C7' };
const progressBarBgStyle: React.CSSProperties = { background: '#0B0C10', borderRadius: '10px', height: '20px', overflow: 'hidden' };
const progressBarStyle: React.CSSProperties = { background: 'linear-gradient(90deg, #45A29E, #66FCF1)', height: '100%', borderRadius: '10px', transition: 'width 0.5s' };
const progressStatsStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', marginTop: '10px', color: '#C5C6C7', fontSize: '14px' };
const startFormStyle: React.CSSProperties = { display: 'flex', gap: '20px', alignItems: 'flex-end' };
const formGroupStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '8px' };
const labelStyle: React.CSSProperties = { color: '#C5C6C7', fontSize: '14px' };
const selectStyle: React.CSSProperties = { padding: '10px 15px', background: '#0B0C10', border: '1px solid #45A29E', borderRadius: '4px', color: '#FFFFFF', fontSize: '16px' };
const inputStyle: React.CSSProperties = { padding: '10px 15px', background: '#0B0C10', border: '1px solid #45A29E', borderRadius: '4px', color: '#FFFFFF', fontSize: '16px', width: '150px' };
const startButtonStyle: React.CSSProperties = { padding: '12px 30px', background: '#45A29E', border: 'none', borderRadius: '4px', color: '#FFFFFF', cursor: 'pointer', fontWeight: 'bold', fontSize: '16px' };
const stopButtonStyle: React.CSSProperties = { padding: '12px 30px', background: '#F44336', border: 'none', borderRadius: '4px', color: '#FFFFFF', cursor: 'pointer', fontWeight: 'bold', fontSize: '16px' };
const checkpointsCardStyle: React.CSSProperties = { background: '#1F2833', borderRadius: '8px', padding: '25px' };
const checkpointsGridStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '20px' };
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
