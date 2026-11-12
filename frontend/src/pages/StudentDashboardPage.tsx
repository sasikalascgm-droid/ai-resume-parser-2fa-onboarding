import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  Award,
  BookOpen,
  Briefcase,
  CheckCircle2,
  Download,
  Edit3,
  FileText,
  GraduationCap,
  LayoutDashboard,
  Loader2,
  LogOut,
  Mail,
  MessageSquare,
  Phone,
  Plus,
  QrCode,
  Save,
  ShieldCheck,
  UploadCloud,
  User,
  Wrench,
  X,
} from 'lucide-react';
import { useOnboarding } from '../context/OnboardingContext';
import { extractApiErrorMessage, onboardingApi } from '../services/api';
import { StudentDashboardData } from '../types/onboarding';

export const StudentDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const resumeInputRef = useRef<HTMLInputElement | null>(null);
  const { logoutSession, refreshProfile, setParsedResumeState } = useOnboarding();

  const [dashboard, setDashboard] = useState<StudentDashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [uploadingResume, setUploadingResume] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'security' | 'edit'>('overview');
  const [showResumePreview, setShowResumePreview] = useState<boolean>(false);

  // Edit profile form state
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [experience, setExperience] = useState('');
  const [qualification, setQualification] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const loadDashboard = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      await refreshProfile();
      const data = await onboardingApi.getStudentDashboard();
      setDashboard(data);
      setFullName(data.full_name);
      setPhone(data.phone);
      setExperience(data.experience || '');
      setQualification(data.qualification || '');
      setSkills(data.skills || []);
    } catch (err) {
      setErrorMsg(extractApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const handleDashboardResumeUpload = async (file: File) => {
    setErrorMsg(null);
    setSaveSuccess(null);
    setUploadingResume(true);
    try {
      const parsed = await onboardingApi.parseResume(file);
      setParsedResumeState(parsed.resume_id, parsed.original_filename, parsed.extracted_data);
      await refreshProfile();
      await loadDashboard();
      setSaveSuccess(
        `Resume "${parsed.original_filename}" uploaded, linked to your account, and synchronized with your dashboard!`
      );
    } catch (err) {
      setErrorMsg(extractApiErrorMessage(err));
    } finally {
      setUploadingResume(false);
    }
  };

  const handleLogout = async () => {
    await logoutSession();
    navigate('/');
  };

  const handleAddSkill = () => {
    const trimmed = skillInput.trim();
    if (!trimmed) return;
    if (!skills.some((s) => s.toLowerCase() === trimmed.toLowerCase())) {
      setSkills([...skills, trimmed]);
    }
    setSkillInput('');
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(null);
    setErrorMsg(null);
    try {
      await onboardingApi.updateProfile({
        full_name: fullName,
        phone,
        skills,
        experience,
        qualification,
      });
      await refreshProfile();
      await loadDashboard();
      setSaveSuccess('Your student profile has been updated!');
      setActiveTab('overview');
    } catch (err) {
      setErrorMsg(extractApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-slate-600">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600 mb-3" />
        <p className="text-sm font-medium">Loading Student Dashboard...</p>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-red-600 mx-auto" />
        <h2 className="text-xl font-bold text-slate-900">Dashboard Access Restricted</h2>
        <p className="text-sm text-slate-600">
          {errorMsg || 'Only authenticated and 2FA-verified candidates can access the Student Dashboard.'}
        </p>
        <div className="flex justify-center gap-3 pt-2">
          <Link
            to="/login"
            className="px-5 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold"
          >
            Go to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Sidebar Navigation */}
        <aside className="lg:col-span-3 space-y-4">
          <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 space-y-6">
            <div className="flex items-center gap-3.5 pb-5 border-b border-slate-100">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center font-extrabold text-lg shrink-0">
                {dashboard.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-bold text-slate-900 truncate">{dashboard.full_name}</p>
                <p className="text-xs text-slate-500 truncate">{dashboard.email}</p>
                <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-bold border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3" />
                  Verified Student
                </span>
              </div>
            </div>

            <nav className="space-y-1.5">
              <button
                type="button"
                onClick={() => setActiveTab('overview')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-colors ${
                  activeTab === 'overview'
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/20'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard Overview</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('security')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-colors ${
                  activeTab === 'security'
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/20'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <ShieldCheck className="w-4 h-4" />
                <span>2FA Security Status</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('edit')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-colors ${
                  activeTab === 'edit'
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/20'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Edit3 className="w-4 h-4" />
                <span>Edit Profile</span>
              </button>

              <Link
                to="/profile-preview"
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
              >
                <User className="w-4 h-4" />
                <span>Profile Preview</span>
              </Link>
            </nav>

            <div className="pt-4 border-t border-slate-100">
              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-red-50 text-red-700 hover:bg-red-100 text-xs font-bold transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout Session</span>
              </button>
            </div>
          </div>

          {/* Profile Completion Card */}
          <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Profile Completion
              </span>
              <span
                data-testid="dashboard-completion-percentage"
                className="text-sm font-extrabold text-blue-600"
              >
                {dashboard.profile_completion_percentage}%
              </span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 to-emerald-500 transition-all duration-500"
                style={{ width: `${dashboard.profile_completion_percentage}%` }}
              />
            </div>
            <p className="text-xs text-slate-500">
              Status:{' '}
              <span className="font-semibold text-slate-800">
                {dashboard.profile_completion_status}
              </span>
            </p>
          </div>
        </aside>

        {/* Main Dashboard Content Area */}
        <div className="lg:col-span-9 space-y-6">
          {/* Welcome Banner */}
          <div className="bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-700 rounded-3xl p-6 sm:p-8 text-white shadow-lg shadow-blue-900/10 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
            <div className="space-y-1.5">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/15 text-xs font-semibold backdrop-blur-sm">
                <Award className="w-3.5 h-3.5" />
                <span>SkillVerse Student Portal</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold">
                Welcome back, {dashboard.full_name}!
              </h1>
              <p className="text-sm text-blue-100 max-w-xl">
                Your candidate onboarding pipeline and multi-channel 2FA verification are complete.
              </p>
            </div>

            <button
              type="button"
              onClick={() => setActiveTab('edit')}
              className="self-start sm:self-auto inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white text-blue-900 text-xs font-bold hover:bg-blue-50 transition-colors shrink-0"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Edit Profile</span>
            </button>
          </div>

          {saveSuccess && (
            <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-800 flex items-center gap-2.5">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <span>{saveSuccess}</span>
            </div>
          )}

          {errorMsg && (
            <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-sm text-red-800 flex items-center gap-2.5">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <input
            ref={resumeInputRef}
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleDashboardResumeUpload(e.target.files[0]);
                e.target.value = '';
              }
            }}
          />

          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Verification Status Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="bg-white rounded-2xl border border-slate-200/80 p-4 flex items-center gap-3 shadow-sm">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase text-slate-400">Account</p>
                    <p
                      data-testid="status-account-active"
                      className="text-sm font-bold text-emerald-700"
                    >
                      {dashboard.is_active ? 'Active' : 'Inactive'}
                    </p>
                  </div>
                </div>

                <div className="bg-white rounded-2xl border border-slate-200/80 p-4 flex items-center gap-3 shadow-sm">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                    <Mail className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase text-slate-400">Email OTP</p>
                    <p
                      data-testid="status-email-otp"
                      className="text-sm font-bold text-slate-900"
                    >
                      {dashboard.verification_status.email ? 'Verified' : 'Pending'}
                    </p>
                  </div>
                </div>

                <div className="bg-white rounded-2xl border border-slate-200/80 p-4 flex items-center gap-3 shadow-sm">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <MessageSquare className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase text-slate-400">
                      WhatsApp OTP
                    </p>
                    <p
                      data-testid="status-whatsapp-otp"
                      className="text-sm font-bold text-slate-900"
                    >
                      {dashboard.verification_status.whatsapp ? 'Verified' : 'Pending'}
                    </p>
                  </div>
                </div>

                <div className="bg-white rounded-2xl border border-slate-200/80 p-4 flex items-center gap-3 shadow-sm">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                    <QrCode className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase text-slate-400">
                      Google Authenticator
                    </p>
                    <p
                      data-testid="status-google-authenticator"
                      className="text-sm font-bold text-slate-900"
                    >
                      {dashboard.verification_status.totp ? 'Enrolled' : 'Pending'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Candidate Profile Card & Academic/Experience Details */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 space-y-4">
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
                    <User className="w-4 h-4 text-blue-600" />
                    <span>Candidate Account Information</span>
                  </h2>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between py-1.5 border-b border-slate-100">
                      <span className="text-slate-500">Student ID</span>
                      <span className="font-mono text-xs font-semibold text-slate-800">
                        {dashboard.user_id.slice(0, 12)}...
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-slate-100">
                      <span className="text-slate-500">Full Name</span>
                      <span
                        data-testid="dashboard-full-name"
                        className="font-semibold text-slate-900"
                      >
                        {dashboard.full_name}
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-slate-100">
                      <span className="text-slate-500">Verified Email</span>
                      <span data-testid="dashboard-email" className="font-semibold text-slate-900">
                        {dashboard.email}
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-slate-100">
                      <span className="text-slate-500 flex items-center gap-1">
                        <Phone className="w-3.5 h-3.5 text-slate-400" />
                        Phone
                      </span>
                      <span data-testid="dashboard-phone" className="font-semibold text-slate-900">
                        {dashboard.phone}
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5">
                      <span className="text-slate-500">Joined On</span>
                      <span className="font-semibold text-slate-900">
                        {new Date(dashboard.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Experience & Qualification Card */}
                <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 space-y-5">
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
                    <BookOpen className="w-4 h-4 text-blue-600" />
                    <span>Qualification &amp; Experience</span>
                  </h2>

                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <GraduationCap className="w-4 h-4 text-blue-600" />
                      Qualification
                    </span>
                    <p
                      data-testid="dashboard-qualification"
                      className="text-sm font-bold text-slate-900 mt-1"
                    >
                      {dashboard.qualification || 'Not provided'}
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <Briefcase className="w-4 h-4 text-blue-600" />
                      Work Experience
                    </span>
                    <p
                      data-testid="dashboard-experience"
                      className="text-sm font-bold text-slate-900 mt-1"
                    >
                      {dashboard.experience || 'Not provided'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Technical Skills Section */}
              <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-blue-600" />
                    <span>Verified Technical Skills ({dashboard.skills.length})</span>
                  </h2>
                  <button
                    type="button"
                    onClick={() => setActiveTab('edit')}
                    className="text-xs font-semibold text-blue-600 hover:underline"
                  >
                    + Manage Skills
                  </button>
                </div>

                {dashboard.skills.length > 0 ? (
                  <div data-testid="dashboard-skills" className="flex flex-wrap gap-2">
                    {dashboard.skills.map((skill) => (
                      <span
                        key={skill}
                        className="px-3.5 py-1.5 rounded-xl bg-blue-50 text-blue-800 border border-blue-200 text-xs font-semibold"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">
                    No technical skills added yet. Click Manage Skills to add your skills.
                  </p>
                )}
              </div>

              {/* Uploaded Resume Card */}
              <div
                data-testid="dashboard-latest-resume"
                className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 space-y-4"
              >
                {dashboard.latest_resume ? (
                  <>
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="flex items-center gap-3.5">
                        <div className="w-11 h-11 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                          <FileText className="w-6 h-6" />
                        </div>
                        <div>
                          <p className="text-xs font-bold uppercase tracking-wider text-blue-600">
                            Latest Uploaded Resume
                          </p>
                          <p
                            data-testid="dashboard-resume-filename"
                            className="text-sm font-bold text-slate-900"
                          >
                            {dashboard.latest_resume.original_filename}
                          </p>
                          <p
                            data-testid="dashboard-resume-date"
                            className="text-xs font-medium text-slate-500 mt-0.5"
                          >
                            Uploaded on{' '}
                            {new Date(dashboard.latest_resume.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2.5">
                        <button
                          type="button"
                          data-testid="view-uploaded-resume-btn"
                          onClick={() => setShowResumePreview((prev) => !prev)}
                          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 transition-colors"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>
                            {showResumePreview ? 'Hide Resume Preview' : 'View Uploaded Resume'}
                          </span>
                        </button>

                        <a
                          href={onboardingApi.getResumeFileUrl(dashboard.latest_resume.id, true)}
                          download={dashboard.latest_resume.original_filename}
                          data-testid="download-resume-link"
                          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-blue-300 bg-blue-50/60 text-blue-700 text-xs font-semibold hover:bg-blue-100/70 transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>Download Resume</span>
                        </a>

                        <button
                          type="button"
                          disabled={uploadingResume}
                          onClick={() => resumeInputRef.current?.click()}
                          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-50 disabled:opacity-50 transition-colors"
                        >
                          {uploadingResume ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <UploadCloud className="w-3.5 h-3.5" />
                          )}
                          <span>Update Resume</span>
                        </button>
                      </div>
                    </div>

                    {showResumePreview && (
                      <div
                        data-testid="uploaded-resume-preview-panel"
                        className="pt-4 border-t border-slate-100 space-y-4"
                      >
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                            <span className="font-semibold text-slate-400 uppercase block">
                              Resume ID
                            </span>
                            <span className="font-mono font-semibold text-slate-800 break-all">
                              {dashboard.latest_resume.id}
                            </span>
                          </div>
                          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                            <span className="font-semibold text-slate-400 uppercase block">
                              Extracted Qualification
                            </span>
                            <span className="font-semibold text-slate-900">
                              {String(
                                dashboard.latest_resume.extracted_metadata?.qualification ||
                                  dashboard.qualification ||
                                  'Not specified'
                              )}
                            </span>
                          </div>
                          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                            <span className="font-semibold text-slate-400 uppercase block">
                              Extracted Experience
                            </span>
                            <span className="font-semibold text-slate-900">
                              {String(
                                dashboard.latest_resume.extracted_metadata?.experience ||
                                  dashboard.experience ||
                                  'Not specified'
                              )}
                            </span>
                          </div>
                        </div>

                        {dashboard.latest_resume.original_filename
                          .toLowerCase()
                          .endsWith('.pdf') && (
                          <iframe
                            src={onboardingApi.getResumeFileUrl(dashboard.latest_resume.id)}
                            title="Uploaded Resume Document"
                            className="w-full h-96 rounded-2xl border border-slate-200 bg-slate-50"
                          />
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3.5">
                      <div className="w-11 h-11 rounded-2xl bg-slate-100 text-slate-500 flex items-center justify-center shrink-0">
                        <FileText className="w-6 h-6" />
                      </div>
                      <div>
                        <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                          Latest Uploaded Resume
                        </p>
                        <p className="text-sm font-medium text-slate-700">
                          No resume uploaded yet. Upload a PDF or DOCX resume to auto-populate your
                          profile.
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={uploadingResume}
                      onClick={() => resumeInputRef.current?.click()}
                      className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 disabled:opacity-50 transition-colors self-start sm:self-auto"
                    >
                      {uploadingResume ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <UploadCloud className="w-3.5 h-3.5" />
                      )}
                      <span>Upload Resume</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-8 space-y-6">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-600" />
                <span>Multi-Channel 2FA &amp; Security Audit</span>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-2">
                  <span className="text-xs font-bold uppercase text-emerald-700">Channel 1</span>
                  <h3 className="text-base font-bold text-slate-900">Email OTP</h3>
                  <p className="text-xs text-slate-600">
                    Verified against {dashboard.email} with HMAC-SHA256 hashed 6-digit OTP.
                  </p>
                </div>

                <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-2">
                  <span className="text-xs font-bold uppercase text-emerald-700">Channel 2</span>
                  <h3 className="text-base font-bold text-slate-900">WhatsApp OTP</h3>
                  <p className="text-xs text-slate-600">
                    Verified against {dashboard.phone} via WhatsApp OTP adapter.
                  </p>
                </div>

                <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-2">
                  <span className="text-xs font-bold uppercase text-emerald-700">Channel 3</span>
                  <h3 className="text-base font-bold text-slate-900">Browser TOTP</h3>
                  <p className="text-xs text-slate-600">
                    Time-based RFC 6238 Authenticator enrolled with Fernet-encrypted secret at rest.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'edit' && (
            <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-8">
              <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                <Edit3 className="w-5 h-5 text-blue-600" />
                <span>Update Student Profile</span>
              </h2>

              <form onSubmit={handleSaveProfile} className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                      Full Name
                    </label>
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                      Phone Number
                    </label>
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      required
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                      Qualification
                    </label>
                    <input
                      type="text"
                      value={qualification}
                      onChange={(e) => setQualification(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                      Work Experience
                    </label>
                    <input
                      type="text"
                      value={experience}
                      onChange={(e) => setExperience(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                    Skills
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={skillInput}
                      onChange={(e) => setSkillInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleAddSkill();
                        }
                      }}
                      placeholder="Add a skill..."
                      className="flex-1 px-3.5 py-2 rounded-xl border border-slate-300 text-sm"
                    />
                    <button
                      type="button"
                      onClick={handleAddSkill}
                      className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold hover:bg-slate-200 flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add</span>
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-3">
                    {skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-blue-50 text-blue-800 border border-blue-200 text-xs font-semibold"
                      >
                        <span>{skill}</span>
                        <button
                          type="button"
                          onClick={() => setSkills(skills.filter((s) => s !== skill))}
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setActiveTab('overview')}
                    className="px-4 py-2.5 rounded-xl border border-slate-300 text-slate-700 text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 disabled:opacity-50"
                  >
                    {saving ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Saving...</span>
                      </>
                    ) : (
                      <>
                        <Save className="w-3.5 h-3.5" />
                        <span>Save Profile</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
