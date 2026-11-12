import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  Briefcase,
  CheckCircle2,
  Download,
  Edit3,
  Eye,
  FileText,
  GraduationCap,
  Loader2,
  Mail,
  Phone,
  Plus,
  Save,
  ShieldCheck,
  UploadCloud,
  User,
  Wrench,
  X,
} from 'lucide-react';
import { StepProgress } from '../components/StepProgress';
import { useOnboarding } from '../context/OnboardingContext';
import { extractApiErrorMessage, onboardingApi } from '../services/api';
import { ProfileData } from '../types/onboarding';

export const ProfilePreviewPage: React.FC = () => {
  const navigate = useNavigate();
  const resumeInputRef = useRef<HTMLInputElement | null>(null);
  const { currentUserProfile, refreshProfile, setParsedResumeState } = useOnboarding();

  const [profile, setProfile] = useState<ProfileData | null>(currentUserProfile);
  const [loading, setLoading] = useState<boolean>(!currentUserProfile);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [uploadingResume, setUploadingResume] = useState<boolean>(false);
  const [showResumePreview, setShowResumePreview] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Editable form state
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [experience, setExperience] = useState('');
  const [qualification, setQualification] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState('');

  const syncFormWithProfile = (p: ProfileData) => {
    setFullName(p.full_name);
    setPhone(p.phone);
    setExperience(p.experience || '');
    setQualification(p.qualification || '');
    setSkills(p.skills || []);
  };

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const refreshed = await refreshProfile();
        const data = refreshed || (await onboardingApi.getProfile());
        if (mounted) {
          setProfile(data);
          syncFormWithProfile(data);
        }
      } catch (err) {
        if (mounted) {
          setErrorMsg(extractApiErrorMessage(err));
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const handleResumeUpload = async (file: File) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setUploadingResume(true);
    try {
      const parsed = await onboardingApi.parseResume(file);
      setParsedResumeState(parsed.resume_id, parsed.original_filename, parsed.extracted_data);
      const updatedProfile = await onboardingApi.getProfile();
      setProfile(updatedProfile);
      syncFormWithProfile(updatedProfile);
      await refreshProfile();
      setSuccessMsg(
        `Resume "${parsed.original_filename}" uploaded, linked to your account, and synchronized with your profile!`
      );
    } catch (err) {
      setErrorMsg(extractApiErrorMessage(err));
    } finally {
      setUploadingResume(false);
    }
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
    setErrorMsg(null);
    setSuccessMsg(null);
    setSaving(true);
    try {
      const updated = await onboardingApi.updateProfile({
        full_name: fullName,
        phone,
        skills,
        experience,
        qualification,
      });
      setProfile(updated);
      syncFormWithProfile(updated);
      await refreshProfile();
      setIsEditing(false);
      setSuccessMsg('Profile updated and saved successfully!');
    } catch (err) {
      setErrorMsg(extractApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-slate-600">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600 mb-3" />
        <p className="text-sm font-medium">Loading verified candidate profile...</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-red-600 mx-auto" />
        <h2 className="text-xl font-bold text-slate-900">Unable to Load Profile</h2>
        <p className="text-sm text-slate-600">
          {errorMsg || 'Please sign in with an active, verified account.'}
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <StepProgress currentStep={4} />

      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-10 space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-6">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-600 mb-1">
              <ShieldCheck className="w-4 h-4" />
              <span>Verified Candidate Profile Preview</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900">
              {profile.full_name}
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Review your verified onboarding record and make any final edits before launching your
              Student Dashboard.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setErrorMsg(null);
                setSuccessMsg(null);
                if (isEditing) {
                  syncFormWithProfile(profile);
                }
                setIsEditing(!isEditing);
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-slate-300 text-slate-700 text-sm font-semibold hover:bg-slate-50 transition-colors"
            >
              <Edit3 className="w-4 h-4 text-blue-600" />
              <span>{isEditing ? 'Cancel Editing' : 'Edit Profile'}</span>
            </button>

            <button
              type="button"
              onClick={() => navigate('/dashboard/student')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 shadow-md shadow-blue-600/20 transition-all"
            >
              <span>Go to Student Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Notifications */}
        {errorMsg && (
          <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-800 flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-800 flex items-start gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Profile Completion Percentage Card */}
        <div
          data-testid="profile-completion-card"
          className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2.5"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
              Profile Completion Percentage
            </span>
            <span
              data-testid="profile-completion-percentage"
              className="text-base font-extrabold text-blue-600"
            >
              {profile.profile_completion}%
            </span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-slate-200 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-600 to-emerald-500 transition-all duration-500"
              style={{ width: `${profile.profile_completion}%` }}
            />
          </div>
          <p className="text-xs text-slate-500">
            Status:{' '}
            <span className="font-semibold text-slate-800">
              {profile.profile_completion === 100
                ? 'Complete'
                : profile.profile_completion >= 75
                  ? 'Almost Complete'
                  : 'In Progress'}
            </span>
          </p>
        </div>

        {/* Verification Badges Row */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-emerald-700">Account Status</p>
              <p
                data-testid="profile-account-status"
                className="text-sm font-bold text-emerald-950 mt-0.5"
              >
                {profile.is_active ? 'Active' : 'Inactive'}
              </p>
            </div>
            <ShieldCheck className="w-6 h-6 text-emerald-600" />
          </div>

          <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-emerald-700">Email Verification</p>
              <p
                data-testid="profile-email-status"
                className="text-sm font-bold text-emerald-950 mt-0.5"
              >
                {profile.is_email_verified ? 'Verified via OTP' : 'Unverified'}
              </p>
            </div>
            <CheckCircle2 className="w-6 h-6 text-emerald-600" />
          </div>

          <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-emerald-700">WhatsApp Verification</p>
              <p
                data-testid="profile-whatsapp-status"
                className="text-sm font-bold text-emerald-950 mt-0.5"
              >
                {profile.is_whatsapp_verified ? 'Verified via OTP' : 'Unverified'}
              </p>
            </div>
            <CheckCircle2 className="w-6 h-6 text-emerald-600" />
          </div>

          <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-emerald-700">Google Authenticator</p>
              <p
                data-testid="profile-totp-status"
                className="text-sm font-bold text-emerald-950 mt-0.5"
              >
                {profile.is_totp_enabled ? 'Enrolled & Active' : 'Disabled'}
              </p>
            </div>
            <CheckCircle2 className="w-6 h-6 text-emerald-600" />
          </div>
        </div>

        <input
          ref={resumeInputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleResumeUpload(e.target.files[0]);
              e.target.value = '';
            }
          }}
        />

        {/* View Mode vs Edit Mode */}
        {!isEditing ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-blue-600" />
                  Full Name
                </span>
                <p
                  data-testid="profile-full-name"
                  className="text-base font-bold text-slate-900 mt-1"
                >
                  {profile.full_name || 'Not provided'}
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-blue-600" />
                  Email Address
                </span>
                <p data-testid="profile-email" className="text-base font-bold text-slate-900 mt-1">
                  {profile.email}
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-blue-600" />
                  Phone Number
                </span>
                <p data-testid="profile-phone" className="text-base font-bold text-slate-900 mt-1">
                  {profile.phone}
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <GraduationCap className="w-3.5 h-3.5 text-blue-600" />
                  Qualification
                </span>
                <p
                  data-testid="profile-qualification"
                  className="text-base font-bold text-slate-900 mt-1"
                >
                  {profile.qualification || 'Not specified'}
                </p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Briefcase className="w-3.5 h-3.5 text-blue-600" />
                Work Experience
              </span>
              <p
                data-testid="profile-experience"
                className="text-sm font-semibold text-slate-900 mt-1"
              >
                {profile.experience || 'Not specified'}
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2.5">
                <Wrench className="w-3.5 h-3.5 text-blue-600" />
                Skills ({profile.skills.length})
              </span>
              {profile.skills.length > 0 ? (
                <div data-testid="profile-skills" className="flex flex-wrap gap-2">
                  {profile.skills.map((skill) => (
                    <span
                      key={skill}
                      className="px-3 py-1 rounded-lg bg-blue-50 text-blue-800 border border-blue-200 text-xs font-semibold"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              ) : (
                <p data-testid="profile-skills-empty" className="text-xs text-slate-400 italic">
                  No skills listed yet. Upload a resume or click Edit Profile to add skills.
                </p>
              )}
            </div>

            {/* Uploaded Resume Section */}
            <div
              data-testid="profile-uploaded-resume"
              className="p-5 rounded-2xl bg-blue-50/50 border border-blue-200/80 space-y-4"
            >
              {profile.latest_resume ? (
                <>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-blue-700">
                          Uploaded Resume Document
                        </p>
                        <p
                          data-testid="profile-resume-filename"
                          className="text-sm font-bold text-slate-900"
                        >
                          {profile.latest_resume.original_filename}
                        </p>
                        <span className="text-xs font-medium text-slate-500">
                          Uploaded on {new Date(profile.latest_resume.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2.5">
                      <button
                        type="button"
                        data-testid="profile-preview-resume-btn"
                        onClick={() => setShowResumePreview((prev) => !prev)}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>{showResumePreview ? 'Hide Preview' : 'Preview Resume'}</span>
                      </button>

                      <a
                        href={onboardingApi.getResumeFileUrl(profile.latest_resume.id, true)}
                        download={profile.latest_resume.original_filename}
                        data-testid="profile-download-resume-link"
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-blue-300 bg-white text-blue-700 text-xs font-semibold hover:bg-blue-50 transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download</span>
                      </a>

                      <button
                        type="button"
                        disabled={uploadingResume}
                        onClick={() => resumeInputRef.current?.click()}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-300 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 disabled:opacity-50 transition-colors"
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
                      data-testid="profile-resume-preview-panel"
                      className="pt-4 border-t border-blue-200/70 space-y-3"
                    >
                      {profile.latest_resume.original_filename.toLowerCase().endsWith('.pdf') ? (
                        <iframe
                          src={onboardingApi.getResumeFileUrl(profile.latest_resume.id)}
                          title="Candidate Uploaded Resume Preview"
                          className="w-full h-96 rounded-xl border border-slate-200 bg-white"
                        />
                      ) : (
                        <p className="text-xs text-slate-600">
                          Document format ({profile.latest_resume.original_filename}). Click Download
                          above to open the file.
                        </p>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-200 text-slate-600 flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Uploaded Resume
                      </p>
                      <p className="text-sm font-medium text-slate-700">
                        No resume uploaded for this profile yet.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={uploadingResume}
                    onClick={() => resumeInputRef.current?.click()}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors self-start sm:self-auto"
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
        ) : (
          /* Edit Form */
          <form onSubmit={handleSaveProfile} className="space-y-5 bg-slate-50 p-6 rounded-2xl border border-slate-200">
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
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm bg-white"
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
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm bg-white"
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
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm bg-white"
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
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm bg-white"
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
                  className="flex-1 px-3.5 py-2 rounded-xl border border-slate-300 text-sm bg-white"
                />
                <button
                  type="button"
                  onClick={handleAddSkill}
                  className="px-4 py-2 rounded-xl bg-slate-200 text-slate-800 text-xs font-semibold hover:bg-slate-300 flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add</span>
                </button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2.5">
                {skills.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-blue-100 text-blue-900 text-xs font-semibold"
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

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 rounded-xl border border-slate-300 bg-white text-slate-700 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-3.5 h-3.5" />
                    <span>Save Changes</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
