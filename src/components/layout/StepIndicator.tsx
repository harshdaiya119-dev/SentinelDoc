import React from 'react';
import { WorkflowStep } from '../../types';
import { Upload, Activity, AlertTriangle, Columns, FileCheck, Check } from 'lucide-react';

interface StepIndicatorProps {
  currentStep: WorkflowStep;
  onStepClick?: (step: WorkflowStep) => void;
  allowedSteps: Set<WorkflowStep>;
}

const STEPS: { id: WorkflowStep; label: string; sub: string; icon: React.ElementType }[] = [
  { id: 'UPLOAD', label: 'Upload', sub: 'Target Document', icon: Upload },
  { id: 'SCANNING', label: 'Telemetry', sub: 'Presidio & NER', icon: Activity },
  { id: 'FINDINGS', label: 'Findings', sub: 'Selective Toggles', icon: AlertTriangle },
  { id: 'PREVIEW', label: 'Redaction', sub: 'Before/After Slider', icon: Columns },
  { id: 'REPORT', label: 'Audit', sub: 'Risk Score & PDF', icon: FileCheck },
];

export const StepIndicator: React.FC<StepIndicatorProps> = ({
  currentStep,
  onStepClick,
  allowedSteps,
}) => {
  const currentIndex = STEPS.findIndex((s) => s.id === currentStep);

  return (
    <nav className="w-full bg-surface border-b border-border px-4 lg:px-8 py-2.5 overflow-x-auto">
      <div className="max-w-6xl mx-auto flex items-center justify-between min-w-[640px] space-x-2">
        {STEPS.map((step, idx) => {
          const isCurrent = step.id === currentStep;
          const isPassed = idx < currentIndex;
          const isClickable = allowedSteps.has(step.id);
          const Icon = step.icon;

          return (
            <React.Fragment key={step.id}>
              <button
                type="button"
                disabled={!isClickable}
                onClick={() => isClickable && onStepClick?.(step.id)}
                className={`flex items-center space-x-2.5 px-3 py-1.5 rounded-md transition-all text-left group ${
                  isCurrent
                    ? 'bg-canvas border border-teal-brand text-text-primary'
                    : isPassed
                    ? 'bg-transparent text-text-secondary hover:text-text-primary cursor-pointer'
                    : 'bg-transparent text-text-muted cursor-not-allowed opacity-60'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded flex items-center justify-center font-mono text-xs font-semibold border ${
                    isCurrent
                      ? 'bg-teal-brand/10 border-teal-brand text-teal-brand'
                      : isPassed
                      ? 'bg-teal-brand/20 border-teal-brand/40 text-teal-brand'
                      : 'bg-canvas border-border text-text-muted'
                  }`}
                >
                  {isPassed ? <Check className="w-3.5 h-3.5" /> : idx + 1}
                </div>

                <div className="flex flex-col">
                  <div className="flex items-center space-x-1.5">
                    <Icon
                      className={`w-3.5 h-3.5 ${
                        isCurrent
                          ? 'text-teal-brand'
                          : isPassed
                          ? 'text-teal-brand/70'
                          : 'text-text-muted'
                      }`}
                    />
                    <span
                      className={`text-xs font-medium tracking-tight ${
                        isCurrent ? 'text-text-primary' : 'text-text-secondary'
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  <span className="text-[10px] text-text-muted font-mono hidden sm:inline">
                    {step.sub}
                  </span>
                </div>
              </button>

              {idx < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-[1px] mx-2 ${
                    idx < currentIndex ? 'bg-teal-brand/40' : 'bg-border'
                  }`}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </nav>
  );
};
