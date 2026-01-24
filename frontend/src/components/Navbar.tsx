/**
 * Navigation bar component
 * Beautiful design with React-icons and Framer Motion animations
 */

import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FaChartBar, 
  FaUsers, 
  FaTicketAlt, 
  FaBrain, 
  FaHome,
  FaRobot,
  FaBullseye,
  FaCog,
  FaDollarSign,
  FaBolt,
  FaKey,
  FaDesktop,
  FaClipboardList
} from 'react-icons/fa';
import { GiPokerHand, GiCardPlay } from 'react-icons/gi';

const Navbar: React.FC = () => {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth >= 768) {
        setIsMobileMenuOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isActive = (path: string) => location.pathname === path;

  const navItems = [
    { path: '/', label: 'Панель управления', icon: FaChartBar },
    { path: '/opponents', label: 'Оппоненты', icon: FaUsers },
    { path: '/sessions', label: 'Сессии', icon: FaTicketAlt },
    { path: '/training', label: 'Обучение', icon: FaBrain },
    { path: '/hands', label: 'Раздачи', icon: GiCardPlay },
  ];

  const adminItems = [
    { path: '/admin/rooms', label: 'Комнаты', icon: FaHome },
    { path: '/admin/bots', label: 'Боты', icon: FaRobot },
    { path: '/admin/tables', label: 'Столы', icon: FaBullseye },
    { path: '/admin/bot-configs', label: 'Конфигурации', icon: FaCog },
    { path: '/admin/rake-models', label: 'Рейк', icon: FaDollarSign },
    { path: '/admin/sessions', label: 'Сессии', icon: FaBolt },
    { path: '/admin/api-keys', label: 'API Ключи', icon: FaKey },
    { path: '/admin/agents', label: 'Агенты', icon: FaDesktop },
    { path: '/admin/audit', label: 'Журнал', icon: FaClipboardList },
  ];

  return (
    <>
    <motion.nav
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={navStyle}
      className="navbar"
    >
      <motion.div
        whileHover={{ scale: 1.05 }}
        style={brandStyle}
      >
        <motion.div
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        >
          <GiPokerHand style={{ fontSize: isMobile ? '24px' : '32px', color: '#66FCF1' }} />
        </motion.div>
        <h2 style={brandTitleStyle} className="navbar-brand-title">Покер Рейк Бот</h2>
      </motion.div>
      
      {!isMobile ? (
        <div style={linksStyle} className="navbar-links">
          {navItems.map((item, index) => (
            <NavLink
              key={item.path}
              to={item.path}
              icon={item.icon}
              label={item.label}
              isActive={isActive(item.path)}
              delay={index * 0.05}
            />
          ))}
          
          <motion.div
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, delay: 0.3 }}
            style={separatorStyle}
          />
          
          {adminItems.map((item, index) => (
            <NavLink
              key={item.path}
              to={item.path}
              icon={item.icon}
              label={item.label}
              isActive={isActive(item.path)}
              delay={0.3 + index * 0.05}
            />
          ))}
        </div>
      ) : (
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          style={mobileMenuButtonStyle}
          className="navbar-mobile-menu-button"
          aria-label="Toggle menu"
        >
          <motion.div
            animate={{ rotate: isMobileMenuOpen ? 180 : 0 }}
            transition={{ duration: 0.3 }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#66FCF1" strokeWidth="2">
              {isMobileMenuOpen ? (
                <path d="M18 6L6 18M6 6l12 12" />
              ) : (
                <path d="M3 12h18M3 6h18M3 18h18" />
              )}
            </svg>
          </motion.div>
        </button>
      )}
    </motion.nav>
    
    <AnimatePresence>
      {isMobile && isMobileMenuOpen && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
          style={mobileMenuStyle}
          className="navbar-mobile-menu"
        >
          <div style={mobileMenuContentStyle}>
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                icon={item.icon}
                label={item.label}
                isActive={isActive(item.path)}
                delay={0}
                onClick={() => setIsMobileMenuOpen(false)}
              />
            ))}
            
            <div style={mobileSeparatorStyle} />
            
            {adminItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                icon={item.icon}
                label={item.label}
                isActive={isActive(item.path)}
                delay={0}
                onClick={() => setIsMobileMenuOpen(false)}
              />
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
    </>
  );
};

