import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  Briefcase,
  CheckCircle2,
  FileText,
  GraduationCap,
  Loader2,
  Mail,
  Phone,
  Sparkles,
  UploadCloud,
  User,
  Wrench,
} from 'lucide-react';
import { StepProgress } from '../components/StepProgress';
import { useOnboarding } from '../context/OnboardingContext';
import { extractApiErrorMessage, onboardingApi } from '../services/api';
import { ExtractedResumeData } from '../types/onboarding';

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];

export const ResumeUploadPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const {
    setParsedResumeState,
    extractedResume,
    resumeFilename,
    accessToken,
    currentUserProfile,
    refreshProfile,
  } = useOnboarding();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [parsingStatus, setParsingStatus] = useState<
    'idle' | 'uploading' | 'parsing' | 'success' | 'error'
  >(extractedResume ? 'success' : 'idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<ExtractedResumeData | null>(extractedResume);
  const [parsedFilename, setParsedFilename] = useState<string | null>(resumeFilename);

  const validateFileClientSide = (file: File): string | null => {
    const lowerName = file.name.toLowerCase();
    const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
    if (!hasValidExt) {
      return 'Unsupported file format. Please upload a PDF (.pdf) or Word (.docx) resume.';
    }
    if (file.size === 0) {
      return 'The selected file is empty (0 bytes). Please choose a valid resume.';
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return 'File size exceeds the 5 MB limit. Please upload a smaller file.';
    }
    return null;
  };

  const handleFileUpload = async (file: File) => {
    setErrorMessage(null);
    const validationErr = validateFileClientSide(file);
    if (validationErr) {
      setSelectedFile(null);
      setParsingStatus('error');
      setErrorMessage(validationErr);
      return;
    }

    setSelectedFile(file);
    setUploadProgress(0);
    setParsingStatus('uploading');

    try {
      const response = await onboardingApi.parseResume(file, (percent) => {
        setUploadProgress(percent);
        if (percent >= 100) {
          setParsingStatus('parsing');
        }
      });

      setPreviewData(response.extracted_data);
      setParsedFilename(response.original_filename);
      setParsedResumeState(
        response.resume_id,
        response.original_filename,
        response.extracted_data
      );
      if (accessToken || currentUserProfile) {
        await refreshProfile();
      }
      setParsingStatus('success');
    } catch (err) {
      setParsingStatus('error');
      setErrorMessage(extractApiErrorMessage(err));
    }
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <StepProgress currentStep={1} />

      <div className="text-center max-w-2xl mx-auto mb-8">
        <h1 className="text-3xl font-extrabold text-slate-900">
          Upload Your Resume to Auto-Fill Registration
        </h1>
        <p className="text-slate-600 mt-2 text-sm sm:text-base">
          Upload your resume in <span className="font-semibold text-slate-800">PDF</span> or{' '}
          <span className="font-semibold text-slate-800">DOCX</span> format. Our parser extracts
          your profile details so you can review and edit them before registering.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Upload Dropzone Column */}
        <div className="lg:col-span-6 bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-blue-600" />
              <span>Resume Document Upload</span>
            </h2>
            <span className="text-xs font-medium text-slate-500">Max 5 MB • .PDF / .DOCX</span>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
              isDragging
                ? 'border-blue-600 bg-blue-50/70'
                : 'border-slate-300 hover:border-blue-500 hover:bg-slate-50/80'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileUpload(e.target.files[0]);
                }
              }}
            />

            <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-4">
              <FileText className="w-7 h-7" />
            </div>

            <p className="text-sm font-semibold text-slate-800">
              Drag &amp; drop your resume here, or{' '}
              <span className="text-blue-600 underline">browse files</span>
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Supports standard text-based PDF and Microsoft Word (.docx) resumes
            </p>

            {selectedFile && (
              <div className="mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 text-xs font-medium">
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                <span className="truncate max-w-[220px]">{selectedFile.name}</span>
                <span className="text-slate-400">
                  ({(selectedFile.size / 1024).toFixed(1)} KB)
                </span>
              </div>
            )}
          </div>

          {/* Upload & Parsing Progress Indicator */}
          {(parsingStatus === 'uploading' || parsingStatus === 'parsing') && (
            <div className="p-4 rounded-xl bg-blue-50/80 border border-blue-200 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-semibold text-blue-900">
                <span className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  {parsingStatus === 'uploading'
                    ? 'Uploading resume to server...'
                    : 'Extracting structured candidate attributes...'}
                </span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-blue-200 overflow-hidden">
                <div
                  className="h-full bg-blue-600 transition-all duration-300"
                  style={{ width: `${Math.max(uploadProgress, 15)}%` }}
                />
              </div>
            </div>
          )}

          {/* Error Alert */}
          {parsingStatus === 'error' && errorMessage && (
            <div
              role="alert"
              className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-red-800"
            >
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div className="text-xs sm:text-sm">
                <p className="font-semibold">Resume Parsing Failed</p>
                <p className="mt-0.5 text-red-700">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* Success Banner */}
          {parsingStatus === 'success' && previewData && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3 text-emerald-900">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              <div className="text-xs sm:text-sm">
                <p className="font-semibold">Resume Parsed Successfully!</p>
                <p className="mt-0.5 text-emerald-700">
                  Extracted details from <span className="font-medium">{parsedFilename}</span>.
                  Review the preview and proceed to registration.
                </p>
              </div>
            </div>
          )}

          <div className="pt-2 flex items-center justify-between border-t border-slate-100">
            <button
              type="button"
              onClick={() => navigate('/register')}
              className="text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
            >
              Skip &amp; fill registration manually →
            </button>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
            >
              Browse Files
            </button>
          </div>
        </div>

        {/* Extracted Information Preview Column */}
        <div className="lg:col-span-6 bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-blue-600" />
              <h2 className="text-base font-bold text-slate-900">
                Extracted Candidate Information
              </h2>
            </div>
            {previewData && (
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                Ready for Auto-Fill
              </span>
            )}
          </div>

          {!previewData ? (
            <div className="py-12 text-center space-y-3 text-slate-400">
              <FileText className="w-10 h-10 mx-auto stroke-[1.5]" />
              <p className="text-sm font-medium text-slate-600">
                No resume parsed yet
              </p>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Upload a PDF or DOCX resume on the left to preview extracted candidate fields here.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-blue-600" />
                    Full Name
                  </span>
                  <p className="text-sm font-semibold text-slate-900 mt-1">
                    {previewData.full_name || (
                      <span className="text-slate-400 italic font-normal">Not detected</span>
                    )}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-blue-600" />
                    Email Address
                  </span>
                  <p className="text-sm font-semibold text-slate-900 mt-1 truncate">
                    {previewData.email || (
                      <span className="text-slate-400 italic font-normal">Not detected</span>
                    )}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-blue-600" />
                    Phone Number
                  </span>
                  <p className="text-sm font-semibold text-slate-900 mt-1">
                    {previewData.phone || (
                      <span className="text-slate-400 italic font-normal">Not detected</span>
                    )}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <GraduationCap className="w-3.5 h-3.5 text-blue-600" />
                    Qualification
                  </span>
                  <p className="text-sm font-semibold text-slate-900 mt-1">
                    {previewData.qualification || (
                      <span className="text-slate-400 italic font-normal">Not detected</span>
                    )}
                  </p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Briefcase className="w-3.5 h-3.5 text-blue-600" />
                  Work Experience
                </span>
                <p className="text-sm font-semibold text-slate-900 mt-1">
                  {previewData.experience || (
                    <span className="text-slate-400 italic font-normal">Not detected</span>
                  )}
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2">
                  <Wrench className="w-3.5 h-3.5 text-blue-600" />
                  Extracted Skills ({previewData.skills.length})
                </span>
                {previewData.skills.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {previewData.skills.map((skill) => (
                      <span
                        key={skill}
                        className="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">No skills detected</p>
                )}
              </div>

              {accessToken || currentUserProfile ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => navigate('/profile-preview')}
                    className="w-full inline-flex items-center justify-center gap-2 py-3.5 px-5 rounded-xl border border-blue-600 text-blue-700 font-semibold hover:bg-blue-50 transition-all"
                  >
                    <span>View Updated Profile</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate('/dashboard/student')}
                    className="w-full inline-flex items-center justify-center gap-2 py-3.5 px-5 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 shadow-md shadow-blue-600/20 transition-all"
                  >
                    <span>Go to Student Dashboard</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => navigate('/register')}
                  className="w-full inline-flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 shadow-md shadow-blue-600/20 transition-all"
                >
                  <span>Continue to Registration (Auto-Fill Form)</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
