import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  getStoredAccessToken,
  onboardingApi,
  setStoredAccessToken,
} from '../services/api';
import { ExtractedResumeData, ProfileData } from '../types/onboarding';

interface StagedUserState {
  userId: string;
  email: string;
  phone: string;
  fullName?: string;
  isActive: boolean;
  isEmailVerified: boolean;
  isWhatsappVerified: boolean;
  isTotpEnabled: boolean;
  requiredChannels: string[];
}

interface OnboardingContextValue {
  resumeId: string | null;
  resumeFilename: string | null;
  extractedResume: ExtractedResumeData | null;
  stagedUser: StagedUserState | null;
  accessToken: string | null;
  currentUserProfile: ProfileData | null;
  isInitializingAuth: boolean;
  setParsedResumeState: (
    resumeId: string,
    filename: string,
    data: ExtractedResumeData
  ) => void;
  setStagedUser: React.Dispatch<React.SetStateAction<StagedUserState | null>>;
  setAuthenticatedToken: (token: string | null) => void;
  refreshProfile: (overrideResumeId?: string) => Promise<ProfileData | null>;
  logoutSession: () => Promise<void>;
}

const STAGED_USER_STORAGE_KEY = 'edtech_staged_user';
const EXTRACTED_RESUME_STORAGE_KEY = 'edtech_extracted_resume';

const OnboardingContext = createContext<OnboardingContextValue | undefined>(undefined);

export const OnboardingProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [resumeId, setResumeId] = useState<string | null>(() => {
    const saved =
      sessionStorage.getItem(EXTRACTED_RESUME_STORAGE_KEY) ||
      localStorage.getItem(EXTRACTED_RESUME_STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved).resumeId || null;
      } catch {
        return null;
      }
    }
    return null;
  });

  const [resumeFilename, setResumeFilename] = useState<string | null>(() => {
    const saved =
      sessionStorage.getItem(EXTRACTED_RESUME_STORAGE_KEY) ||
      localStorage.getItem(EXTRACTED_RESUME_STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved).filename || null;
      } catch {
        return null;
      }
    }
    return null;
  });

  const [extractedResume, setExtractedResume] = useState<ExtractedResumeData | null>(() => {
    const saved =
      sessionStorage.getItem(EXTRACTED_RESUME_STORAGE_KEY) ||
      localStorage.getItem(EXTRACTED_RESUME_STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved).data || null;
      } catch {
        return null;
      }
    }
    return null;
  });

  const [stagedUser, setStagedUser] = useState<StagedUserState | null>(() => {
    const saved =
      sessionStorage.getItem(STAGED_USER_STORAGE_KEY) ||
      localStorage.getItem(STAGED_USER_STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });

  const [accessToken, setAccessToken] = useState<string | null>(() => getStoredAccessToken());
  const [currentUserProfile, setCurrentUserProfile] = useState<ProfileData | null>(null);
  const [isInitializingAuth, setIsInitializingAuth] = useState<boolean>(true);

  useEffect(() => {
    if (stagedUser) {
      const serialized = JSON.stringify(stagedUser);
      sessionStorage.setItem(STAGED_USER_STORAGE_KEY, serialized);
      localStorage.setItem(STAGED_USER_STORAGE_KEY, serialized);
    } else {
      sessionStorage.removeItem(STAGED_USER_STORAGE_KEY);
      localStorage.removeItem(STAGED_USER_STORAGE_KEY);
    }
  }, [stagedUser]);

  const setParsedResumeState = (
    id: string,
    filename: string,
    data: ExtractedResumeData
  ) => {
    setResumeId(id);
    setResumeFilename(filename);
    setExtractedResume(data);
    const serialized = JSON.stringify({ resumeId: id, filename, data });
    sessionStorage.setItem(EXTRACTED_RESUME_STORAGE_KEY, serialized);
    localStorage.setItem(EXTRACTED_RESUME_STORAGE_KEY, serialized);
  };

  const setAuthenticatedToken = (token: string | null) => {
    setStoredAccessToken(token);
    setAccessToken(token);
  };

  const refreshProfile = async (overrideResumeId?: string): Promise<ProfileData | null> => {
    try {
      let profile = await onboardingApi.getProfile();
      const targetResumeId = overrideResumeId ?? resumeId;
      if (
        targetResumeId &&
        (!profile.latest_resume || profile.latest_resume.id !== targetResumeId)
      ) {
        try {
          await onboardingApi.associateResume(targetResumeId);
          profile = await onboardingApi.getProfile();
        } catch {
          // Ignore if resume belongs to another user or was not found
        }
      }
      setCurrentUserProfile(profile);
      return profile;
    } catch {
      setCurrentUserProfile(null);
      return null;
    }
  };

  useEffect(() => {
    let mounted = true;
    const init = async () => {
      const token = getStoredAccessToken();
      if (token) {
        try {
          let profile = await onboardingApi.getProfile();
          if (resumeId && (!profile.latest_resume || profile.latest_resume.id !== resumeId)) {
            try {
              await onboardingApi.associateResume(resumeId);
              profile = await onboardingApi.getProfile();
            } catch {
              // Ignore if resume belongs to another user or was not found
            }
          }
          if (mounted) {
            setCurrentUserProfile(profile);
          }
        } catch {
          if (mounted) {
            setStoredAccessToken(null);
            setAccessToken(null);
            setCurrentUserProfile(null);
          }
        }
      }
      if (mounted) {
        setIsInitializingAuth(false);
      }
    };
    init();
    return () => {
      mounted = false;
    };
  }, []);

  const logoutSession = async () => {
    await onboardingApi.logout();
    setAccessToken(null);
    setCurrentUserProfile(null);
    setStagedUser(null);
    setResumeId(null);
    setResumeFilename(null);
    setExtractedResume(null);
    sessionStorage.removeItem(STAGED_USER_STORAGE_KEY);
    localStorage.removeItem(STAGED_USER_STORAGE_KEY);
    sessionStorage.removeItem(EXTRACTED_RESUME_STORAGE_KEY);
    localStorage.removeItem(EXTRACTED_RESUME_STORAGE_KEY);
  };

  return (
    <OnboardingContext.Provider
      value={{
        resumeId,
        resumeFilename,
        extractedResume,
        stagedUser,
        accessToken,
        currentUserProfile,
        isInitializingAuth,
        setParsedResumeState,
        setStagedUser,
        setAuthenticatedToken,
        refreshProfile,
        logoutSession,
      }}
    >
      {children}
    </OnboardingContext.Provider>
  );
};

export function useOnboarding(): OnboardingContextValue {
  const ctx = useContext(OnboardingContext);
  if (!ctx) {
    throw new Error('useOnboarding must be used within an OnboardingProvider');
  }
  return ctx;
}
