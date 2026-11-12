import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Loader2,
  Mail,
  MessageSquare,
  QrCode,
  RefreshCw,
  ShieldCheck,
  Smartphone,
} from 'lucide-react';
import { StepProgress } from '../components/StepProgress';
import { useOnboarding } from '../context/OnboardingContext';
import { useCountdown } from '../hooks/useCountdown';
import { extractApiErrorMessage, onboardingApi } from '../services/onboardingApi';

export const MultiChannel2FAPage: React.FC = () => {
  const navigate = useNavigate();
  const { stagedUser, setStagedUser, setAuthenticatedToken, refreshProfile } = useOnboarding();

  // Channel 1: Email OTP state
  const [emailOtp, setEmailOtp] = useState('');
  const [emailSending, setEmailSending] = useState(false);
  const [emailVerifying, setEmailVerifying] = useState(false);
  const [emailStatusMsg, setEmailStatusMsg] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [emailDeliveryMode, setEmailDeliveryMode] = useState<string | null>(null);
  const [emailDevOtp, setEmailDevOtp] = useState<string | null>(null);
  const emailTimer = useCountdown(0);

  // Channel 2: WhatsApp OTP state
  const [waOtp, setWaOtp] = useState('');
  const [waSending, setWaSending] = useState(false);
  const [waVerifying, setWaVerifying] = useState(false);
  const [waStatusMsg, setWaStatusMsg] = useState<string | null>(null);
  const [waError, setWaError] = useState<string | null>(null);
  const [waDeliveryMode, setWaDeliveryMode] = useState<string | null>(null);
  const [waDevOtp, setWaDevOtp] = useState<string | null>(null);
  const waTimer = useCountdown(0);

  // Channel 3: Browser TOTP state
  const [totpQrDataUrl, setTotpQrDataUrl] = useState<string | null>(null);
  const [totpCode, setTotpCode] = useState('');
  const [totpLoadingSetup, setTotpLoadingSetup] = useState(false);
  const [totpVerifying, setTotpVerifying] = useState(false);
  const [totpStatusMsg, setTotpStatusMsg] = useState<string | null>(null);
  const [totpSuccessMsg, setTotpSuccessMsg] = useState<string | null>(null);
  const [totpError, setTotpError] = useState<string | null>(null);

  // Refresh or recover verification status on mount
  useEffect(() => {
    const targetId = stagedUser?.userId || 'latest';
    onboardingApi
      .getVerificationStatus(targetId)
      .then((statusData) => {
        setStagedUser({
          userId: statusData.user_id,
          email: statusData.email,
          phone: statusData.phone,
          fullName: statusData.full_name,
          isActive: statusData.is_active,
          isEmailVerified: statusData.is_email_verified,
          isWhatsappVerified: statusData.is_whatsapp_verified,
          isTotpEnabled: statusData.is_totp_enabled,
          requiredChannels: statusData.required_channels,
        });
      })
      .catch(() => {
        // Keep existing staged state if network fails or no candidate is registered yet
      });
  }, [stagedUser?.userId, setStagedUser]);

  const activeUser = stagedUser || {
    userId: '',
    email: 'Not loaded yet',
    phone: 'Not loaded yet',
    fullName: '',
    isActive: false,
    isEmailVerified: false,
    isWhatsappVerified: false,
    isTotpEnabled: false,
    requiredChannels: ['email', 'whatsapp', 'totp'],
  };

  const handleSendEmailOtp = async () => {
    setEmailError(null);
    setEmailStatusMsg(null);
    setEmailSending(true);
    try {
      const res = await onboardingApi.sendOTP({
        user_id: activeUser.userId || undefined,
        email: stagedUser?.email || undefined,
        channel: 'email',
      });
      setEmailDeliveryMode(res.delivery_mode);
      setEmailDevOtp(res.dev_otp_preview || null);
      setEmailStatusMsg(res.message);
      emailTimer.startCountdown(res.cooldown_seconds || 30);
    } catch (err) {
      setEmailError(extractApiErrorMessage(err));
    } finally {
      setEmailSending(false);
    }
  };

  const handleVerifyEmailOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError(null);
    setEmailVerifying(true);
    try {
      const res = await onboardingApi.verify2FA({
        user_id: activeUser.userId || undefined,
        email: stagedUser?.email || undefined,
        channel: 'email',
        otp: emailOtp.trim(),
      });
      setEmailStatusMsg(res.message);
      setEmailDevOtp(null);
      setStagedUser((prev) =>
        prev
          ? {
              ...prev,
              userId: res.user_id || prev.userId,
              isEmailVerified: res.is_email_verified,
              isWhatsappVerified: res.is_whatsapp_verified,
              isTotpEnabled: res.is_totp_enabled,
              isActive: res.is_active,
            }
          : null
      );
      if (res.access_token) {
        setAuthenticatedToken(res.access_token);
        await refreshProfile();
      }
    } catch (err) {
      setEmailError(extractApiErrorMessage(err));
    } finally {
      setEmailVerifying(false);
    }
  };

  const handleSendWhatsappOtp = async () => {
    setWaError(null);
    setWaStatusMsg(null);
    setWaSending(true);
    try {
      const res = await onboardingApi.sendOTP({
        user_id: activeUser.userId || undefined,
        email: stagedUser?.email || undefined,
        channel: 'whatsapp',
      });
      setWaDeliveryMode(res.delivery_mode);
      setWaDevOtp(res.dev_otp_preview || null);
      setWaStatusMsg(res.message);
      waTimer.startCountdown(res.cooldown_seconds || 30);
    } catch (err) {
      setWaError(extractApiErrorMessage(err));
    } finally {
      setWaSending(false);
    }
  };

  const handleVerifyWhatsappOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setWaError(null);
    setWaVerifying(true);
    try {
      const res = await onboardingApi.verify2FA({
        user_id: activeUser.userId || undefined,
        email: stagedUser?.email || undefined,
        channel: 'whatsapp',
        otp: waOtp.trim(),
      });
      setWaStatusMsg(res.message);
      setWaDevOtp(null);
      setStagedUser((prev) =>
        prev
          ? {
              ...prev,
              userId: res.user_id || prev.userId,
              isEmailVerified: res.is_email_verified,
              isWhatsappVerified: res.is_whatsapp_verified,
              isTotpEnabled: res.is_totp_enabled,
              isActive: res.is_active,
            }
          : null
      );
      if (res.access_token) {
        setAuthenticatedToken(res.access_token);
        await refreshProfile();
      }
    } catch (err) {
      setWaError(extractApiErrorMessage(err));
    } finally {
      setWaVerifying(false);
    }
  };

  const handleSetupTotp = async () => {
    setTotpError(null);
    setTotpStatusMsg(null);
    setTotpSuccessMsg(null);
    setTotpQrDataUrl(null);
    setTotpLoadingSetup(true);
    try {
      const res = await onboardingApi.setupTOTP({
        user_id: activeUser.userId || undefined,
        email: stagedUser?.email || undefined,
      });
      const qrCodeDataUrl =
        typeof res?.qr_code_data_url === 'string' ? res.qr_code_data_url.trim() : '';
      const isValidPngDataUrl =
        /^data:image\/png;base64,[A-Za-z0-9+/=]+$/i.test(qrCodeDataUrl) &&
        qrCodeDataUrl.length > 64;

      if (!qrCodeDataUrl || !isValidPngDataUrl) {
        setTotpError(
          'Unable to display TOTP QR code: the QR code image data is missing or invalid. Please regenerate the QR code.'
        );
        return;
      }

      setTotpQrDataUrl(qrCodeDataUrl);
      setTotpCode('');
      setStagedUser((prev) => (prev ? { ...prev, isTotpEnabled: false } : prev));
      setTotpStatusMsg(
        'Scan the QR code below with Google Authenticator, Authy, or Microsoft Authenticator, then enter the 6-digit code.'
      );
    } catch (err) {
      setTotpQrDataUrl(null);
      setTotpError(extractApiErrorMessage(err));
    } finally {
      setTotpLoadingSetup(false);
    }
  };

  const handleVerifyTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpError(null);
    setTotpStatusMsg(null);
    setTotpSuccessMsg(null);
    setTotpVerifying(true);
    try {
      const res = await onboardingApi.verifyTOTP({
        user_id: activeUser.userId || undefined,
        email: stagedUser?.email || undefined,
        otp: totpCode.trim(),
      });
      setTotpQrDataUrl(null);
      setTotpCode('');
      setTotpSuccessMsg(
        res.message || 'TOTP verified successfully! Browser Authenticator 2FA is now enabled.'
      );
      setStagedUser((prev) =>
        prev
          ? {
              ...prev,
              userId: res.user_id || prev.userId,
              isEmailVerified: res.is_email_verified,
              isWhatsappVerified: res.is_whatsapp_verified,
              isTotpEnabled: res.is_totp_enabled,
              isActive: res.is_active,
            }
          : null
      );
      if (res.access_token) {
        setAuthenticatedToken(res.access_token);
        await refreshProfile();
      }
    } catch (err) {
      setTotpError(extractApiErrorMessage(err));
    } finally {
      setTotpVerifying(false);
    }
  };

  const verifiedCount = [
    activeUser.isEmailVerified,
    activeUser.isWhatsappVerified,
    activeUser.isTotpEnabled,
  ].filter(Boolean).length;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <StepProgress currentStep={3} />

      {/* Header & Verification Status Summary */}
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-8 mb-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-600 mb-1">
              <ShieldCheck className="w-4 h-4" />
              <span>Multi-Channel Two-Factor Authentication</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900">
              Verify Your Identity Across 3 Security Channels
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Your account is currently in a <span className="font-semibold">staged inactive state</span>.
              Complete Email OTP, WhatsApp OTP, and Browser TOTP verification to activate your account.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-center">
              <p className="text-xs font-semibold text-slate-500">Channels Verified</p>
              <p className="text-2xl font-extrabold text-blue-600">{verifiedCount} / 3</p>
            </div>
            <div
              className={`px-4 py-3 rounded-2xl border text-center ${
                activeUser.isActive
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : 'bg-amber-50 border-amber-200 text-amber-800'
              }`}
            >
              <p className="text-xs font-semibold">Account Status</p>
              <p className="text-sm font-bold mt-1">
                {activeUser.isActive ? 'ACTIVE & JWT ISSUED' : 'STAGED (INACTIVE)'}
              </p>
            </div>
          </div>
        </div>

        {!stagedUser && (
          <div className="mt-4 p-3.5 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-600">
            <span>
              No active registration session found in browser storage. You can still set up or test
              2FA below, or register/sign in.
            </span>
            <div className="flex gap-2 shrink-0">
              <Link
                to="/upload-resume"
                className="px-3.5 py-1.5 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700"
              >
                Register
              </Link>
              <Link
                to="/login"
                className="px-3.5 py-1.5 rounded-lg bg-white border border-slate-300 text-slate-700 font-semibold hover:bg-slate-50"
              >
                Login
              </Link>
            </div>
          </div>
        )}

        {/* Account Activated Callout */}
        {activeUser.isActive && (
          <div className="mt-6 p-5 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg shadow-emerald-600/20">
            <div className="flex items-center gap-3.5">
              <CheckCircle2 className="w-8 h-8 shrink-0" />
              <div>
                <h3 className="text-base font-bold">
                  All 2FA Channels Verified &amp; Account Activated!
                </h3>
                <p className="text-xs sm:text-sm text-emerald-50">
                  Your JWT session is now active. Review your candidate profile before entering the
                  Student Dashboard.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate('/profile-preview')}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-white text-emerald-900 font-bold text-sm hover:bg-emerald-50 transition-colors shrink-0"
            >
              <span>Continue to Profile Preview</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Three Independent Verification Channels Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 1. EMAIL OTP CARD */}
        <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                  <Mail className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900">1. Email OTP</h2>
                  <p className="text-xs text-slate-500">SMTP Verification Channel</p>
                </div>
              </div>
              {activeUser.isEmailVerified ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Verified
                </span>
              ) : (
                <span className="px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-xs font-semibold">
                  Pending
                </span>
              )}
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Registered Email Address
              </span>
              <p className="text-sm font-semibold text-slate-900 truncate mt-0.5">
                {activeUser.email}
              </p>
            </div>

            {emailDeliveryMode && (
              <div className="flex items-center justify-between text-xs px-3 py-2 rounded-lg bg-slate-100 text-slate-700">
                <span className="font-medium">Delivery Mode:</span>
                <span className="font-bold uppercase text-blue-700">
                  {emailDeliveryMode === 'smtp' ? 'Live SMTP' : 'Simulated Mock Mode'}
                </span>
              </div>
            )}

            {emailDevOtp && !activeUser.isEmailVerified && (
              <div className="p-3 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-950 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold uppercase tracking-wider text-indigo-700">
                    Dev Mode Simulated Email OTP
                  </span>
                  <button
                    type="button"
                    onClick={() => setEmailOtp(emailDevOtp)}
                    className="text-[11px] font-semibold text-indigo-600 underline hover:text-indigo-800"
                  >
                    Auto-fill OTP
                  </button>
                </div>
                <p className="font-mono text-lg font-extrabold tracking-widest text-indigo-900">
                  {emailDevOtp}
                </p>
              </div>
            )}

            {emailError && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span>{emailError}</span>
              </div>
            )}

            {emailStatusMsg && (
              <div className="p-3 rounded-xl bg-blue-50/80 border border-blue-200 text-xs text-blue-800">
                {emailStatusMsg}
              </div>
            )}
          </div>

          {!activeUser.isEmailVerified ? (
            <div className="mt-6 pt-4 border-t border-slate-100 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={handleSendEmailOtp}
                  disabled={emailSending || emailTimer.isActive}
                  className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 disabled:opacity-50 transition-all"
                >
                  {emailSending ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Sending Email OTP...</span>
                    </>
                  ) : emailTimer.isActive ? (
                    <>
                      <Clock className="w-3.5 h-3.5" />
                      <span>Resend in {emailTimer.secondsLeft}s</span>
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Send / Resend Email OTP</span>
                    </>
                  )}
                </button>
              </div>

              <form onSubmit={handleVerifyEmailOtp} className="flex gap-2">
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={emailOtp}
                  onChange={(e) => setEmailOtp(e.target.value.replace(/\D/g, ''))}
                  placeholder="6-digit OTP"
                  className="flex-1 px-3.5 py-2.5 rounded-xl border border-slate-300 text-center font-mono text-sm font-bold tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
                <button
                  type="submit"
                  disabled={emailVerifying || emailOtp.length !== 6}
                  className="px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {emailVerifying ? 'Verifying...' : 'Verify'}
                </button>
              </form>
            </div>
          ) : (
            <div className="mt-6 pt-4 border-t border-slate-100 flex items-center gap-2 text-emerald-700 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Email channel verified &amp; locked.</span>
            </div>
          )}
        </div>

        {/* 2. WHATSAPP OTP CARD */}
        <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <MessageSquare className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900">2. WhatsApp OTP</h2>
                  <p className="text-xs text-slate-500">WhatsApp Business Cloud API</p>
                </div>
              </div>
              {activeUser.isWhatsappVerified ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Verified
                </span>
              ) : (
                <span className="px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-xs font-semibold">
                  Pending
                </span>
              )}
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Registered WhatsApp Phone
              </span>
              <p className="text-sm font-semibold text-slate-900 mt-0.5">{activeUser.phone}</p>
            </div>

            {waDeliveryMode && (
              <div className="flex items-center justify-between text-xs px-3 py-2 rounded-lg bg-slate-100 text-slate-700">
                <span className="font-medium">Delivery Adapter:</span>
                <span className="font-bold uppercase text-emerald-700">
                  {waDeliveryMode === 'cloud'
                    ? 'Meta Cloud API'
                    : 'Simulated Mock Adapter'}
                </span>
              </div>
            )}

            {waDevOtp && !activeUser.isWhatsappVerified && (
              <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-950 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold uppercase tracking-wider text-emerald-700">
                    Dev Mode Simulated WhatsApp OTP
                  </span>
                  <button
                    type="button"
                    onClick={() => setWaOtp(waDevOtp)}
                    className="text-[11px] font-semibold text-emerald-700 underline hover:text-emerald-900"
                  >
                    Auto-fill OTP
                  </button>
                </div>
                <p className="font-mono text-lg font-extrabold tracking-widest text-emerald-900">
                  {waDevOtp}
                </p>
              </div>
            )}

            {waError && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span>{waError}</span>
              </div>
            )}

            {waStatusMsg && (
              <div className="p-3 rounded-xl bg-blue-50/80 border border-blue-200 text-xs text-blue-800">
                {waStatusMsg}
              </div>
            )}
          </div>

          {!activeUser.isWhatsappVerified ? (
            <div className="mt-6 pt-4 border-t border-slate-100 space-y-3">
              <button
                type="button"
                onClick={handleSendWhatsappOtp}
                disabled={waSending || waTimer.isActive}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 disabled:opacity-50 transition-all"
              >
                {waSending ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Sending WhatsApp OTP...</span>
                  </>
                ) : waTimer.isActive ? (
                  <>
                    <Clock className="w-3.5 h-3.5" />
                    <span>Resend in {waTimer.secondsLeft}s</span>
                  </>
                ) : (
                  <>
                    <Smartphone className="w-3.5 h-3.5" />
                    <span>Send / Resend WhatsApp OTP</span>
                  </>
                )}
              </button>

              <form onSubmit={handleVerifyWhatsappOtp} className="flex gap-2">
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={waOtp}
                  onChange={(e) => setWaOtp(e.target.value.replace(/\D/g, ''))}
                  placeholder="6-digit OTP"
                  className="flex-1 px-3.5 py-2.5 rounded-xl border border-slate-300 text-center font-mono text-sm font-bold tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
                <button
                  type="submit"
                  disabled={waVerifying || waOtp.length !== 6}
                  className="px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {waVerifying ? 'Verifying...' : 'Verify'}
                </button>
              </form>
            </div>
          ) : (
            <div className="mt-6 pt-4 border-t border-slate-100 flex items-center gap-2 text-emerald-700 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>WhatsApp channel verified &amp; locked.</span>
            </div>
          )}
        </div>

        {/* 3. BROWSER / AUTHENTICATOR TOTP CARD */}
        <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <QrCode className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900">3. Browser TOTP</h2>
                  <p className="text-xs text-slate-500">Time-Based Authenticator App</p>
                </div>
              </div>
              {activeUser.isTotpEnabled ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Enrolled
                </span>
              ) : (
                <span className="px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-xs font-semibold">
                  Not Enrolled
                </span>
              )}
            </div>

            {!totpQrDataUrl && !totpLoadingSetup && !activeUser.isTotpEnabled && (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70 text-xs text-slate-600 space-y-2">
                <p className="font-semibold text-slate-800">
                  Enroll an Authenticator Application
                </p>
                <p>
                  Generate a fresh, encrypted TOTP QR code and scan it using Google Authenticator,
                  Authy, or Microsoft Authenticator.
                </p>
              </div>
            )}

            {totpLoadingSetup && (
              <div
                role="status"
                aria-live="polite"
                className="p-6 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col items-center justify-center text-center space-y-2"
              >
                <Loader2 className="w-7 h-7 animate-spin text-indigo-600" />
                <p className="text-xs font-semibold text-slate-700">
                  Generating TOTP QR code...
                </p>
              </div>
            )}

            {totpQrDataUrl && !totpLoadingSetup && (
              <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center">
                <img
                  src={totpQrDataUrl}
                  alt="Authenticator QR Code"
                  className="w-56 h-56 aspect-square object-contain select-none"
                  onError={() => {
                    setTotpQrDataUrl(null);
                    setTotpError(
                      'Unable to render the TOTP QR code image. Please regenerate the QR code and try again.'
                    );
                  }}
                />
                <span className="text-xs font-medium text-slate-600 mt-2 text-center">
                  Scan with Google Authenticator or any TOTP app
                </span>
              </div>
            )}

            {totpError && (
              <div
                role="alert"
                className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2"
              >
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span>{totpError}</span>
              </div>
            )}

            {totpStatusMsg && !activeUser.isTotpEnabled && (
              <div className="p-3 rounded-xl bg-blue-50/80 border border-blue-200 text-xs text-blue-800">
                {totpStatusMsg}
              </div>
            )}

            {(totpSuccessMsg || activeUser.isTotpEnabled) && (
              <div
                role="status"
                className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-start gap-2 font-medium"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>
                  {totpSuccessMsg ||
                    'TOTP verified successfully! Browser Authenticator 2FA is active.'}
                </span>
              </div>
            )}
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 space-y-3">
            <button
              type="button"
              onClick={handleSetupTotp}
              disabled={totpLoadingSetup}
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 disabled:opacity-50 transition-all"
            >
              {totpLoadingSetup ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Generating QR Code...</span>
                </>
              ) : (
                <>
                  <QrCode className="w-3.5 h-3.5" />
                  <span>
                    {totpQrDataUrl ? 'Regenerate TOTP QR Code' : 'Set up Authenticator'}
                  </span>
                </>
              )}
            </button>

            {!activeUser.isTotpEnabled ? (
              <form onSubmit={handleVerifyTotp} className="flex gap-2">
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="\d{6}"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="6-digit TOTP"
                  aria-label="6-digit TOTP code"
                  className="flex-1 px-3.5 py-2.5 rounded-xl border border-slate-300 text-center font-mono text-sm font-bold tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
                <button
                  type="submit"
                  disabled={totpVerifying || totpCode.length !== 6}
                  className="px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {totpVerifying ? 'Verifying...' : 'Verify TOTP'}
                </button>
              </form>
            ) : (
              <div className="flex items-center gap-2 text-emerald-700 text-xs font-semibold pt-1">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Browser TOTP enrolled &amp; verified.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
