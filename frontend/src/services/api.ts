/**
 * API клиент для взаимодействия с backend
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
}

export const apiClient = new APIClient();
