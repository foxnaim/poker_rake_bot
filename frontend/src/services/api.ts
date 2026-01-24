/**
 * API клиент для взаимодействия с backend
 */

// Используем относительный путь для прокси или переменную окружения
// В браузере относительный путь будет работать через прокси из package.json
// Принудительно используем относительные пути, если переменная содержит 'api:' (Docker hostname)
// или если мы в браузере (window определен)
const envUrl = process.env.REACT_APP_API_URL || '';
const isBrowser = typeof window !== 'undefined';
const API_BASE_URL = (envUrl.includes('api:') || (isBrowser && !envUrl)) ? '' : envUrl;

// Логирование для отладки (только в development)
if (process.env.NODE_ENV === 'development') {
  console.log('API_BASE_URL:', API_BASE_URL || '(relative - using proxy)');
  console.log('REACT_APP_API_URL:', envUrl || '(not set)');
}

export interface GameStateRequest {
  hand_id: string;
  table_id: string;
  limit_type: string;
  street: string;
  hero_position: number;
  dealer: number;
  hero_cards: string;
  board_cards?: string;
  stacks: Record<string, string>;
  bets: Record<string, string>;
  total_bets: Record<string, string>;
  active_players: number[];
  pot: number;
  current_player: number;
  last_raise_amount: number;
  small_blind: number;
  big_blind: number;
  opponent_ids?: string[];
}

export interface DecisionResponse {
  action: string;
  amount?: number;
  reasoning?: any;
  latency_ms: number;
  cached?: boolean;
}

export class APIClient {
  private apiKey: string | null = null;

  constructor() {
    // В development режиме используем dev ключ автоматически
    if (process.env.NODE_ENV === 'development') {
      this.apiKey = 'dev_admin_key';
    }
  }

  setApiKey(key: string) {
    this.apiKey = key;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.apiKey) {
      (headers as Record<string, string>)['X-API-Key'] = this.apiKey;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  }

