import React from 'react';
import { Check, FileText, ShieldCheck, UserCheck, UserPlus } from 'lucide-react';

interface StepProgressProps {
  currentStep: 1 | 2 | 3 | 4;
}

const STEPS = [
  { id: 1, title: 'Resume Upload', subtitle: 'AI Data Extraction', icon: FileText },
  { id: 2, title: 'Account Setup', subtitle: 'Auto-Filled Registration', icon: UserPlus },
  { id: 3, title: 'Multi-Channel 2FA', subtitle: 'Email, WhatsApp & TOTP', icon: ShieldCheck },
  { id: 4, title: 'Profile Review', subtitle: 'Verify & Launch Dashboard', icon: UserCheck },
];

export const StepProgress: React.FC<StepProgressProps> = ({ currentStep }) => {
  return (
    <div className="w-full max-w-4xl mx-auto mb-8">
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm px-6 py-4">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {STEPS.map((step) => {
            const Icon = step.icon;
            const isCompleted = step.id < currentStep;
            const isActive = step.id === currentStep;

            return (
              <div
                key={step.id}
                className={`flex items-center gap-3 p-2.5 rounded-xl transition-all ${
                  isActive
                    ? 'bg-blue-50/90 border border-blue-200'
                    : isCompleted
                    ? 'bg-emerald-50/60 border border-emerald-100'
                    : 'opacity-60'
                }`}
              >
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 font-semibold text-sm ${
                    isCompleted
                      ? 'bg-emerald-600 text-white'
                      : isActive
                      ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                      : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {isCompleted ? <Check className="w-5 h-5" /> : <Icon className="w-5 h-5" />}
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Step 0{step.id}
                  </p>
                  <p
                    className={`text-sm font-semibold truncate ${
                      isActive
                        ? 'text-blue-950'
                        : isCompleted
                        ? 'text-emerald-950'
                        : 'text-slate-700'
                    }`}
                  >
                    {step.title}
                  </p>
                  <p className="text-xs text-slate-500 truncate">{step.subtitle}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