const NavLink: React.FC<{
  to: string;
  icon: React.ComponentType<any>;
  label: string;
  isActive: boolean;
  delay: number;
  onClick?: () => void;
}> = ({ to, icon: Icon, label, isActive, delay, onClick }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
    >
      <Link to={to} style={{ textDecoration: 'none' }} onClick={onClick}>
        <motion.div
          whileHover={{ scale: 1.05, y: -2 }}
          whileTap={{ scale: 0.95 }}
          style={{
            ...linkStyle,
            ...(isActive ? activeLinkStyle : {})
          }}
          className="navbar-link"
        >
          <motion.div
            animate={isActive ? { 
              rotate: [0, -10, 10, -10, 0],
              scale: [1, 1.2, 1]
            } : {}}
            transition={{ duration: 0.5 }}
            style={iconContainerStyle}
          >
            <Icon style={{ fontSize: '20px' }} />
          </motion.div>
          <span style={linkTextStyle}>{label}</span>
          {isActive && (
            <motion.div
              layoutId="activeIndicator"
              style={activeIndicatorStyle}
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
            />
          )}
        </motion.div>
      </Link>
    </motion.div>
  );
};

// Styles
const navStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
  background: 'linear-gradient(135deg, #1F2937 0%, #111827 100%)',
  borderRadius: '12px',
  marginBottom: '16px',
  border: '1px solid #374151',
  boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)',
  position: 'sticky',
  top: '10px',
  zIndex: 1000
};

// Add responsive padding via CSS
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media (min-width: 640px) {
      .navbar {
        padding: 16px 24px !important;
        margin-bottom: 20px !important;
        top: 16px !important;
      }
    }
    @media (min-width: 768px) {
      .navbar {
        padding: 20px 32px !important;
        margin-bottom: 24px !important;
        top: 20px !important;
        border-radius: 16px !important;
      }
    }
  `;
  document.head.appendChild(style);
}

const brandStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  cursor: 'pointer'
};

const brandTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '18px',
  fontWeight: '700',
  background: 'linear-gradient(135deg, #66FCF1 0%, #45A29E 100%)',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  backgroundClip: 'text',
  whiteSpace: 'nowrap'
};

const linksStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  flexWrap: 'wrap'
};

const linkStyle: React.CSSProperties = {
  color: '#9CA3AF',
  textDecoration: 'none',
  padding: '8px 12px',
  borderRadius: '8px',
  transition: 'all 0.3s ease',
  fontWeight: '500',
  fontSize: '13px',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  position: 'relative',
  overflow: 'hidden'
};

const activeLinkStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #66FCF1 0%, #45A29E 100%)',
  color: '#0B0C10',
  boxShadow: '0 4px 15px rgba(102, 252, 241, 0.4)',
  fontWeight: '700'
};

const iconContainerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
};

const linkTextStyle: React.CSSProperties = {
  whiteSpace: 'nowrap'
};

const activeIndicatorStyle: React.CSSProperties = {
  position: 'absolute',
  bottom: 0,
  left: 0,
  right: 0,
  height: '3px',
  background: '#0B0C10',
  borderRadius: '0 0 12px 12px'
};

const separatorStyle: React.CSSProperties = {
  borderLeft: '2px solid #374151',
  height: '32px',
  margin: '0 8px'
};

const mobileMenuButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: '1px solid #66FCF1',
  borderRadius: '8px',
  padding: '8px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: '#66FCF1'
};

const mobileMenuStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #1F2937 0%, #111827 100%)',
  borderRadius: '16px',
  marginTop: '10px',
  marginBottom: '24px',
  border: '1px solid #374151',
  boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)',
  overflow: 'hidden'
};

const mobileMenuContentStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  padding: '12px'
};

const mobileSeparatorStyle: React.CSSProperties = {
  borderTop: '2px solid #374151',
  margin: '8px 0'
};

// Responsive styles are handled in responsiveStyles.ts utility

export default Navbar;
