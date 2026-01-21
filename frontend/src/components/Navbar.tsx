/**
 * Navigation bar component
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navbar: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav style={navStyle}>
      <div style={brandStyle}>
        <span style={{ fontSize: '24px' }}>🎰</span>
        <h2 style={{ margin: 0, marginLeft: '10px' }}>Poker Rake Bot</h2>
      </div>
      
      <div style={linksStyle}>
        <Link 
          to="/" 
          style={{...linkStyle, ...(isActive('/') ? activeLinkStyle : {})}}
        >
          📊 Dashboard
        </Link>
        <Link 
          to="/opponents" 
          style={{...linkStyle, ...(isActive('/opponents') ? activeLinkStyle : {})}}
        >
          👥 Opponents
        </Link>
        <Link 
          to="/sessions" 
          style={{...linkStyle, ...(isActive('/sessions') ? activeLinkStyle : {})}}
        >
          🎮 Sessions
        </Link>
        <Link 
          to="/training" 
          style={{...linkStyle, ...(isActive('/training') ? activeLinkStyle : {})}}
        >
          🧠 Training
        </Link>
        <Link 
          to="/hands" 
          style={{...linkStyle, ...(isActive('/hands') ? activeLinkStyle : {})}}
        >
          🃏 Hands
        </Link>
        <div style={{ borderLeft: '1px solid #C5C6C7', margin: '0 10px', height: '30px' }} />
        <Link 
          to="/admin/rooms" 
          style={{...linkStyle, ...(isActive('/admin/rooms') ? activeLinkStyle : {})}}
        >
          🏠 Rooms
        </Link>
        <Link 
          to="/admin/bots" 
          style={{...linkStyle, ...(isActive('/admin/bots') ? activeLinkStyle : {})}}
        >
          🤖 Bots
        </Link>
        <Link 
          to="/admin/tables" 
          style={{...linkStyle, ...(isActive('/admin/tables') ? activeLinkStyle : {})}}
        >
          🎯 Tables
        </Link>
        <Link 
          to="/admin/bot-configs" 
          style={{...linkStyle, ...(isActive('/admin/bot-configs') ? activeLinkStyle : {})}}
        >
          ⚙️ Configs
        </Link>
        <Link 
          to="/admin/rake-models" 
          style={{...linkStyle, ...(isActive('/admin/rake-models') ? activeLinkStyle : {})}}
        >
          💰 Rake
        </Link>
        <Link 
          to="/admin/sessions" 
          style={{...linkStyle, ...(isActive('/admin/sessions') ? activeLinkStyle : {})}}
        >
          ⚡ Sessions
        </Link>
        <Link 
          to="/admin/api-keys" 
          style={{...linkStyle, ...(isActive('/admin/api-keys') ? activeLinkStyle : {})}}
        >
          🔑 API Keys
        </Link>
      </div>
    </nav>
  );
};

const navStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '15px 30px',
  background: '#1F2833',
  borderRadius: '8px',
  marginBottom: '20px',
  border: '1px solid #C5C6C7'
};

const brandStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  color: '#66FCF1'
};

const linksStyle: React.CSSProperties = {
  display: 'flex',
  gap: '20px'
};

const linkStyle: React.CSSProperties = {
  color: '#C5C6C7',
  textDecoration: 'none',
  padding: '8px 16px',
  borderRadius: '4px',
  transition: 'all 0.3s',
  fontWeight: 500
};

const activeLinkStyle: React.CSSProperties = {
  background: '#66FCF1',
  color: '#0B0C10'
};

export default Navbar;
