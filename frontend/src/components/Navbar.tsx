/**
 * Navigation bar component
 * Beautiful design with React-icons and Framer Motion animations
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
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
    <motion.nav
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={navStyle}
    >
      <motion.div
        whileHover={{ scale: 1.05 }}
        style={brandStyle}
      >
        <motion.div
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        >
          <GiPokerHand style={{ fontSize: '32px', color: '#66FCF1' }} />
        </motion.div>
        <h2 style={brandTitleStyle}>Покер Рейк Бот</h2>
      </motion.div>
      
      <div style={linksStyle}>
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
    </motion.nav>
  );
};

const NavLink: React.FC<{
  to: string;
  icon: React.ComponentType<any>;
  label: string;
  isActive: boolean;
  delay: number;
}> = ({ to, icon: Icon, label, isActive, delay }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
    >
      <Link to={to} style={{ textDecoration: 'none' }}>
        <motion.div
          whileHover={{ scale: 1.05, y: -2 }}
          whileTap={{ scale: 0.95 }}
          style={{
            ...linkStyle,
            ...(isActive ? activeLinkStyle : {})
          }}
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
  padding: '20px 32px',
  background: 'linear-gradient(135deg, #1F2937 0%, #111827 100%)',
  borderRadius: '16px',
  marginBottom: '24px',
  border: '1px solid #374151',
  boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)',
  position: 'sticky',
  top: '20px',
  zIndex: 1000
};

const brandStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  cursor: 'pointer'
};

const brandTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '24px',
  fontWeight: '700',
  background: 'linear-gradient(135deg, #66FCF1 0%, #45A29E 100%)',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  backgroundClip: 'text'
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
  padding: '12px 20px',
  borderRadius: '12px',
  transition: 'all 0.3s ease',
  fontWeight: '500',
  fontSize: '14px',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
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

export default Navbar;
