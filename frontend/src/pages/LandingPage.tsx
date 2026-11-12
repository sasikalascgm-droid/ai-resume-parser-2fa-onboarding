import React from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Award,
  CheckCircle2,
  FileSearch,
  Lock,
  Mail,
  MessageSquare,
  QrCode,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  UserCheck,
  Zap,
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  return (
    <div className="space-y-20">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-blue-50/70 via-white to-slate-50 pt-14 pb-20 border-b border-slate-200/70">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-100/80 text-blue-800 text-xs font-semibold border border-blue-200">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                <span>Next-Gen EdTech Candidate Onboarding</span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 leading-[1.12]">
                Smart AI Resume Parsing &amp;{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
                  Multi-Channel 2FA
                </span>{' '}
                Onboarding
              </h1>

              <p className="text-lg text-slate-600 max-w-2xl leading-relaxed">
                Upload your PDF or DOCX resume to automatically extract your skills, academic
                qualifications, and work experience. Verify your identity across Email, WhatsApp,
                and Authenticator TOTP to unlock your personalized SkillVerse Student Dashboard.
              </p>

              <div className="flex flex-wrap items-center gap-4 pt-2">
                <Link
                  to="/upload-resume"
                  className="inline-flex items-center gap-2.5 px-7 py-3.5 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 shadow-lg shadow-blue-600/25 transition-all"
                >
                  <UploadCloud className="w-5 h-5" />
                  <span>Register with Resume</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl bg-white text-slate-700 font-semibold border border-slate-300 hover:bg-slate-50 transition-all"
                >
                  <Lock className="w-4 h-4 text-slate-500" />
                  <span>Student Login</span>
                </Link>
              </div>

              <div className="pt-4 grid grid-cols-3 gap-4 max-w-lg border-t border-slate-200/80">
                <div>
                  <p className="text-xl font-bold text-slate-900">PDF &amp; DOCX</p>
                  <p className="text-xs text-slate-500">Instant Extraction</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-slate-900">Argon2id</p>
                  <p className="text-xs text-slate-500">Zero-Plaintext Security</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-slate-900">3-Factor 2FA</p>
                  <p className="text-xs text-slate-500">Email + WhatsApp + TOTP</p>
                </div>
              </div>
            </div>

            {/* Interactive Pipeline Preview Card */}
            <div className="lg:col-span-5">
              <div className="bg-white rounded-3xl border border-slate-200/90 shadow-xl shadow-slate-900/5 p-6 sm:p-8 space-y-6">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-blue-600">
                      Live Security Pipeline
                    </span>
                    <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                      Candidate Verification Architecture
                    </h3>
                  </div>
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-start gap-3.5 p-3.5 rounded-2xl bg-slate-50 border border-slate-200/60">
                    <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                      <FileSearch className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        1. Intelligent Resume Parsing
                      </p>
                      <p className="text-xs text-slate-600 mt-0.5">
                        Extracts Name, Email, Phone, Skills, Experience &amp; Qualification without
                        fabricating missing fields.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3.5 p-3.5 rounded-2xl bg-slate-50 border border-slate-200/60">
                    <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                      <Lock className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        2. Staged Argon2id Account Creation
                      </p>
                      <p className="text-xs text-slate-600 mt-0.5">
                        Creates an inactive PostgreSQL record with Argon2id hashed credentials until
                        all 2FA challenges pass.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3.5 p-3.5 rounded-2xl bg-slate-50 border border-slate-200/60">
                    <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        3. Tri-Channel 2FA &amp; JWT Issuance
                      </p>
                      <p className="text-xs text-slate-600 mt-0.5">
                        Verifies SMTP Email OTP, WhatsApp Cloud OTP, and encrypted Browser TOTP
                        before activating your Student Dashboard.
                      </p>
                    </div>
                  </div>
                </div>

                <Link
                  to="/upload-resume"
                  className="w-full inline-flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800 transition-colors"
                >
                  <span>Start Candidate Onboarding</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Platform Features Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <span className="text-xs font-bold uppercase tracking-widest text-blue-600">
            Enterprise Platform Features
          </span>
          <h2 className="text-3xl font-bold text-slate-900 mt-2">
            Engineered for Security, Accuracy &amp; Speed
          </h2>
          <p className="text-slate-600 mt-2 text-sm sm:text-base">
            Every layer of the onboarding pipeline is designed to eliminate manual form entry while
            enforcing banking-grade multi-factor verification.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
              <Zap className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Automated Resume Extraction</h3>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              Supports PDF and DOCX files with magic-byte validation, scanned-PDF detection, and
              structured JSON extraction for instant registration form auto-fill.
            </p>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-11 h-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
              <Mail className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Email &amp; WhatsApp OTPs</h3>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              Cryptographically random 6-digit OTPs hashed with HMAC-SHA256 at rest, protected by
              expiration windows, resend cooldowns, and brute-force attempt caps.
            </p>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
              <QrCode className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Encrypted Authenticator TOTP</h3>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              Instant QR provisioning for Google Authenticator, Authy, or Microsoft Authenticator
              with Fernet symmetric encryption for TOTP secrets at rest.
            </p>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-3xl border border-slate-200/90 p-8 sm:p-12 shadow-sm">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <span className="text-xs font-bold uppercase tracking-widest text-blue-600">
              End-to-End Onboarding Workflow
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-2">
              How SkillVerse Onboarding Works
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/70">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-blue-600 text-white">
                  Step 1
                </span>
                <UploadCloud className="w-5 h-5 text-blue-600" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm">Upload Resume</h4>
              <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
                Drop your PDF or DOCX resume. Our parser extracts your contact details, technical
                skills, experience, and degree.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/70">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-blue-600 text-white">
                  Step 2
                </span>
                <UserCheck className="w-5 h-5 text-blue-600" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm">Review &amp; Register</h4>
              <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
                Review and edit the auto-populated registration fields and set a strong password
                hashed with Argon2id.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/70">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-blue-600 text-white">
                  Step 3
                </span>
                <MessageSquare className="w-5 h-5 text-blue-600" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm">Verify 3-Channel 2FA</h4>
              <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
                Complete Email OTP, WhatsApp OTP, and Browser Authenticator TOTP verification to
                activate your account.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/70">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-600 text-white">
                  Step 4
                </span>
                <Award className="w-5 h-5 text-emerald-600" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm">Student Dashboard</h4>
              <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
                Confirm your profile preview and access your JWT-protected Student Dashboard with
                verified credentials.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
