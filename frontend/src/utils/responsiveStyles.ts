/**
 * Utility functions for responsive styles
 */

export const addResponsiveStyles = () => {
  if (typeof document === 'undefined') return;
  
  const styleId = 'responsive-styles';
  if (document.getElementById(styleId)) return;
  
  const style = document.createElement('style');
  style.id = styleId;
  style.textContent = `
    /* Admin pages responsive styles */
    @media (max-width: 639px) {
      .admin-page-container {
        padding: 12px !important;
      }
      .admin-page-header {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 12px !important;
      }
      .admin-list-grid {
        grid-template-columns: 1fr !important;
        gap: 16px !important;
      }
      .admin-stats-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 12px !important;
      }
      .admin-form-grid {
        grid-template-columns: 1fr !important;
      }
      .admin-table-wrapper {
        overflow-x: auto !important;
      }
      .admin-table-wrapper table {
        font-size: 12px !important;
        min-width: 600px;
      }
      .admin-table-wrapper th,
      .admin-table-wrapper td {
        padding: 8px 4px !important;
      }
    }
    
    @media (min-width: 640px) {
      .admin-page-container {
        padding: 16px !important;
      }
      .admin-page-header {
        flex-direction: row !important;
        align-items: center !important;
      }
      .admin-list-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 18px !important;
      }
      .admin-stats-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 15px !important;
      }
    }
    
    @media (min-width: 768px) {
      .admin-page-container {
        padding: 20px !important;
      }
      .admin-list-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 20px !important;
      }
      .admin-stats-grid {
        grid-template-columns: repeat(4, 1fr) !important;
      }
    }
    
    @media (min-width: 1024px) {
      .admin-list-grid {
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)) !important;
      }
      .admin-table-wrapper table {
        font-size: 14px !important;
        min-width: auto;
      }
      .admin-table-wrapper th,
      .admin-table-wrapper td {
        padding: 12px 15px !important;
      }
    }
    
    /* Form responsive styles */
    @media (max-width: 639px) {
      .admin-form-row {
        flex-direction: column !important;
        gap: 10px !important;
      }
      .admin-form-col {
        width: 100% !important;
      }
    }
    
    /* Button responsive styles */
    @media (max-width: 639px) {
      .admin-button {
        width: 100% !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
      }
    }
    
    /* Card responsive styles */
    @media (max-width: 639px) {
      .admin-card {
        padding: 16px !important;
      }
      .admin-card-header {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 12px !important;
      }
    }
    
    /* Filter responsive styles */
    @media (min-width: 640px) {
      .admin-form-row {
        flex-direction: row !important;
        align-items: center !important;
      }
    }
    
    /* Input responsive styles */
    @media (max-width: 639px) {
      .admin-input {
        min-width: 100% !important;
        font-size: 16px !important;
      }
      input[type="text"],
      input[type="number"],
      select,
      textarea {
        font-size: 16px !important;
      }
    }
    
    /* Form row responsive */
    @media (max-width: 639px) {
      .admin-form-row {
        flex-direction: column !important;
      }
      .admin-form-col {
        width: 100% !important;
        flex: 1 1 100% !important;
      }
    }
    
    /* Chart responsive */
    @media (max-width: 1023px) {
      .recharts-wrapper {
        width: 100% !important;
      }
      .recharts-surface {
        width: 100% !important;
      }
    }
    
    /* Button group responsive */
    @media (min-width: 640px) {
      .admin-button-group {
        flex-direction: row !important;
        width: auto !important;
      }
      .admin-button-group .admin-button {
        width: auto !important;
      }
    }
    
    /* Filter responsive */
    @media (min-width: 640px) {
      .admin-form-row {
        flex-direction: row !important;
        align-items: center !important;
      }
      .admin-select-filter {
        min-width: 200px !important;
      }
    }
    @media (min-width: 768px) {
      .admin-select-filter {
        min-width: 300px !important;
      }
    }
    
    /* User pages responsive */
    @media (max-width: 639px) {
      .user-page-container {
        padding: 12px !important;
      }
      .user-page-header {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 12px !important;
      }
      .user-table-wrapper {
        overflow-x: auto !important;
      }
      .user-table-wrapper table {
        font-size: 12px !important;
        min-width: 600px;
      }
    }
    
    @media (min-width: 640px) {
      .user-page-container {
        padding: 16px !important;
      }
      .user-page-header {
        flex-direction: row !important;
        align-items: center !important;
      }
    }
    
    @media (min-width: 768px) {
      .user-page-container {
        padding: 20px !important;
      }
    }
    
    /* Opponents page specific */
    @media (min-width: 640px) {
      .opponents-stats {
        flex-direction: row !important;
        gap: 20px !important;
      }
    }
    
    /* Hands page specific */
    @media (min-width: 640px) {
      .hands-summary {
        flex-direction: row !important;
        gap: 20px !important;
      }
    }
    
    /* Sessions page specific */
    @media (min-width: 640px) {
      .session-start-group {
        flex-direction: row !important;
      }
    }
    @media (min-width: 768px) {
      .session-active-stats {
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 20px !important;
      }
    }
    
    /* Table responsive for all user tables */
    @media (max-width: 639px) {
      .opponents-table-wrapper table,
      .hands-table-wrapper table,
      .sessions-table-wrapper table {
        font-size: 12px !important;
        min-width: 600px;
      }
      .opponents-table-wrapper th,
      .opponents-table-wrapper td,
      .hands-table-wrapper th,
      .hands-table-wrapper td,
      .sessions-table-wrapper th,
      .sessions-table-wrapper td {
        padding: 8px 4px !important;
      }
    }
    
    /* Navbar responsive */
    @media (max-width: 767px) {
      .navbar-brand-title {
        font-size: 18px !important;
      }
      .navbar-links {
        display: none !important;
      }
    }
    @media (min-width: 768px) {
      .navbar-mobile-menu {
        display: none !important;
      }
    }
    
    /* Dashboard responsive */
    @media (min-width: 640px) {
      .dashboard-page {
        padding: 16px !important;
      }
      .dashboard-header {
        flex-direction: row !important;
        padding: 20px 24px !important;
        margin-bottom: 28px !important;
        border-radius: 14px !important;
      }
      .dashboard-title {
        font-size: 28px !important;
      }
      .dashboard-stats-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 20px !important;
        margin-bottom: 28px !important;
      }
    }
    @media (min-width: 768px) {
      .dashboard-page {
        padding: 20px !important;
      }
      .dashboard-header {
        padding: 24px 28px !important;
        margin-bottom: 32px !important;
        border-radius: 16px !important;
      }
      .dashboard-title {
        font-size: 32px !important;
      }
      .dashboard-charts-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 20px !important;
        margin-bottom: 28px !important;
      }
    }
    @media (min-width: 1024px) {
      .dashboard-stats-grid {
        grid-template-columns: repeat(3, 1fr) !important;
        gap: 24px !important;
        margin-bottom: 32px !important;
      }
      .dashboard-charts-grid {
        grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)) !important;
        gap: 24px !important;
        margin-bottom: 32px !important;
      }
      .dashboard-actions-grid {
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)) !important;
        gap: 16px !important;
      }
    }
    @media (min-width: 1280px) {
      .dashboard-stats-grid {
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)) !important;
      }
      .dashboard-charts-grid {
        grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)) !important;
      }
    }
    
    /* Chart card responsive */
    @media (max-width: 767px) {
      .dashboard-chart-card {
        padding: 16px !important;
        border-radius: 12px !important;
      }
      .dashboard-chart-title {
        font-size: 16px !important;
      }
      .dashboard-chart-container {
        overflow-x: auto !important;
      }
      .dashboard-chart-container .recharts-wrapper {
        min-width: 100% !important;
      }
      .dashboard-chart-container .recharts-surface {
        width: 100% !important;
      }
      .dashboard-chart-container .recharts-responsive-container {
        height: 250px !important;
      }
    }
    @media (min-width: 768px) and (max-width: 1023px) {
      .dashboard-chart-card {
        padding: 20px !important;
      }
      .dashboard-chart-title {
        font-size: 18px !important;
      }
      .dashboard-chart-container .recharts-responsive-container {
        height: 280px !important;
      }
    }
    @media (min-width: 1024px) {
      .dashboard-chart-card {
        padding: 28px !important;
      }
      .dashboard-chart-title {
        font-size: 20px !important;
      }
      .dashboard-chart-container .recharts-responsive-container {
        height: 300px !important;
      }
    }
  `;
  document.head.appendChild(style);
};
