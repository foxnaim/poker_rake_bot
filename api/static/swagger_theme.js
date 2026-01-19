// Кастомная тема для Swagger UI
// Инжектируется после загрузки Swagger UI

(function() {
    'use strict';
    
    const colors = {
        dark: '#0B0C10',
        medium: '#1F2833',
        light: '#C5C6C7',
        accent: '#66FCF1',
        neutral: '#45A29E'
    };
    
    const style = document.createElement('style');
    style.textContent = `
        /* Основная тема Swagger UI */
        .swagger-ui {
            background: ${colors.dark} !important;
            color: #FFFFFF !important;
        }
        
        .swagger-ui .topbar {
            background: ${colors.medium} !important;
            border-bottom: 2px solid ${colors.accent} !important;
        }
        
        .swagger-ui .topbar .download-url-wrapper {
            background: ${colors.light} !important;
        }
        
        .swagger-ui .topbar .download-url-wrapper input {
            border: 1px solid ${colors.accent} !important;
            color: #FFFFFF !important;
            background: ${colors.neutral} !important;
        }
        
        .swagger-ui .info {
            background: ${colors.medium} !important;
            border: 1px solid ${colors.light} !important;
        }
        
        .swagger-ui .opblock.opblock-post {
            background: ${colors.medium} !important;
            border-color: ${colors.accent} !important;
        }
        
        .swagger-ui .opblock.opblock-get {
            background: ${colors.medium} !important;
            border-color: ${colors.light} !important;
        }
        
        .swagger-ui .opblock.opblock-put {
            background: ${colors.medium} !important;
            border-color: ${colors.accent} !important;
        }
        
        .swagger-ui .opblock.opblock-delete {
            background: ${colors.medium} !important;
            border-color: #FF4444 !important;
        }
        
        .swagger-ui .opblock.opblock-patch {
            background: ${colors.medium} !important;
            border-color: ${colors.accent} !important;
        }
        
        .swagger-ui .opblock .opblock-summary {
            background: ${colors.light} !important;
        }
        
        .swagger-ui .opblock .opblock-summary:hover {
            background: ${colors.accent} !important;
        }
        
        .swagger-ui .btn.execute {
            background: ${colors.accent} !important;
            border-color: ${colors.accent} !important;
        }
        
        .swagger-ui .btn.execute:hover {
            background: ${colors.light} !important;
        }
        
        .swagger-ui .scheme-container {
            background: ${colors.medium} !important;
            border: 1px solid ${colors.light} !important;
        }
        
        .swagger-ui .response-col_status {
            color: #FFFFFF !important;
        }
        
        .swagger-ui .parameter__name {
            color: #FFFFFF !important;
        }
        
        .swagger-ui .model-title {
            color: #FFFFFF !important;
        }
        
        .swagger-ui .model-box {
            background: ${colors.medium} !important;
            border: 1px solid ${colors.light} !important;
        }
        
        .swagger-ui code {
            background: ${colors.neutral} !important;
            color: #FFFFFF !important;
        }
        
        .swagger-ui .response-content-type {
            background: ${colors.neutral} !important;
        }
        
        .swagger-ui .parameter__name,
        .swagger-ui .parameter__type,
        .swagger-ui .prop-name,
        .swagger-ui .prop-type {
            color: #FFFFFF !important;
        }
        
        /* Скроллбар */
        .swagger-ui ::-webkit-scrollbar {
            width: 10px;
        }
        
        .swagger-ui ::-webkit-scrollbar-track {
            background: ${colors.dark} !important;
        }
        
        .swagger-ui ::-webkit-scrollbar-thumb {
            background: ${colors.accent} !important;
            border-radius: 5px;
        }
        
        .swagger-ui ::-webkit-scrollbar-thumb:hover {
            background: ${colors.light} !important;
        }
        
        body {
            background: ${colors.dark} !important;
        }
    `;
    
    // Добавляем стили после загрузки DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            document.head.appendChild(style);
        });
    } else {
        document.head.appendChild(style);
    }
})();
