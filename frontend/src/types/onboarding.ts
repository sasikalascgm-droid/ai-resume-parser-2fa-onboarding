export interface ExtractedResumeData {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  skills: string[];
  experience: string | null;
  qualification: string | null;
}

export interface ResumeParseResponse {
  success: boolean;
  resume_id: string;
  original_filename: string;
  extracted_data: ExtractedResumeData;
  warnings: string[];
}

export interface RegisterRequestPayload {
  full_name: string;
  email: string;
  phone: string;
  skills: string[];
  experience?: string | null;
  qualification?: string | null;
  password: string;
  confirm_password: string;
  resume_id?: string | null;
}

export interface RegisterResponse {
  success: boolean;
  message: string;
  user_id: string;
  email: string;
  phone: string;
  is_active: boolean;
  required_2fa_channels: string[];
  verification_status: {
    email: boolean;
    whatsapp: boolean;
    totp: boolean;
  };
}

export interface SendOTPResponse {
  success: boolean;
  channel: 'email' | 'whatsapp';
  delivery_mode: string;
  delivered: boolean;
  message: string;
  expires_in_seconds: number;
  cooldown_seconds: number;
  recipient_masked: string;
  dev_otp_preview?: string | null;
}

export interface TOTPSetupResponse {
  success: boolean;
  qr_code_data_url: string;
  is_totp_enabled: boolean;
}

export interface VerificationStatusResponse {
  success: boolean;
  message: string;
  user_id: string;
  channel_verified: string;
  is_email_verified: boolean;
  is_whatsapp_verified: boolean;
  is_totp_enabled: boolean;
  is_active: boolean;
  required_channels: string[];
  access_token?: string | null;
  token_type?: string | null;
}

export interface ResumeMetadataSummary {
  id: string;
  original_filename: string;
  extracted_metadata: Record<string, unknown>;
  created_at: string;
}

export interface ProfileData {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  skills: string[];
  experience: string | null;
  qualification: string | null;
  is_active: boolean;
  is_email_verified: boolean;
  is_whatsapp_verified: boolean;
  is_totp_enabled: boolean;
  profile_completion: number;
  latest_resume: ResumeMetadataSummary | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdatePayload {
  full_name?: string;
  phone?: string;
  skills?: string[];
  experience?: string;
  qualification?: string;
}

export interface StudentDashboardData {
  user_id: string;
  full_name: string;
  email: string;
  phone: string;
  skills: string[];
  experience: string | null;
  qualification: string | null;
  is_active: boolean;
  verification_status: {
    email: boolean;
    whatsapp: boolean;
    totp: boolean;
    all_required_verified: boolean;
  };
  profile_completion_percentage: number;
  profile_completion_status: string;
  dashboard_route: string;
  latest_resume: ResumeMetadataSummary | null;
  created_at: string;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  user_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  requires_2fa_completion: boolean;
  verification_status: {
    email: boolean;
    whatsapp: boolean;
    totp: boolean;
  };
  required_channels: string[];
  access_token?: string | null;
  token_type?: string | null;
}
