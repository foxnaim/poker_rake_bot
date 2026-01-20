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
import './App.css';

const App: React.FC = () => {
  return (
    <Router>
      <div className="App" style={appStyle}>
        <Navbar />
        <main style={mainStyle}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/opponents" element={<OpponentsPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/training" element={<TrainingPage />} />
            <Route path="/hands" element={<HandsPage />} />
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
  padding: '20px',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
};

const mainStyle: React.CSSProperties = {
  maxWidth: '1400px',
  margin: '0 auto'
};

export default App;
