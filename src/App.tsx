import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { WorkflowStep, ScanResponse, ReportResponse } from './types';
import { Navbar } from './components/layout/Navbar';
import { StepIndicator } from './components/layout/StepIndicator';
import { Screen1Upload } from './components/screens/Screen1Upload';
import { Screen2Scanning } from './components/screens/Screen2Scanning';
import { Screen3Findings } from './components/screens/Screen3Findings';
import { Screen4Preview } from './components/screens/Screen4Preview';
import { Screen5Report } from './components/screens/Screen5Report';
import { LoginPage } from './components/screens/LoginPage';
import { useAuth } from './context/AuthContext';
import { redactDocument, getRiskReport } from './services/api';

export const App: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('UPLOAD');
  const [allowedSteps, setAllowedSteps] = useState<Set<WorkflowStep>>(new Set(['UPLOAD']));

  const [file, setFile] = useState<File | null>(null);
  const [scanResult, setScanResult] = useState<ScanResponse | null>(null);
  const [selectedFindingIds, setSelectedFindingIds] = useState<Set<string>>(new Set());
  const [redactedBlob, setRedactedBlob] = useState<Blob | null>(null);
  const [reportData, setReportData] = useState<ReportResponse | null>(null);
  const [isRedacting, setIsRedacting] = useState<boolean>(false);
  const [isDemoActive, setIsDemoActive] = useState<boolean>(false);

  // Step 1 -> Step 2
  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    setCurrentStep('SCANNING');
    setAllowedSteps((prev) => new Set([...prev, 'SCANNING']));
  };

  // Launch Full Demonstration with Planted PII & False-Positive Controls
  const handleLaunchDemo = () => {
    setIsDemoActive(true);
    const demoContent = `SENTINELDOC ENTERPRISE SECURITY & PII COMPLIANCE AUDIT
============================================================
CASE FILE: INC-2026-SRM-AP-PS3
CLASSIFICATION: CONFIDENTIAL // REGULATORY ASSESSMENT

1. EXECUTIVE SUBJECT PROFILE
----------------------------
Executive Name: Dr. Vikram Malhotra
Direct Contact: +91 9876543210
Official Corporate Email: vikram.malhotra@cyberdefense.in
Personal Tax Identifier (PAN): ABCDE1234F
National ID (Aadhaar UIDAI): 3675 9832 4511
Emergency Contact: Priya Sharma (+91 9123456789)
Residential Address: Flat 402, Cyber Heights, Sector 62, Noida 201301
Date of Birth: 15-08-1985

2. RECURRENT CORPORATE PAYMENT CARD
-----------------------------------
Primary Card Number: 4532 0150 1234 5678
Cardholder: VIKRAM MALHOTRA
Card Network: Visa International (Luhn Verified)

3. PLANTED FALSE-POSITIVE EXCLUSIONS (DEMONSTRATING CHECKSUM INTELLIGENCE)
--------------------------------------------------------------------------
Order Tracking ID: ORD-984213459812 (12-digit order string; fails Verhoeff algorithm)
Internal Routing Ref: REF-8877665544332211 (16-digit hardware ref; fails Luhn algorithm)
System Tracking Token: XY99ZZ88AA (10-char tracking key; rejects PAN non-tax pattern)
Postal Sector PIN: PIN 201301 (6-digit code; rejects non-mobile number)

Authorized by: Security Operations Directorate
DPDP Act 2023 §8 & RBI Cyber Framework Audit
`;
    const blob = new Blob([demoContent], { type: 'text/plain' });
    const demoFile = new File([blob], 'SENTINELDOC_JUDGE_DEMO_EVALUATION.txt', { type: 'text/plain' });
    handleFileSelect(demoFile);
  };

  // Step 2 -> Step 3
  const handleScanComplete = (response: ScanResponse) => {
    setScanResult(response);
    // By default, select all detected findings for redaction
    const allIds = new Set(response.findings.map((f) => f.id));
    setSelectedFindingIds(allIds);
    setCurrentStep('FINDINGS');
    setAllowedSteps((prev) => new Set([...prev, 'FINDINGS']));
  };

  // Step 3 Actions
  const handleToggleFinding = (id: string) => {
    setSelectedFindingIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSelectAll = () => {
    if (!scanResult) return;
    setSelectedFindingIds(new Set(scanResult.findings.map((f) => f.id)));
  };

  const handleDeselectAll = () => {
    setSelectedFindingIds(new Set());
  };

  const handleInvertSelection = () => {
    if (!scanResult) return;
    const inverted = new Set<string>();
    for (const f of scanResult.findings) {
      if (!selectedFindingIds.has(f.id)) {
        inverted.add(f.id);
      }
    }
    setSelectedFindingIds(inverted);
  };

  // Step 3 -> Step 4
  const handleProceedToRedact = async () => {
    if (!file || !scanResult) return;
    setIsRedacting(true);

    try {
      const idsArray = Array.from(selectedFindingIds);
      const blob = await redactDocument(file, idsArray);
      setRedactedBlob(blob);
      setCurrentStep('PREVIEW');
      setAllowedSteps((prev) => new Set([...prev, 'PREVIEW']));
    } catch (err) {
      alert(`Redaction failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsRedacting(false);
    }
  };

  // Step 4 -> Step 5
  const handleProceedToReport = async () => {
    if (!file) return;

    try {
      const report = await getRiskReport(file);
      setReportData(report);
      setCurrentStep('REPORT');
      setAllowedSteps((prev) => new Set([...prev, 'REPORT']));
    } catch (err) {
      alert(`Failed to generate risk report: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Reset flow
  const handleReset = () => {
    setFile(null);
    setScanResult(null);
    setSelectedFindingIds(new Set());
    setRedactedBlob(null);
    setReportData(null);
    setIsDemoActive(false);
    setCurrentStep('UPLOAD');
    setAllowedSteps(new Set(['UPLOAD']));
  };

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="min-h-screen bg-canvas text-text-primary flex flex-col selection:bg-teal-subtle selection:text-teal-brand">
      {/* Navigation Header */}
      <Navbar onLaunchDemo={handleLaunchDemo} isDemoActive={isDemoActive} />

      {/* 5-Step Workflow Tracker */}
      <StepIndicator
        currentStep={currentStep}
        onStepClick={(step) => setCurrentStep(step)}
        allowedSteps={allowedSteps}
      />

      {/* Main Content Area */}
      <main className="flex-1 relative overflow-hidden">
        <AnimatePresence mode="wait">
          {currentStep === 'UPLOAD' && (
            <motion.div key="UPLOAD" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} transition={{ duration: 0.2 }} className="h-full">
              <Screen1Upload onFileSelect={handleFileSelect} onLaunchDemo={handleLaunchDemo} />
            </motion.div>
          )}

          {currentStep === 'SCANNING' && file && (
            <motion.div key="SCANNING" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} transition={{ duration: 0.2 }} className="h-full">
              <Screen2Scanning
                file={file}
                onScanComplete={handleScanComplete}
                onBack={() => setCurrentStep('UPLOAD')}
              />
            </motion.div>
          )}

          {currentStep === 'FINDINGS' && scanResult && (
            <motion.div key="FINDINGS" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} transition={{ duration: 0.2 }} className="h-full">
              <Screen3Findings
                scanResult={scanResult}
                selectedFindingIds={selectedFindingIds}
                onToggleFinding={handleToggleFinding}
                onSelectAll={handleSelectAll}
                onDeselectAll={handleDeselectAll}
                onInvertSelection={handleInvertSelection}
                onProceedToRedact={handleProceedToRedact}
                onBack={() => setCurrentStep('UPLOAD')}
                isRedacting={isRedacting}
              />
            </motion.div>
          )}

          {currentStep === 'PREVIEW' && file && (
            <motion.div key="PREVIEW" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} transition={{ duration: 0.2 }} className="h-full">
              <Screen4Preview
                originalFile={file}
                redactedBlob={redactedBlob}
                scanResult={scanResult}
                selectedCount={selectedFindingIds.size}
                totalCount={scanResult?.total_findings || 0}
                onProceedToReport={handleProceedToReport}
                onBack={() => setCurrentStep('FINDINGS')}
              />
            </motion.div>
          )}

          {currentStep === 'REPORT' && file && reportData && (
            <motion.div key="REPORT" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} transition={{ duration: 0.2 }} className="h-full">
              <Screen5Report
                originalFile={file}
                reportData={reportData}
                redactedBlob={redactedBlob}
                onReset={handleReset}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="w-full bg-surface border-t border-border py-4 px-6 text-center text-xs text-text-muted font-mono">
        <div className="flex flex-col sm:flex-row items-center justify-between max-w-6xl mx-auto gap-2">
          <span>
            SENTINELDOC // IEEE SRM AP Hackathon — Problem Statement 3 (Cybersecurity Track)
          </span>
          <span>Presidio NER • D5 Verhoeff • Luhn Mod-10 • ReportLab Platypus</span>
        </div>
      </footer>
    </div>
  );
};