  async decide(request: GameStateRequest): Promise<DecisionResponse> {
    return this.request<DecisionResponse>('/api/v1/decide', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async logHand(handData: any): Promise<any> {
    return this.request('/api/v1/log_hand', {
      method: 'POST',
      body: JSON.stringify(handData),
    });
  }

  async getOpponentProfile(opponentId: string): Promise<any> {
    return this.request(`/api/v1/opponent/${opponentId}`);
  }

  async getHealth(): Promise<any> {
    return this.request('/api/v1/health');
  }

  // Week 2: Admin API methods
  async getBots(): Promise<any[]> {
    return this.request('/api/v1/admin/bots');
  }

  async createBot(bot: any): Promise<any> {
    return this.request('/api/v1/admin/bots', {
      method: 'POST',
      body: JSON.stringify(bot),
    });
  }

  async updateBot(botId: number, bot: any): Promise<any> {
    return this.request(`/api/v1/admin/bots/${botId}`, {
      method: 'PATCH',
      body: JSON.stringify(bot),
    });
  }

  async deleteBot(botId: number): Promise<void> {
    return this.request(`/api/v1/admin/bots/${botId}`, {
      method: 'DELETE',
    });
  }

  async getRooms(): Promise<any[]> {
    return this.request('/api/v1/admin/rooms');
  }

  async createRoom(room: any): Promise<any> {
    return this.request('/api/v1/admin/rooms', {
      method: 'POST',
      body: JSON.stringify(room),
    });
  }

  async onboardRoom(room: any): Promise<any> {
    return this.request('/api/v1/admin/rooms/onboard', {
      method: 'POST',
      body: JSON.stringify(room),
    });
  }

  async getTables(roomId?: number): Promise<any[]> {
    const url = roomId 
      ? `/api/v1/admin/tables?room_id=${roomId}`
      : '/api/v1/admin/tables';
    return this.request(url);
  }

  async createTable(table: any): Promise<any> {
    return this.request('/api/v1/admin/tables', {
      method: 'POST',
      body: JSON.stringify(table),
    });
  }

  async updateTable(tableId: number, table: any): Promise<any> {
    return this.request(`/api/v1/admin/tables/${tableId}`, {
      method: 'PATCH',
      body: JSON.stringify(table),
    });
  }

  async deleteTable(tableId: number): Promise<void> {
    return this.request(`/api/v1/admin/tables/${tableId}`, {
      method: 'DELETE',
    });
  }

  async getRakeModels(roomId?: number): Promise<any[]> {
    const url = roomId 
      ? `/api/v1/admin/rake-models?room_id=${roomId}`
      : '/api/v1/admin/rake-models';
    return this.request(url);
  }

  async createRakeModel(model: any): Promise<any> {
    return this.request('/api/v1/admin/rake-models', {
      method: 'POST',
      body: JSON.stringify(model),
    });
  }

  async updateRakeModel(modelId: number, model: any): Promise<any> {
    return this.request(`/api/v1/admin/rake-models/${modelId}`, {
      method: 'PATCH',
      body: JSON.stringify(model),
    });
  }

  async deleteRakeModel(modelId: number): Promise<void> {
    return this.request(`/api/v1/admin/rake-models/${modelId}`, {
      method: 'DELETE',
    });
  }

  async getBotConfigs(botId?: number): Promise<any[]> {
    const url = botId 
      ? `/api/v1/admin/bot-configs?bot_id=${botId}`
      : '/api/v1/admin/bot-configs';
    return this.request(url);
  }

  async createBotConfig(config: any): Promise<any> {
    return this.request('/api/v1/admin/bot-configs', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async updateBotConfig(configId: number, config: any): Promise<any> {
    return this.request(`/api/v1/admin/bot-configs/${configId}`, {
      method: 'PATCH',
      body: JSON.stringify(config),
    });
  }

  async deleteBotConfig(configId: number): Promise<void> {
    return this.request(`/api/v1/admin/bot-configs/${configId}`, {
      method: 'DELETE',
    });
  }

  async startSession(session: any): Promise<any> {
    return this.request('/api/v1/admin/session/start', {
      method: 'POST',
      body: JSON.stringify(session),
    });
  }

  async pauseSession(sessionId: string): Promise<any> {
    return this.request(`/api/v1/admin/session/${sessionId}/pause`, {
      method: 'POST',
    });
  }

  async stopSession(sessionId: string): Promise<any> {
    return this.request(`/api/v1/admin/session/${sessionId}/stop`, {
      method: 'POST',
    });
  }

  async getRecentSessions(limit: number = 50): Promise<any[]> {
    return this.request(`/api/v1/admin/sessions/recent?limit=${limit}`);
  }

  async getSession(sessionId: string): Promise<any> {
    return this.request(`/api/v1/admin/session/${sessionId}`);
  }

  // Audit Log methods
  async getAuditLog(limit: number = 100, action?: string, entityType?: string): Promise<any[]> {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    if (action) params.append('action', action);
    if (entityType) params.append('entity_type', entityType);
    return this.request(`/api/v1/admin/audit?${params.toString()}`);
  }

  async getAuditSummary(): Promise<any> {
    return this.request('/api/v1/admin/audit/summary');
  }

  async getEntityAudit(entityType: string, entityId: number): Promise<any[]> {
    return this.request(`/api/v1/admin/audit/entity/${entityType}/${entityId}`);
  }

  // API Keys management
  async getApiKeys(): Promise<any[]> {
    return this.request('/api/v1/admin/api-keys');
  }

  async createApiKey(keyData: any): Promise<any> {
    return this.request('/api/v1/admin/api-keys', {
      method: 'POST',
      body: JSON.stringify(keyData),
    });
  }

  async deleteApiKey(keyId: number): Promise<void> {
    return this.request(`/api/v1/admin/api-keys/${keyId}`, {
      method: 'DELETE',
    });
  }

  async toggleApiKey(keyId: number): Promise<void> {
    return this.request(`/api/v1/admin/api-keys/${keyId}/toggle`, {
      method: 'PATCH',
    });
  }
}

export const apiClient = new APIClient();
