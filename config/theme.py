"""Утилиты для работы с цветовой схемой"""

import yaml
from pathlib import Path
from typing import Dict, Any

THEME_CONFIG_PATH = Path(__file__).parent / "theme.yaml"


def load_theme() -> Dict[str, Any]:
    """Загружает конфигурацию цветовой схемы"""
    with open(THEME_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_colors() -> Dict[str, str]:
    """Возвращает словарь с цветами"""
    theme = load_theme()
    return theme.get('colors', {})


def get_swagger_ui_css() -> str:
    """Возвращает CSS для кастомизации Swagger UI"""
    colors = get_colors()
    primary = colors.get('primary', {})
    usage = load_theme().get('usage', {})
    
    return f"""
    <style>
        /* Основная тема Swagger UI */
        .swagger-ui {{
            background: {primary.get('dark', '#0B0C10')};
            color: #FFFFFF;
        }}
        
        .swagger-ui .topbar {{
            background: {primary.get('medium', '#1F2833')};
            border-bottom: 2px solid {primary.get('accent', '#66FCF1')};
        }}
        
        .swagger-ui .topbar .download-url-wrapper {{
            background: {primary.get('light', '#C5C6C7')};
        }}
        
        .swagger-ui .topbar .download-url-wrapper input {{
            border: 1px solid {primary.get('accent', '#66FCF1')};
            color: #FFFFFF;
        }}
        
        .swagger-ui .info {{
            background: {usage.get('backgrounds', {}).get('card', '#1F2833')};
            border: 1px solid {primary.get('light', '#C5C6C7')};
        }}
        
        .swagger-ui .opblock.opblock-post {{
            background: {primary.get('medium', '#1F2833')};
            border-color: {primary.get('accent', '#66FCF1')};
        }}
        
        .swagger-ui .opblock.opblock-get {{
            background: {primary.get('medium', '#1F2833')};
            border-color: {primary.get('light', '#C5C6C7')};
        }}
        
        .swagger-ui .opblock.opblock-put {{
            background: {primary.get('medium', '#1F2833')};
            border-color: {primary.get('accent', '#66FCF1')};
        }}
        
        .swagger-ui .opblock.opblock-delete {{
            background: {primary.get('medium', '#1F2833')};
            border-color: #FF4444;
        }}
        
        .swagger-ui .opblock.opblock-patch {{
            background: {primary.get('medium', '#1F2833')};
            border-color: {primary.get('accent', '#66FCF1')};
        }}
        
        .swagger-ui .opblock .opblock-summary {{
            background: {usage.get('backgrounds', {}).get('panel', '#C5C6C7')};
        }}
        
        .swagger-ui .opblock .opblock-summary:hover {{
            background: {usage.get('backgrounds', {}).get('hover', '#66FCF1')};
        }}
        
        .swagger-ui .btn.execute {{
            background: {primary.get('accent', '#66FCF1')};
            border-color: {primary.get('accent', '#66FCF1')};
        }}
        
        .swagger-ui .btn.execute:hover {{
            background: {primary.get('light', '#C5C6C7')};
        }}
        
        .swagger-ui .scheme-container {{
            background: {primary.get('medium', '#1F2833')};
            border: 1px solid {primary.get('light', '#C5C6C7')};
        }}
        
        .swagger-ui .response-col_status {{
            color: #FFFFFF;
        }}
        
        .swagger-ui .parameter__name {{
            color: #FFFFFF;
        }}
        
        .swagger-ui .model-title {{
            color: #FFFFFF;
        }}
        
        .swagger-ui .model-box {{
            background: {usage.get('backgrounds', {}).get('card', '#1F2833')};
            border: 1px solid {primary.get('light', '#C5C6C7')};
        }}
        
        .swagger-ui code {{
            background: {primary.get('neutral', '#45A29E')};
            color: #FFFFFF;
        }}
        
        .swagger-ui .response-content-type {{
            background: {primary.get('neutral', '#45A29E')};
        }}
        
        /* Скроллбар */
        .swagger-ui ::-webkit-scrollbar {{
            width: 10px;
        }}
        
        .swagger-ui ::-webkit-scrollbar-track {{
            background: {primary.get('dark', '#0B0C10')};
        }}
        
        .swagger-ui ::-webkit-scrollbar-thumb {{
            background: {primary.get('accent', '#66FCF1')};
            border-radius: 5px;
        }}
        
        .swagger-ui ::-webkit-scrollbar-thumb:hover {{
            background: {primary.get('light', '#C5C6C7')};
        }}
    </style>
    """


def get_grafana_colors() -> list:
    """Возвращает список цветов для Grafana в формате hex"""
    colors = get_colors()
    primary = colors.get('primary', {})
    semantic = colors.get('semantic', {})
    
    return [
        primary.get('accent', '#66FCF1'),
        primary.get('light', '#C5C6C7'),
        primary.get('medium', '#1F2833'),
        semantic.get('success', '#00FF88'),
        semantic.get('warning', '#FFB800'),
        semantic.get('error', '#FF4444'),
        semantic.get('info', '#66FCF1'),
    ]
