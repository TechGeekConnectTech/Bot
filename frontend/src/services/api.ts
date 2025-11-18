import axios, { AxiosInstance, AxiosResponse } from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: BASE_URL,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // Add auth interceptor
    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(username: string, password: string) {
    console.log('ApiService: Sending login request for username:', username);
    console.log('ApiService: Request URL:', `${BASE_URL}/api/auth/login`);
    
    try {
      const response = await this.api.post('/api/auth/login', {
        username,
        password
      });
      console.log('ApiService: Login response status:', response.status);
      console.log('ApiService: Login response data:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('ApiService: Login request failed:', error);
      if (error.response) {
        console.error('ApiService: Error response status:', error.response.status);
        console.error('ApiService: Error response data:', error.response.data);
      }
      throw error;
    }
  }

  async register(userData: {
    username: string;
    email: string;
    password: string;
    full_name: string;
    department?: string;
  }) {
    const response = await this.api.post('/api/auth/register', userData);
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.api.get('/api/auth/me');
    return response.data;
  }

  // Chat
  async sendMessage(messageData: {
    message: string;
    conversation_id?: number;
    server_name?: string;
    correlation_id?: string;
    category?: string;
  }) {
    const response = await this.api.post('/api/chat/send-message', messageData);
    return response.data;
  }

  async getConversations() {
    const response = await this.api.get('/api/chat/conversations');
    return response.data;
  }

  async getConversationMessages(conversationId: number) {
    const response = await this.api.get(`/api/chat/conversation/${conversationId}/messages`);
    return response.data;
  }

  async deleteConversation(conversationId: number) {
    const response = await this.api.delete(`/api/chat/conversation/${conversationId}`);
    return response.data;
  }

  async deleteAllConversations() {
    const response = await this.api.delete('/api/chat/conversations/all');
    return response.data;
  }

  // Admin
  async getDashboardStats() {
    const response = await this.api.get('/api/admin/dashboard');
    return response.data;
  }

  async getUserStatistics() {
    const response = await this.api.get('/api/admin/users');
    return response.data;
  }

  // Get all incidents (admin only)
  async getIncidents() {
    const response = await this.api.get('/api/admin/incidents');
    return response.data;
  }

  // Get user's own incidents
  async getUserIncidents(filters?: {
    server_name?: string;
    query_type?: string;
    incident_status?: string;
    page?: number;
    limit?: number;
  }) {
    try {
      // First try to get user's own incidents
      const params = new URLSearchParams();
      if (filters?.server_name) params.append('server_name', filters.server_name);
      if (filters?.query_type) params.append('query_type', filters.query_type);
      if (filters?.incident_status) params.append('incident_status', filters.incident_status);
      if (filters?.limit) params.append('limit', filters.limit.toString());
      if (filters?.page) {
        const offset = ((filters.page - 1) * (filters.limit || 50));
        params.append('offset', offset.toString());
      }
      
      const response = await this.api.get(`/api/incidents?${params.toString()}`);
      return {
        incidents: response.data.incidents || [],
        total_pages: Math.ceil((response.data.total_count || 0) / (filters?.limit || 50)),
        total_incidents: response.data.total_count || 0,
        filtered_incidents: response.data.filtered_count || 0
      };
    } catch (error: any) {
      console.error('Error fetching user incidents:', error);
      if (error.response?.status === 403) {
        // If user doesn't have access to own incidents, try admin endpoint
        return this.getAdminIncidents(filters);
      }
      throw error;
    }
  }

  // Get all incidents (admin access required)
  async getAdminIncidents(filters?: {
    server_name?: string;
    query_type?: string;
    incident_status?: string;
    page?: number;
    limit?: number;
  }) {
    try {
      const params = new URLSearchParams();
      if (filters?.server_name) params.append('server_name', filters.server_name);
      if (filters?.query_type) params.append('query_type', filters.query_type);
      if (filters?.incident_status) params.append('incident_status', filters.incident_status);
      if (filters?.limit) params.append('limit', filters.limit.toString());
      if (filters?.page) {
        const offset = ((filters.page - 1) * (filters.limit || 50));
        params.append('offset', offset.toString());
      }
      
      const response = await this.api.get(`/api/admin/incidents?${params.toString()}`);
      return {
        incidents: response.data.incidents || [],
        total_pages: Math.ceil((response.data.total_count || 0) / (filters?.limit || 50)),
        total_incidents: response.data.total_count || 0,
        filtered_incidents: response.data.filtered_count || 0
      };
    } catch (error: any) {
      console.error('Error fetching admin incidents:', error);
      if (error.response?.status === 403) {
        throw new Error('Admin access required to view all incidents');
      }
      throw error;
    }
  }

  async getIncidentDetails(incidentId: string) {
    try {
      // First try user incident endpoint
      const response = await this.api.get(`/api/incidents/${incidentId}`);
      return response.data;
    } catch (error: any) {
      // If user access fails, try admin endpoint
      if (error.response?.status === 404 || error.response?.status === 403) {
        try {
          const response = await this.api.get(`/api/admin/incidents/${incidentId}`);
          return response.data;
        } catch (adminError: any) {
          console.error('Error fetching incident details (admin):', adminError);
          throw new Error('Incident not found or access denied');
        }
      }
      console.error('Error fetching incident details:', error);
      throw error;
    }
  }

  async deleteUserConversations(userId: number) {
    const response = await this.api.delete(`/api/admin/conversations/user/${userId}`);
    return response.data;
  }

  async deleteAllConversationsAdmin() {
    const response = await this.api.delete('/api/admin/conversations/all');
    return response.data;
  }

  async getConversationStats() {
    const response = await this.api.get('/api/admin/conversations/stats');
    return response.data;
  }

  async createIncident(conversationId: number, incidentDetails: {
    server_name?: string;
    correlation_id?: string; 
    job_id?: string;
    affected_username?: string;
    issue_description: string;
    priority?: string;
    category?: string;
    user_id?: number;
  }) {
    const response = await this.api.post('/api/admin/create-incident', {
      conversation_id: conversationId,
      incident_details: incidentDetails
    });
    return response.data;
  }

  // Health check
  async healthCheck() {
    const response = await this.api.get('/health');
    return response.data;
  }
}

export const apiService = new ApiService();
export default ApiService;