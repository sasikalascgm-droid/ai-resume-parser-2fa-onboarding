import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  GraduationCap,
  LayoutDashboard,
  LogIn,
  LogOut,
  ShieldCheck,
  Sparkles,
  UserCheck,
} from 'lucide-react';
import { useOnboarding } from '../context/OnboardingContext';

export const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { accessToken, currentUserProfile, logoutSession } = useOnboarding();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logoutSession();
    navigate('/');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-slate-200/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center text-white shadow-sm shadow-blue-600/25 group-hover:scale-105 transition-transform">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-lg tracking-tight text-slate-900">
                  SkillVerse
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  EdTech
                </span>
              </div>
              <p className="text-[11px] text-slate-500 hidden sm:block">
                AI Resume Parser &amp; Multi-Channel 2FA Onboarding
              </p>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
            <Link
              to="/"
              className={`hover:text-blue-600 transition-colors ${
                location.pathname === '/' ? 'text-blue-600 font-semibold' : ''
              }`}
            >
              Home
            </Link>
            <Link
              to="/upload-resume"
              className={`hover:text-blue-600 transition-colors ${
                location.pathname === '/upload-resume' ? 'text-blue-600 font-semibold' : ''
              }`}
            >
              Resume Parser
            </Link>
            <Link
              to="/register"
              className={`hover:text-blue-600 transition-colors ${
                location.pathname === '/register' ? 'text-blue-600 font-semibold' : ''
              }`}
            >
              Registration
            </Link>
            <Link
              to="/verify-2fa"
              className={`hover:text-blue-600 transition-colors ${
                location.pathname === '/verify-2fa' ? 'text-blue-600 font-semibold' : ''
              }`}
            >
              2FA Security
            </Link>
          </nav>

          <div className="flex items-center gap-3">
            {accessToken || currentUserProfile ? (
              <>
                <Link
                  to="/profile-preview"
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
                >
                  <UserCheck className="w-4 h-4 text-blue-600" />
                  <span className="hidden sm:inline">Profile</span>
                </Link>
                <Link
                  to="/dashboard/student"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-sm shadow-blue-600/20 transition-all"
                >
                  <LayoutDashboard className="w-4 h-4" />
                  <span>Student Dashboard</span>
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium text-slate-600 hover:text-red-600 hover:bg-red-50 transition-colors"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
                >
                  <LogIn className="w-4 h-4 text-slate-500" />
                  <span>Login</span>
                </Link>
                <Link
                  to="/upload-resume"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-sm shadow-blue-600/25 transition-all"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Register</span>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">{children}</main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200/80 py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            <span className="font-semibold text-slate-700">SkillVerse EdTech</span>
            <span>— Enterprise AI Resume Onboarding &amp; Multi-Channel 2FA Pipeline</span>
          </div>
          <div className="flex items-center gap-6 text-xs">
            <span>Argon2id Password Security</span>
            <span>•</span>
            <span>Email + WhatsApp + TOTP 2FA</span>
            <span>•</span>
            <span>JWT Protected</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
