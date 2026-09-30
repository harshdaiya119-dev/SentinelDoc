import React, { useState, useRef, DragEvent, ChangeEvent } from 'react';
import {
  UploadCloud,
  FileText,
  FileSpreadsheet,
  FileCode,
  File as FileIcon,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  X,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  FileStack,
  Camera,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Hero3D } from './Hero3D';
import { CameraCapture } from './CameraCapture';

interface Screen1UploadProps {
  onFileSelect: (file: File) => void;
  onLaunchDemo?: () => void;
}

const SUPPORTED_EXTENSIONS = ['pdf', 'docx', 'csv', 'xlsx', 'txt'];
const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB

export const Screen1Upload: React.FC<Screen1UploadProps> = ({ onFileSelect, onLaunchDemo }) => {
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showCameraModal, setShowCameraModal] = useState<boolean>(false);
  const [showPermissionModal, setShowPermissionModal] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getFileExtension = (filename: string): string => {
    const parts = filename.split('.');
    return parts.length > 1 ? parts.pop()!.toLowerCase() : '';
  };

  const validateAndSetFile = (file: File) => {
    setErrorMessage(null);
    const ext = getFileExtension(file.name);

    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      setErrorMessage(
        `Unsupported format '.${ext}'. SentinelDoc supports: PDF, DOCX, CSV, XLSX, TXT.`
      );
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      setErrorMessage(`The selected file is empty (0 bytes). Please upload a valid document.`);
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setErrorMessage(`File size exceeds 25 MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`);
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleDrag = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleInspect = () => {
    if (selectedFile) {
      setShowPermissionModal(true);
    }
  };

  const handleAllowScan = () => {
    if (selectedFile) {
      setShowPermissionModal(false);
      onFileSelect(selectedFile);
    }
  };

  const handleCancelScan = () => {
    setShowPermissionModal(false);
  };

  // Quick preset sample generator for effortless live testing
  const loadSyntheticSample = (type: 'pdf_text' | 'csv' | 'txt') => {
    let content = '';
    let filename = '';
    let mimeType = 'text/plain';

    if (type === 'txt') {
      filename = 'employee_onboarding_audit.txt';
      content = `SENTINELDOC CONFIDENTIAL AUDIT LOG
=========================================
Candidate: Rahul Sharma
Email: rahul.sharma@example.com
Phone: +91 9876543210
Aadhaar ID: 3675 9832 4511
PAN Number: ABCDE1234F
Card on file: 4532 0150 1234 5678
Address: Flat 402, Sunrise Residency, Sector 62, Noida 201301
Date of Birth: 15-08-1988
Authorized by HR Department.
`;
      mimeType = 'text/plain';
    } else if (type === 'csv') {
      filename = 'customer_database_export.csv';
      content = `ID,CustomerName,EmailAddress,PhoneNumber,TaxIdentifier,CardNumber
1,Vikram Mehta,vikram.mehta@corp.in,+91 9823456789,BKRPK9876M,5105105105105100
2,Ananya Iyer,ananya.iyer@fintech.io,+91 9123456780,ABCDE1234F,4111111111111111
3,Suresh Nair,suresh.nair@portal.org,+91 9988776655,CKRPN5432L,4012888888881881
`;
      mimeType = 'text/csv';
    } else {
      filename = 'executive_contract_pii.txt';
      content = `EXECUTIVE NON-DISCLOSURE AND DATA PROCESSING AGREEMENT
Parties:
Provider: Priya Patel
Identity (Aadhaar): 9876 5432 1098
Income Tax PAN: ABCDE1234F
Contact: +91 9876543210
Email: priya.patel@sentinel.org
Emergency Contact: Rajesh Kumar (+91 9123456789)
Billing Address: Plot 12, Cyber City, Madhapur, Hyderabad, Telangana 500081
Financial Card: 4532 7512 3456 7890
`;
      mimeType = 'text/plain';
    }

    const blob = new Blob([content], { type: mimeType });
    const file = new File([blob], filename, { type: mimeType });
    validateAndSetFile(file);
  };

  const getFormatIcon = (ext: string) => {
    switch (ext) {
      case 'pdf':
        return <FileText className="w-5 h-5 text-teal-brand" />;
      case 'docx':
        return <FileCode className="w-5 h-5 text-text-primary" />;
      case 'csv':
      case 'xlsx':
        return <FileSpreadsheet className="w-5 h-5 text-amber-brand" />;
      case 'txt':
        return <FileIcon className="w-5 h-5 text-text-secondary" />;
      default:
        return <FileIcon className="w-5 h-5 text-text-muted" />;
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="relative min-h-[calc(100vh-140px)] flex items-center justify-center">
      <Hero3D />
      <div className="relative z-10 max-w-4xl mx-auto py-8 px-4 sm:px-6 w-full">
        {/* Hero Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-md bg-surface/90 backdrop-blur-sm border border-border text-xs font-mono text-teal-brand mb-3">
          <ShieldCheck className="w-4 h-4 text-teal-brand" />
          <span>SECURITY CONSOLE // DATA LEAK AUDITOR</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-text-primary">
          Scan Document for Personal Data Leaks
        </h1>
        <p className="text-sm text-text-secondary mt-2 max-w-xl mx-auto">
          Ingest enterprise documents across PDF, DOCX, CSV, XLSX, and TXT. Presidio NER and
          mathematical checksums detect Aadhaar, PAN, Card, and phone numbers in seconds.
        </p>

        {onLaunchDemo && (
          <div className="mt-4 flex justify-center">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onLaunchDemo();
              }}
              type="button"
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-md bg-teal-brand text-canvas hover:bg-teal-brand/90 font-medium text-xs font-mono tracking-wide shadow-md transition-all cursor-pointer"
            >
              <span>⚡ Launch Live Judge Evaluation (1-Click Demo)</span>
            </button>
          </div>
        )}
      </div>

      {/* Main Upload Dropzone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-md p-8 sm:p-12 text-center transition-all cursor-pointer bg-surface/50 hover:bg-surface/80 ${
          dragActive
            ? 'border-teal-brand bg-teal-brand/5 shadow-[0_0_24px_rgba(45,212,191,0.12)]'
            : selectedFile
            ? 'border-teal-brand/60 bg-surface'
            : 'border-border hover:border-border-focus'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.csv,.xlsx,.txt"
          onChange={handleChange}
          className="hidden"
          id="file-upload-input"
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div
            className={`w-14 h-14 rounded-md flex items-center justify-center border transition-colors ${
              selectedFile
                ? 'bg-teal-brand/10 border-teal-brand/40 text-teal-brand'
                : 'bg-canvas border-border text-text-muted group-hover:text-text-primary'
            }`}
          >
            {selectedFile ? (
              <FileStack className="w-7 h-7 text-teal-brand" />
            ) : (
              <UploadCloud className="w-7 h-7 text-teal-brand" />
            )}
          </div>

          <div>
            <p className="text-base font-medium text-text-primary">
              {selectedFile ? (
                <span className="text-teal-brand font-mono">{selectedFile.name}</span>
              ) : (
                'Drop target document here, or click to browse'
              )}
            </p>
            <p className="text-xs text-text-muted mt-1 font-mono">
              Accepted Formats: PDF, DOCX, CSV, XLSX, TXT • Max size: 25 MB
            </p>
          </div>

          {/* Supported Format Pills */}
          <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
            {[
              { label: 'PDF', ext: 'pdf' },
              { label: 'DOCX', ext: 'docx' },
              { label: 'CSV', ext: 'csv' },
              { label: 'XLSX', ext: 'xlsx' },
              { label: 'TXT', ext: 'txt' },
            ].map((fmt) => (
              <span
                key={fmt.label}
                className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-canvas border border-border text-[11px] font-mono text-text-secondary"
              >
                {getFormatIcon(fmt.ext)}
                <span>.{fmt.label}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-center">
        <button
          onClick={() => setShowCameraModal(true)}
          type="button"
          className="flex items-center space-x-2 px-5 py-2.5 rounded-full border border-teal-brand/40 bg-teal-brand/10 text-teal-brand font-medium hover:bg-teal-brand hover:text-canvas transition-colors cursor-pointer group shadow-sm text-sm"
        >
          <Camera className="w-5 h-5 group-hover:scale-110 transition-transform" />
          <span>Scan Physical ID (Liveness & Authenticity)</span>
        </button>
      </div>

      {showCameraModal && (
        <CameraCapture onClose={() => setShowCameraModal(false)} />
      )}

      {/* Error Alert */}
      {errorMessage && (
        <div className="mt-4 p-3 rounded-md bg-crimson-brand/10 border border-crimson-brand/30 flex items-start space-x-2.5 text-xs text-crimson-brand">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div className="flex-1 font-mono">{errorMessage}</div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-text-muted hover:text-text-primary"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Selected File Details & Actions Card */}
      {selectedFile && (
        <div className="mt-6 p-4 rounded-md bg-surface border border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-md bg-canvas border border-border flex items-center justify-center">
              {getFormatIcon(getFileExtension(selectedFile.name))}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-sm font-medium text-text-primary truncate max-w-xs">
                  {selectedFile.name}
                </span>
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.2 rounded bg-teal-brand/10 border border-teal-brand/30 text-teal-brand">
                  {getFileExtension(selectedFile.name)}
                </span>
              </div>
              <div className="text-xs text-text-muted font-mono mt-0.5">
                Size: {formatFileSize(selectedFile.size)} • Status: Ready for ingestion
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2 w-full sm:w-auto">
            <button
              onClick={handleClear}
              type="button"
              className="px-3 py-2 rounded-md bg-canvas border border-border hover:border-border-focus text-xs font-mono text-text-secondary hover:text-text-primary transition-colors flex items-center space-x-1"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>

            <button
              onClick={handleInspect}
              type="button"
              className="flex-1 sm:flex-none px-4 py-2 rounded-md bg-teal-brand text-canvas hover:bg-teal-brand/90 font-medium text-xs tracking-wide transition-colors flex items-center justify-center space-x-1.5 shadow-sm"
            >
              <span>Inspect Document</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Quick Test Samples */}
      <div className="mt-8 pt-6 border-t border-border">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-mono uppercase text-text-muted tracking-wider">
            Quick Test Datasets (Synthetic PII)
          </span>
          <span className="text-[11px] font-mono text-text-muted">
            Pre-loaded with Aadhaar, PAN, Card, Phone & Email
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          <button
            type="button"
            onClick={() => loadSyntheticSample('txt')}
            className="p-3 rounded-md bg-surface border border-border hover:border-teal-brand/50 text-left transition-colors group"
          >
            <div className="flex items-center justify-between text-xs font-medium text-text-primary mb-1">
              <span className="flex items-center space-x-1.5">
                <FileText className="w-3.5 h-3.5 text-teal-brand" />
                <span>Employee Onboarding</span>
              </span>
              <span className="text-[10px] font-mono text-text-muted">.TXT</span>
            </div>
            <p className="text-[11px] text-text-secondary line-clamp-2">
              Contains Aadhaar (Verhoeff), PAN, Card (Luhn), Phone (+91), and residential address.
            </p>
          </button>

          <button
            type="button"
            onClick={() => loadSyntheticSample('csv')}
            className="p-3 rounded-md bg-surface border border-border hover:border-amber-brand/50 text-left transition-colors group"
          >
            <div className="flex items-center justify-between text-xs font-medium text-text-primary mb-1">
              <span className="flex items-center space-x-1.5">
                <FileSpreadsheet className="w-3.5 h-3.5 text-amber-brand" />
                <span>Customer Database</span>
              </span>
              <span className="text-[10px] font-mono text-text-muted">.CSV</span>
            </div>
            <p className="text-[11px] text-text-secondary line-clamp-2">
              Tabular customer export with credit cards, Indian PANs, phone numbers, and emails.
            </p>
          </button>

          <button
            type="button"
            onClick={() => loadSyntheticSample('pdf_text')}
            className="p-3 rounded-md bg-surface border border-border hover:border-teal-brand/50 text-left transition-colors group"
          >
            <div className="flex items-center justify-between text-xs font-medium text-text-primary mb-1">
              <span className="flex items-center space-x-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-teal-brand" />
                <span>Executive NDA Agreement</span>
              </span>
              <span className="text-[10px] font-mono text-text-muted">.TXT</span>
            </div>
            <p className="text-[11px] text-text-secondary line-clamp-2">
              Legal agreement with Aadhaar, PAN, phone, email, and billing address coordinates.
            </p>
          </button>
        </div>
      </div>

      {/* ── Sensitive Data Scan Permission Notification Modal ── */}
      <AnimatePresence>
        {showPermissionModal && selectedFile && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="w-full max-w-md bg-surface border border-amber-brand/50 rounded-xl shadow-2xl p-6 relative overflow-hidden"
            >
              {/* Glowing top accent strip */}
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-brand via-teal-brand to-amber-brand" />

              <div className="flex items-start space-x-3.5 mb-4">
                <div className="w-10 h-10 rounded-xl bg-amber-brand/10 border border-amber-brand/40 flex items-center justify-center flex-shrink-0 text-amber-brand">
                  <AlertTriangle className="w-5 h-5 animate-pulse" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-base font-bold text-text-primary font-mono tracking-tight">
                      SENSITIVE DATA WARNING
                    </h3>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-brand/10 border border-amber-brand/30 text-amber-brand font-bold uppercase">
                      PERMISSION
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary mt-1 font-sans leading-relaxed">
                    Your data is sensitive, be careful!
                  </p>
                </div>
              </div>

              {/* Target Document Details Box */}
              <div className="p-3.5 rounded-lg bg-card border border-border mb-4 text-xs font-mono space-y-2">
                <div className="flex justify-between items-center text-text-muted text-[11px] pb-2 border-b border-border/60">
                  <span>Target File:</span>
                  <span className="text-teal-brand font-bold truncate max-w-[200px]">{selectedFile.name}</span>
                </div>
                <div className="flex justify-between text-text-muted text-[11px]">
                  <span>Size:</span>
                  <span>{formatFileSize(selectedFile.size)}</span>
                </div>
                <p className="text-[11px] text-text-secondary font-sans leading-relaxed pt-1">
                  This document will be analyzed by SentinelDoc for confidential personal data (PII) such as Aadhaar, PAN, payment cards, phone numbers, and emails.
                </p>
              </div>

              <div className="flex items-center space-x-2 mb-5 text-[11px] font-mono text-text-muted">
                <ShieldAlert className="w-4 h-4 text-amber-brand flex-shrink-0" />
                <span>Grant permission to allow scanning of this sensitive document?</span>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={handleCancelScan}
                  className="px-4 py-2 rounded-lg border border-border hover:bg-canvas text-xs font-mono text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleAllowScan}
                  className="px-5 py-2 rounded-lg bg-teal-brand hover:opacity-90 text-white text-xs font-mono font-bold transition-all shadow-lg shadow-teal-brand/20 active:scale-95 flex items-center space-x-1.5 cursor-pointer"
                >
                  <ShieldCheck className="w-4 h-4" />
                  <span>Allow for now</span>
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
    </div>
  );
};
