import React from 'react';
import { Navigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useOnboarding } from '../context/OnboardingContext';

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { accessToken, currentUserProfile, isInitializingAuth } = useOnboarding();

  if (isInitializingAuth) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 text-slate-600">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600 mb-3" />
        <p className="text-sm font-medium">Verifying security session...</p>
      </div>
    );
  }

  if (!accessToken && !currentUserProfile) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};
