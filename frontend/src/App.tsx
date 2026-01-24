/**
 * Main App component with routing
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import OpponentsPage from './pages/OpponentsPage';
import SessionsPage from './pages/SessionsPage';
import TrainingPage from './pages/TrainingPage';
import HandsPage from './pages/HandsPage';
import AdminRoomsPage from './pages/AdminRoomsPage';
import AdminBotsPage from './pages/AdminBotsPage';
import AdminSessionsPage from './pages/AdminSessionsPage';
import AdminTablesPage from './pages/AdminTablesPage';
import AdminBotConfigsPage from './pages/AdminBotConfigsPage';
import AdminRakeModelsPage from './pages/AdminRakeModelsPage';
import AdminAPIKeysPage from './pages/AdminAPIKeysPage';
import AdminAgentsPage from './pages/AdminAgentsPage';
import AdminAuditPage from './pages/AdminAuditPage';
import './App.css';

const App: React.FC = () => {
  return (
    <Router
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <div className="App" style={appStyle}>
        <Navbar />
        <main style={mainStyle}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/opponents" element={<OpponentsPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/training" element={<TrainingPage />} />
            <Route path="/hands" element={<HandsPage />} />
            <Route path="/admin/rooms" element={<AdminRoomsPage />} />
            <Route path="/admin/bots" element={<AdminBotsPage />} />
            <Route path="/admin/tables" element={<AdminTablesPage />} />
            <Route path="/admin/bot-configs" element={<AdminBotConfigsPage />} />
            <Route path="/admin/rake-models" element={<AdminRakeModelsPage />} />
            <Route path="/admin/api-keys" element={<AdminAPIKeysPage />} />
            <Route path="/admin/sessions" element={<AdminSessionsPage />} />
            <Route path="/admin/agents" element={<AdminAgentsPage />} />
            <Route path="/admin/audit" element={<AdminAuditPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

const appStyle: React.CSSProperties = {
  minHeight: '100vh',
  background: '#0B0C10',
  color: '#FFFFFF',
  padding: '10px',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
};

const mainStyle: React.CSSProperties = {
  maxWidth: '1400px',
  margin: '0 auto',
  width: '100%'
};

// Add responsive styles via CSS classes
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .App {
        padding: 16px !important;
      }
    }
    @media (min-width: 768px) {
      .App {
        padding: 20px !important;
      }
    }
  `;
  document.head.appendChild(style);
}

export default App;
