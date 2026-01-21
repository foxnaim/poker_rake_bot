/**
 * Admin page for managing bot agents (physical bot instances)
 */

import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface Agent {
  agent_id: string;
  status: string;
  last_seen: string;
  version: string | null;
  assigned_session_id: number | null;
  heartbeat_lag_seconds: number | null;
}

const AdminAgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commandAgent, setCommandAgent] = useState<string | null>(null);
  const [commandType, setCommandType] = useState<string>('pause');
  const [commandReason, setCommandReason] = useState<string>('');

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await axios.get('/api/v1/agents', {
        headers: { 'X-Admin-Key': localStorage.getItem('adminKey') || '' }
      });
      setAgents(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch agents');
    } finally {
      setLoading(false);
    }
  };

  const sendCommand = async (agentId: string) => {
    try {
      await axios.post(`/api/v1/agent/${agentId}/command`, {
        command: commandType,
        reason: commandReason
      }, {
        headers: { 'X-Admin-Key': localStorage.getItem('adminKey') || '' }
      });
      setCommandAgent(null);
      setCommandReason('');
      alert(`Command ${commandType} sent to ${agentId}`);
    } catch (err: any) {
      alert(`Error: ${err.response?.data?.detail || 'Failed to send command'}`);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return '#4CAF50';
      case 'offline': return '#F44336';
      case 'busy': return '#FFA726';
      default: return '#9E9E9E';
    }
  };

  const formatLastSeen = (lastSeen: string) => {
    if (!lastSeen) return 'Never';
    const date = new Date(lastSeen);
    return date.toLocaleString();
  };

  if (loading) {
    return <div style={loadingStyle}>Loading agents...</div>;
  }

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <h1 style={{ margin: 0 }}>Agent Management</h1>
        <p style={{ margin: '5px 0 0 0', color: '#C5C6C7' }}>
          Monitor and control bot agents in real-time
        </p>
      </div>

      {error && <div style={errorStyle}>{error}</div>}

      {/* Stats Summary */}
      <div style={statsRowStyle}>
        <div style={statBoxStyle}>
          <div style={statValueStyle}>{agents.length}</div>
          <div style={statLabelStyle}>Total Agents</div>
        </div>
        <div style={statBoxStyle}>
          <div style={{ ...statValueStyle, color: '#4CAF50' }}>
            {agents.filter(a => a.status === 'online').length}
          </div>
          <div style={statLabelStyle}>Online</div>
        </div>
        <div style={statBoxStyle}>
          <div style={{ ...statValueStyle, color: '#F44336' }}>
            {agents.filter(a => a.status === 'offline').length}
          </div>
          <div style={statLabelStyle}>Offline</div>
        </div>
        <div style={statBoxStyle}>
          <div style={{ ...statValueStyle, color: '#FFA726' }}>
            {agents.filter(a => a.assigned_session_id).length}
          </div>
          <div style={statLabelStyle}>In Session</div>
        </div>
      </div>

      {/* Agents Grid */}
      <div style={agentsGridStyle}>
        {agents.length === 0 ? (
          <div style={emptyStyle}>No agents registered yet</div>
        ) : (
          agents.map(agent => (
            <div key={agent.agent_id} style={agentCardStyle}>
              <div style={agentHeaderStyle}>
                <span style={{
                  ...statusDotStyle,
                  background: getStatusColor(agent.status)
                }} />
                <span style={agentIdStyle}>{agent.agent_id}</span>
                <span style={{
                  ...statusBadgeStyle,
                  background: getStatusColor(agent.status)
                }}>
                  {agent.status.toUpperCase()}
                </span>
              </div>

              <div style={agentInfoStyle}>
                <div style={infoRowStyle}>
                  <span style={infoLabelStyle}>Last Seen:</span>
                  <span>{formatLastSeen(agent.last_seen)}</span>
                </div>
                <div style={infoRowStyle}>
                  <span style={infoLabelStyle}>Version:</span>
                  <span>{agent.version || 'Unknown'}</span>
                </div>
                <div style={infoRowStyle}>
                  <span style={infoLabelStyle}>Session:</span>
                  <span>{agent.assigned_session_id || 'None'}</span>
                </div>
                <div style={infoRowStyle}>
                  <span style={infoLabelStyle}>Heartbeat Lag:</span>
                  <span style={{
                    color: (agent.heartbeat_lag_seconds || 0) > 30 ? '#F44336' : '#4CAF50'
                  }}>
                    {agent.heartbeat_lag_seconds?.toFixed(1) || '0'}s
                  </span>
                </div>
              </div>

              <div style={agentActionsStyle}>
                {commandAgent === agent.agent_id ? (
                  <div style={commandFormStyle}>
                    <select
                      value={commandType}
                      onChange={e => setCommandType(e.target.value)}
                      style={selectStyle}
                    >
                      <option value="pause">Pause</option>
                      <option value="resume">Resume</option>
                      <option value="stop">Stop</option>
                      <option value="sit_out">Sit Out</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Reason (optional)"
                      value={commandReason}
                      onChange={e => setCommandReason(e.target.value)}
                      style={inputStyle}
                    />
                    <div style={buttonRowStyle}>
                      <button
                        onClick={() => sendCommand(agent.agent_id)}
                        style={sendButtonStyle}
                      >
                        Send
                      </button>
                      <button
                        onClick={() => setCommandAgent(null)}
                        style={cancelButtonStyle}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setCommandAgent(agent.agent_id)}
                    style={commandButtonStyle}
                    disabled={agent.status === 'offline'}
                  >
                    Send Command
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// Styles
const pageStyle: React.CSSProperties = { padding: '20px' };
const loadingStyle: React.CSSProperties = { textAlign: 'center', padding: '50px', color: '#C5C6C7' };
const headerStyle: React.CSSProperties = { marginBottom: '30px', padding: '20px', background: '#1F2833', borderRadius: '8px' };
const errorStyle: React.CSSProperties = { background: '#F44336', color: '#FFFFFF', padding: '15px', borderRadius: '8px', marginBottom: '20px' };

const statsRowStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px', marginBottom: '30px' };
const statBoxStyle: React.CSSProperties = { background: '#1F2833', padding: '20px', borderRadius: '8px', textAlign: 'center' };
const statValueStyle: React.CSSProperties = { fontSize: '32px', fontWeight: 'bold', color: '#66FCF1' };
const statLabelStyle: React.CSSProperties = { color: '#C5C6C7', marginTop: '5px' };

const agentsGridStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '20px' };
const emptyStyle: React.CSSProperties = { textAlign: 'center', padding: '40px', color: '#C5C6C7', gridColumn: '1 / -1' };

const agentCardStyle: React.CSSProperties = { background: '#1F2833', borderRadius: '8px', padding: '20px' };
const agentHeaderStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px', paddingBottom: '15px', borderBottom: '1px solid #45A29E' };
const statusDotStyle: React.CSSProperties = { width: '12px', height: '12px', borderRadius: '50%' };
const agentIdStyle: React.CSSProperties = { flex: 1, fontWeight: 'bold', fontSize: '16px' };
const statusBadgeStyle: React.CSSProperties = { padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 'bold', color: '#FFFFFF' };

const agentInfoStyle: React.CSSProperties = { marginBottom: '15px' };
const infoRowStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #2C3440' };
const infoLabelStyle: React.CSSProperties = { color: '#C5C6C7' };

const agentActionsStyle: React.CSSProperties = { marginTop: '15px' };
const commandButtonStyle: React.CSSProperties = { width: '100%', padding: '12px', background: '#45A29E', border: 'none', borderRadius: '6px', color: '#FFFFFF', cursor: 'pointer', fontWeight: 'bold' };

const commandFormStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '10px' };
const selectStyle: React.CSSProperties = { padding: '10px', background: '#0B0C10', border: '1px solid #45A29E', borderRadius: '6px', color: '#FFFFFF' };
const inputStyle: React.CSSProperties = { padding: '10px', background: '#0B0C10', border: '1px solid #45A29E', borderRadius: '6px', color: '#FFFFFF' };
const buttonRowStyle: React.CSSProperties = { display: 'flex', gap: '10px' };
const sendButtonStyle: React.CSSProperties = { flex: 1, padding: '10px', background: '#4CAF50', border: 'none', borderRadius: '6px', color: '#FFFFFF', cursor: 'pointer', fontWeight: 'bold' };
const cancelButtonStyle: React.CSSProperties = { flex: 1, padding: '10px', background: '#F44336', border: 'none', borderRadius: '6px', color: '#FFFFFF', cursor: 'pointer', fontWeight: 'bold' };

export default AdminAgentsPage;
