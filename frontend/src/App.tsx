import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { OnboardingProvider } from './context/OnboardingContext';
import { MainLayout } from './layouts/MainLayout';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { MultiChannel2FAPage } from './pages/MultiChannel2FAPage';
import { ProfilePreviewPage } from './pages/ProfilePreviewPage';
import { RegistrationPage } from './pages/RegistrationPage';
import { ResumeUploadPage } from './pages/ResumeUploadPage';
import { StudentDashboardPage } from './pages/StudentDashboardPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <OnboardingProvider>
        <MainLayout>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/upload-resume" element={<ResumeUploadPage />} />
            <Route path="/register" element={<RegistrationPage />} />
            <Route path="/verify-2fa" element={<MultiChannel2FAPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/profile-preview"
              element={
                <ProtectedRoute>
                  <ProfilePreviewPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/student"
              element={
                <ProtectedRoute>
                  <StudentDashboardPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </MainLayout>
      </OnboardingProvider>
    </BrowserRouter>
  );
};

export default App;
