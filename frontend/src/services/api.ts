import axios, { AxiosError } from 'axios';
import {
  LoginResponse,
  ProfileData,
  ProfileUpdatePayload,
  RegisterRequestPayload,
  RegisterResponse,
  ResumeParseResponse,
  SendOTPResponse,
  StudentDashboardData,
  TOTPSetupResponse,
  VerificationStatusResponse,
} from '../types/onboarding';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const TOKEN_STORAGE_KEY = 'edtech_jwt_token';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (typeof FormData !== 'undefined' && config.data instanceof FormData && config.headers) {
    delete config.headers['Content-Type'];
  }
  return config;
});

export function setStoredAccessToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export function getStoredAccessToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function extractApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<{
      message?: string;
      detail?: string;
      errors?: Array<{ field: string; message: string }>;
    }>;
    const data = axiosErr.response?.data;
    if (data && typeof data === 'object') {
      if (Array.isArray(data.errors) && data.errors.length > 0) {
        return data.errors.map((e) => e.message).join(' ');
      }
      if (typeof data.message === 'string' && data.message.trim()) {
        return data.message;
      }
      if (typeof data.detail === 'string' && data.detail.trim()) {
        return data.detail;
      }
    }
    const status = axiosErr.response?.status;
    if (status === 500 || status === 502 || status === 503 || status === 504) {
      return (
        'Unable to reach the resume parsing backend service (HTTP ' +
        status +
        '). Please ensure the FastAPI backend server is running on http://127.0.0.1:8000 and try again.'
      );
    }
    if (!axiosErr.response && axiosErr.code === 'ERR_NETWORK') {
      return 'Network error: Unable to connect to the backend API server (http://127.0.0.1:8000).';
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred. Please try again.';
}

export const onboardingApi = {
  async parseResume(
    file: File,
    onUploadProgress?: (percent: number) => void
  ): Promise<ResumeParseResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<ResumeParseResponse>('/resume/parse', formData, {
      onUploadProgress: (progressEvent) => {
        if (onUploadProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onUploadProgress(percent);
        }
      },
    });
    return response.data;
  },

  async associateResume(resumeId: string): Promise<ResumeParseResponse> {
    const response = await apiClient.post<ResumeParseResponse>(`/resume/${resumeId}/associate`);
    return response.data;
  },

  getResumeFileUrl(resumeId: string, download = false): string {
    return `${API_BASE_URL}/resume/${resumeId}/file${download ? '?download=true' : ''}`;
  },

  async registerCandidate(payload: RegisterRequestPayload): Promise<RegisterResponse> {
    const response = await apiClient.post<RegisterResponse>('/auth/register', payload);
    return response.data;
  },

  async sendOTP(params: {
    user_id?: string;
    email?: string;
    channel: 'email' | 'whatsapp';
  }): Promise<SendOTPResponse> {
    const response = await apiClient.post<SendOTPResponse>('/auth/send-otp', params);
    return response.data;
  },

  async verify2FA(params: {
    user_id?: string;
    email?: string;
    channel: 'email' | 'whatsapp';
    otp: string;
  }): Promise<VerificationStatusResponse> {
    const response = await apiClient.post<VerificationStatusResponse>('/auth/verify-2fa', params);
    if (response.data.access_token) {
      setStoredAccessToken(response.data.access_token);
    }
    return response.data;
  },

  async setupTOTP(params: { user_id?: string; email?: string }): Promise<TOTPSetupResponse> {
    const response = await apiClient.post<TOTPSetupResponse | string>('/auth/totp/setup', params);
    const raw =
      typeof response.data === 'string'
        ? (JSON.parse(response.data) as Partial<TOTPSetupResponse>)
        : response.data;
    return {
      success: Boolean(raw?.success),
      qr_code_data_url: typeof raw?.qr_code_data_url === 'string' ? raw.qr_code_data_url : '',
      is_totp_enabled: Boolean(raw?.is_totp_enabled),
    };
  },

  async verifyTOTP(params: {
    user_id?: string;
    email?: string;
    otp: string;
  }): Promise<VerificationStatusResponse> {
    const response = await apiClient.post<VerificationStatusResponse>('/auth/totp/verify', params);
    if (response.data.access_token) {
      setStoredAccessToken(response.data.access_token);
    }
    return response.data;
  },

  async getVerificationStatus(userId: string): Promise<{
    success: boolean;
    user_id: string;
    email: string;
    phone: string;
    full_name: string;
    is_active: boolean;
    is_email_verified: boolean;
    is_whatsapp_verified: boolean;
    is_totp_enabled: boolean;
    required_channels: string[];
  }> {
    const response = await apiClient.get(`/auth/status/${userId}`);
    return response.data;
  },

  async login(
    email: string,
    password: string,
    resumeId?: string | null
  ): Promise<LoginResponse> {
    const payload: { email: string; password: string; resume_id?: string } = {
      email,
      password,
    };
    if (resumeId) {
      payload.resume_id = resumeId;
    }
    const response = await apiClient.post<LoginResponse>('/auth/login', payload);
    if (response.data.access_token) {
      setStoredAccessToken(response.data.access_token);
    }
    return response.data;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      setStoredAccessToken(null);
    }
  },

  async getProfile(): Promise<ProfileData> {
    const response = await apiClient.get<ProfileData>('/profile');
    return response.data;
  },

  async updateProfile(payload: ProfileUpdatePayload): Promise<ProfileData> {
    const response = await apiClient.patch<ProfileData>('/profile', payload);
    return response.data;
  },

  async getStudentDashboard(): Promise<StudentDashboardData> {
    const response = await apiClient.get<StudentDashboardData>('/dashboard/student');
    return response.data;
  },
};
