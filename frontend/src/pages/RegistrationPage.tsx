import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  FileText,
  Loader2,
  Lock,
  Plus,
  Sparkles,
  UserPlus,
  X,
} from 'lucide-react';
import { StepProgress } from '../components/StepProgress';
import { useOnboarding } from '../context/OnboardingContext';
import { extractApiErrorMessage, onboardingApi } from '../services/api';

interface RegistrationFormValues {
  full_name: string;
  email: string;
  phone: string;
  experience: string;
  qualification: string;
  password: string;
  confirm_password: string;
}

export const RegistrationPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    extractedResume,
    resumeId,
    resumeFilename,
    setStagedUser,
  } = useOnboarding();

  const [skills, setSkills] = useState<string[]>(extractedResume?.skills || []);
  const [skillInput, setSkillInput] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<RegistrationFormValues>({
    defaultValues: {
      full_name: extractedResume?.full_name || '',
      email: extractedResume?.email || '',
      phone: extractedResume?.phone || '',
      experience: extractedResume?.experience || '',
      qualification: extractedResume?.qualification || '',
      password: '',
      confirm_password: '',
    },
  });

  useEffect(() => {
    if (extractedResume) {
      reset({
        full_name: extractedResume.full_name || '',
        email: extractedResume.email || '',
        phone: extractedResume.phone || '',
        experience: extractedResume.experience || '',
        qualification: extractedResume.qualification || '',
        password: '',
        confirm_password: '',
      });
      setSkills(extractedResume.skills || []);
    }
  }, [extractedResume, reset]);

  const watchedPassword = watch('password', '');

  const passwordChecks = [
    { label: 'At least 8 characters', valid: watchedPassword.length >= 8 },
    { label: 'Uppercase letter (A-Z)', valid: /[A-Z]/.test(watchedPassword) },
    { label: 'Lowercase letter (a-z)', valid: /[a-z]/.test(watchedPassword) },
    { label: 'Number (0-9)', valid: /\d/.test(watchedPassword) },
    {
      label: 'Special character (!@#$...)',
      valid: /[!@#$%^&*(),.?":{}|<>\-_=+[\]\\;'/`~]/.test(watchedPassword),
    },
  ];

  const handleAddSkill = () => {
    const trimmed = skillInput.trim();
    if (!trimmed) return;
    const parts = trimmed
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    const updated = [...skills];
    for (const part of parts) {
      if (!updated.some((existing) => existing.toLowerCase() === part.toLowerCase())) {
        updated.push(part);
      }
    }
    setSkills(updated);
    setSkillInput('');
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setSkills(skills.filter((s) => s !== skillToRemove));
  };

  const onSubmit = async (values: RegistrationFormValues) => {
    setApiError(null);
    setIsSubmitting(true);
    try {
      const response = await onboardingApi.registerCandidate({
        full_name: values.full_name,
        email: values.email,
        phone: values.phone,
        skills,
        experience: values.experience || null,
        qualification: values.qualification || null,
        password: values.password,
        confirm_password: values.confirm_password,
        resume_id: resumeId,
      });

      setStagedUser({
        userId: response.user_id,
        email: response.email,
        phone: response.phone,
        fullName: values.full_name,
        isActive: response.is_active,
        isEmailVerified: response.verification_status.email,
        isWhatsappVerified: response.verification_status.whatsapp,
        isTotpEnabled: response.verification_status.totp,
        requiredChannels: response.required_2fa_channels,
      });

      navigate('/verify-2fa');
    } catch (err) {
      setApiError(extractApiErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <StepProgress currentStep={2} />

      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold text-blue-600 mb-1">
              <UserPlus className="w-4 h-4" />
              <span>Candidate Account Registration</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900">
              Review &amp; Complete Your Profile
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Verify the auto-filled resume attributes below and create a strong password.
            </p>
          </div>

          {resumeFilename && (
            <div className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-blue-50 border border-blue-200 text-xs font-semibold text-blue-800 shrink-0">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <span>Auto-filled from {resumeFilename}</span>
            </div>
          )}
        </div>

        {apiError && (
          <div
            role="alert"
            className="mt-6 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-red-800"
          >
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-semibold">Registration Error</p>
              <p className="text-red-700 mt-0.5">{apiError}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-6" noValidate>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Full Name */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Full Name *
              </label>
              <input
                type="text"
                placeholder="e.g., Aarav Sharma"
                {...register('full_name', {
                  required: 'Full name is required',
                  minLength: { value: 2, message: 'Full name must be at least 2 characters' },
                })}
                className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              />
              {errors.full_name && (
                <p className="text-xs text-red-600 mt-1">{errors.full_name.message}</p>
              )}
            </div>

            {/* Email */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Email Address *
              </label>
              <input
                type="email"
                placeholder="candidate@example.com"
                {...register('email', {
                  required: 'Email address is required',
                  pattern: {
                    value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                    message: 'Please enter a valid email address',
                  },
                })}
                className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              />
              {errors.email && (
                <p className="text-xs text-red-600 mt-1">{errors.email.message}</p>
              )}
            </div>

            {/* Phone Number */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Phone Number (WhatsApp Enabled) *
              </label>
              <input
                type="tel"
                placeholder="e.g., 9876543210 or +919876543210"
                {...register('phone', {
                  required: 'Phone number is required',
                  pattern: {
                    value: /^\+?[0-9\s\-()]{10,18}$/,
                    message: 'Phone number must be 10 to 15 digits',
                  },
                })}
                className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              />
              {errors.phone && (
                <p className="text-xs text-red-600 mt-1">{errors.phone.message}</p>
              )}
            </div>

            {/* Qualification */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Highest Qualification
              </label>
              <input
                type="text"
                placeholder="e.g., B.Tech in Computer Science"
                {...register('qualification')}
                className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              />
            </div>
          </div>

          {/* Work Experience */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Work Experience
            </label>
            <input
              type="text"
              placeholder="e.g., 2 years of experience in Backend Engineering / Fresher"
              {...register('experience')}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
          </div>

          {/* Skills Tag Editor */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Technical Skills
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
                placeholder="Add skill (e.g., Python, FastAPI, React) and press Enter"
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              />
              <button
                type="button"
                onClick={handleAddSkill}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-100 text-slate-700 text-sm font-semibold hover:bg-slate-200 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Add</span>
              </button>
            </div>

            {skills.length > 0 ? (
              <div className="flex flex-wrap gap-2 mt-3">
                {skills.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-blue-50 text-blue-800 border border-blue-200 text-xs font-semibold"
                  >
                    <span>{skill}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(skill)}
                      className="text-blue-500 hover:text-blue-900"
                      aria-label={`Remove ${skill}`}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 mt-2">
                No skills added yet. Type a skill above and click Add.
              </p>
            )}
          </div>

          {/* Password & Confirm Password */}
          <div className="pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Password (Argon2id Protected) *
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Create a strong password"
                  {...register('password', {
                    required: 'Password is required',
                    minLength: { value: 8, message: 'Password must be at least 8 characters' },
                    validate: (val) => {
                      if (!/[A-Z]/.test(val)) return 'Must include an uppercase letter';
                      if (!/[a-z]/.test(val)) return 'Must include a lowercase letter';
                      if (!/\d/.test(val)) return 'Must include a digit';
                      if (!/[!@#$%^&*(),.?":{}|<>\-_=+[\]\\;'/`~]/.test(val))
                        return 'Must include a special character';
                      return true;
                    },
                  })}
                  className="w-full pl-4 pr-10 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-red-600 mt-1">{errors.password.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Confirm Password *
              </label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Re-enter your password"
                  {...register('confirm_password', {
                    required: 'Please confirm your password',
                    validate: (val) =>
                      val === watchedPassword || 'Passwords do not match',
                  })}
                  className="w-full pl-4 pr-10 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                  aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
              {errors.confirm_password && (
                <p className="text-xs text-red-600 mt-1">{errors.confirm_password.message}</p>
              )}
            </div>
          </div>

          {/* Password Strength Checklist */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-700 mb-2.5">
              <Lock className="w-3.5 h-3.5 text-blue-600" />
              <span>Password Security Requirements</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {passwordChecks.map((check) => (
                <div
                  key={check.label}
                  className={`flex items-center gap-1.5 text-xs ${
                    check.valid ? 'text-emerald-700 font-medium' : 'text-slate-500'
                  }`}
                >
                  <CheckCircle2
                    className={`w-3.5 h-3.5 shrink-0 ${
                      check.valid ? 'text-emerald-600' : 'text-slate-300'
                    }`}
                  />
                  <span>{check.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-100">
            <Link
              to="/upload-resume"
              className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-900"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Resume Upload</span>
            </Link>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-60 shadow-md shadow-blue-600/20 transition-all"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Creating Staged Account...</span>
                </>
              ) : (
                <>
                  <span>Create Account &amp; Proceed to 2FA</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
