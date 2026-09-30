import React, { useRef, useState, useCallback, useEffect } from 'react';
import Webcam from 'react-webcam';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Camera,
  X,
  CheckCircle2,
  XCircle,
  Loader2,
  ScanFace,
  ShieldAlert,
  ShieldCheck,
  Upload,
  User,
  Calendar,
  CreditCard,
  QrCode,
  Sparkles,
  Lock,
  RefreshCw,
  Award,
  Fingerprint,
  Eye,
  Hash,
  UserCheck,
  AlertTriangle,
  Radio,
  Cpu,
} from 'lucide-react';

interface VerificationCheck {
  label: string;
  passed: boolean;
}

interface VerifyIdResponse {
  is_real: boolean;
  status_category?: 'REAL_GOVT_ID' | 'GOVT_ID_NOT_FOUND' | 'FAKE_CARD' | 'NOT_FOUND' | string;
  face_found: boolean;
  qr_found: boolean;
  hologram_found?: boolean;
  message: string;
  id_type?: string | null;
  id_number?: string | null;
  name?: string | null;
  dob?: string | null;
  gender?: string | null;
  photo_base64?: string | null;
  extracted_data: Record<string, any>;
  verification_checks?: VerificationCheck[];
  authenticity_score?: number;
  pan_holder_type?: string | null;
  aadhaar_verified?: boolean;
  pan_verified?: boolean;
}

interface CameraCaptureProps {
  onClose: () => void;
}

// ── Scanning Phase Telemetry Messages ──
const SCAN_PHASES = [
  { text: 'Activating Cyber HUD & Vision Engine...', icon: Eye, duration: 600 },
  { text: 'Scanning for Human Biometrics & Face...', icon: ScanFace, duration: 800 },
  { text: 'Executing Optical Character Recognition (OCR)...', icon: Cpu, duration: 700 },
  { text: 'Evaluating Aadhaar 12-Digit Verhoeff Checksum...', icon: Hash, duration: 600 },
  { text: 'Validating PAN 10-Char Pattern & Taxpayer Class...', icon: CreditCard, duration: 500 },
  { text: 'Detecting Micro-QR Code & Hologram Foil...', icon: Sparkles, duration: 500 },
  { text: 'Computing Real vs Fake Authenticity Vector...', icon: Award, duration: 400 },
];

export const CameraCapture: React.FC<CameraCaptureProps> = ({ onClose }) => {
  const webcamRef = useRef<Webcam>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<'camera' | 'upload'>('camera');
  const [capturedImg, setCapturedImg] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [result, setResult] = useState<VerifyIdResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [scanPhase, setScanPhase] = useState(0);
  const [scanLinePos, setScanLinePos] = useState(0);

  // Animate scanning laser during verification
  useEffect(() => {
    if (!isVerifying) {
      setScanPhase(0);
      setScanLinePos(0);
      return;
    }

    // Scan line animation
    const lineInterval = setInterval(() => {
      setScanLinePos((prev) => (prev >= 100 ? 0 : prev + 2));
    }, 30);

    // Phase progression
    let phaseIdx = 0;
    setScanPhase(0);
    const advancePhase = () => {
      if (phaseIdx < SCAN_PHASES.length - 1) {
        phaseIdx++;
        setScanPhase(phaseIdx);
        setTimeout(advancePhase, SCAN_PHASES[phaseIdx].duration);
      }
    };
    const phaseTimer = setTimeout(advancePhase, SCAN_PHASES[0].duration);

    return () => {
      clearInterval(lineInterval);
      clearTimeout(phaseTimer);
    };
  }, [isVerifying]);

  const capture = useCallback(() => {
    const imageSrc = webcamRef.current?.getScreenshot();
    if (imageSrc) {
      setCapturedImg(imageSrc);
      setResult(null);
      setErrorMsg(null);
    }
  }, [webcamRef]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      if (typeof event.target?.result === 'string') {
        setCapturedImg(event.target.result);
        setResult(null);
        setErrorMsg(null);
      }
    };
    reader.readAsDataURL(file);
  };

  const retake = () => {
    setCapturedImg(null);
    setResult(null);
    setErrorMsg(null);
    setShowPermissionModal(false);
  };

  const [showPermissionModal, setShowPermissionModal] = useState<boolean>(false);

  const handleRequestVerify = () => {
    if (!capturedImg) return;
    setShowPermissionModal(true);
  };

  const handleAllowVerify = () => {
    setShowPermissionModal(false);
    executeVerifyId();
  };

  const handleCancelVerify = () => {
    setShowPermissionModal(false);
  };

  const executeVerifyId = async () => {
    if (!capturedImg) return;
    setIsVerifying(true);
    setErrorMsg(null);

    try {
      const res = await fetch(capturedImg);
      const blob = await res.blob();
      const file = new File([blob], 'id-capture.jpg', { type: 'image/jpeg' });

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/verify-id', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Verification service returned status ${response.status}`);
      }

      const data: VerifyIdResponse = await response.json();
      setResult(data);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'Error verifying ID. Ensure backend is running.');
    } finally {
      setIsVerifying(false);
    }
  };

  const score = result?.authenticity_score ?? 0;
  const checks = result?.verification_checks ?? [];
  const hasGovtNumber = Boolean(result?.id_number && result.id_number.trim().length > 0);
  // Absolute Rule: Can NEVER be a real Government ID if there is no Government ID number!
  const isReal = Boolean(result?.is_real && hasGovtNumber);
  const statusCategory = result?.status_category;

  // Determine HUD glow styling based on verdict:
  // If no ID number was extracted, it is strictly categorized as GOVT_ID_NOT_FOUND
  const isGovIdNotFound = Boolean(
    result && (!hasGovtNumber || statusCategory === 'GOVT_ID_NOT_FOUND')
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/85 backdrop-blur-md p-3 sm:p-6 overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className={`bg-surface border rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col my-auto max-h-[92vh] transition-all duration-500 ${
          result
            ? isReal
              ? 'cyber-glow-real border-teal-brand/80'
              : isGovIdNotFound
              ? 'border-amber-500/80 shadow-[0_0_25px_rgba(245,158,11,0.35)]'
              : 'cyber-glow-fake border-crimson-brand/80'
            : 'border-border'
        }`}
      >
        {/* ── Cyber HUD Header ── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface/90 backdrop-blur sticky top-0 z-10">
          <div className="flex items-center space-x-3 text-teal-brand">
            <div className="relative w-9 h-9 rounded-lg bg-teal-brand/10 border border-teal-brand/40 flex items-center justify-center overflow-hidden">
              <ScanFace className="w-5 h-5 text-teal-brand" />
              <div className="absolute top-0 left-0 w-1.5 h-1.5 border-t border-l border-teal-brand" />
              <div className="absolute top-0 right-0 w-1.5 h-1.5 border-t border-r border-teal-brand" />
              <div className="absolute bottom-0 left-0 w-1.5 h-1.5 border-b border-l border-teal-brand" />
              <div className="absolute bottom-0 right-0 w-1.5 h-1.5 border-b border-r border-teal-brand" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="font-semibold text-text-primary text-base tracking-wide font-mono">
                  CYBER ETHICAL ID VERIFICATION CAMERA
                </h2>
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-brand opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-brand"></span>
                </span>
              </div>
              <p className="text-xs text-text-muted font-mono flex items-center space-x-2">
                <span>OCR OPTICAL AUDIT</span>
                <span>•</span>
                <span>AADHAAR VERHOEFF</span>
                <span>•</span>
                <span>PAN CLASSIFICATION</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-text-muted hover:text-text-primary rounded-lg hover:bg-canvas transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* ── Mode Selector Tabs ── */}
        {!capturedImg && (
          <div className="flex border-b border-border bg-canvas/60 px-6 pt-3 gap-2">
            <button
              onClick={() => setMode('camera')}
              className={`flex items-center space-x-2 px-4 py-2 text-xs font-mono font-medium rounded-t-lg transition-colors cursor-pointer ${
                mode === 'camera'
                  ? 'bg-surface text-teal-brand border-t border-x border-border font-semibold shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <Radio className="w-3.5 h-3.5 animate-pulse text-teal-brand" />
              <span>Live Ethical Camera Feed</span>
            </button>
            <button
              onClick={() => {
                setMode('upload');
                fileInputRef.current?.click();
              }}
              className={`flex items-center space-x-2 px-4 py-2 text-xs font-mono font-medium rounded-t-lg transition-colors cursor-pointer ${
                mode === 'upload'
                  ? 'bg-surface text-teal-brand border-t border-x border-border font-semibold shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload Document Snapshot</span>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileUpload}
            />
          </div>
        )}

        {/* ── Body Content ── */}
        <div className="p-6 overflow-y-auto flex-1 flex flex-col items-center">
          {!capturedImg ? (
            /* ── Live Cyber Camera View ── */
            <div className="w-full flex flex-col items-center">
              <div className="relative w-full max-w-lg rounded-xl overflow-hidden border-2 border-teal-brand/50 bg-black aspect-video flex items-center justify-center shadow-2xl group">
                <Webcam
                  audio={false}
                  ref={webcamRef}
                  screenshotFormat="image/jpeg"
                  videoConstraints={{ facingMode: 'environment', width: 1280, height: 720 }}
                  className="w-full h-full object-cover opacity-90"
                />

                {/* Cyber Matrix Crosshair Grid Overlay */}
                <div
                  className="absolute inset-0 pointer-events-none opacity-20"
                  style={{
                    backgroundImage:
                      'linear-gradient(to right, rgba(45,212,191,0.2) 1px, transparent 1px), linear-gradient(to bottom, rgba(45,212,191,0.2) 1px, transparent 1px)',
                    backgroundSize: '30px 30px',
                  }}
                />

                {/* Cyber Crosshair Center Target */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-40">
                  <div className="w-16 h-16 border border-teal-brand/40 rounded-full flex items-center justify-center">
                    <div className="w-2 h-2 bg-teal-brand rounded-full" />
                  </div>
                </div>

                {/* Cyber ID Card Target Alignment Reticle */}
                <div className="absolute inset-x-8 inset-y-6 border border-teal-brand/60 rounded-lg pointer-events-none flex flex-col justify-between p-3 bg-teal-brand/[0.02]">
                  <div className="flex justify-between items-center text-[10px] font-mono text-teal-brand bg-black/75 px-2.5 py-1 rounded border border-teal-brand/40 backdrop-blur self-start">
                    <span className="animate-pulse">● CAM_LIVE // ALIGN AADHAAR OR PAN CARD</span>
                  </div>
                  <div className="flex justify-between items-end">
                    <div className="w-14 h-16 border border-dashed border-teal-brand/60 rounded bg-teal-brand/5 flex flex-col items-center justify-center text-[9px] font-mono text-teal-brand/90 backdrop-blur-sm">
                      <ScanFace className="w-4 h-4 mb-0.5" />
                      <span>FACE</span>
                    </div>
                    <div className="w-12 h-12 border border-dashed border-teal-brand/60 rounded bg-teal-brand/5 flex flex-col items-center justify-center text-[9px] font-mono text-teal-brand/90 backdrop-blur-sm">
                      <QrCode className="w-4 h-4 mb-0.5" />
                      <span>QR</span>
                    </div>
                  </div>
                </div>

                {/* Tactical Cyber HUD Corner Brackets */}
                <div className="absolute top-3 left-4 w-7 h-7 border-t-2 border-l-2 border-teal-brand pointer-events-none" />
                <div className="absolute top-3 right-4 w-7 h-7 border-t-2 border-r-2 border-teal-brand pointer-events-none" />
                <div className="absolute bottom-3 left-4 w-7 h-7 border-b-2 border-l-2 border-teal-brand pointer-events-none" />
                <div className="absolute bottom-3 right-4 w-7 h-7 border-b-2 border-r-2 border-teal-brand pointer-events-none" />

                {/* Cyber Telemetry Status Tags */}
                <div className="absolute top-3 right-5 flex items-center space-x-1.5 text-[9px] font-mono text-teal-brand bg-black/80 px-2 py-0.5 rounded border border-teal-brand/30">
                  <span className="w-1.5 h-1.5 bg-teal-brand rounded-full animate-ping" />
                  <span>REC • 1080P_60FPS</span>
                </div>
              </div>

              <p className="text-xs text-text-muted mt-3 font-mono text-center flex items-center justify-center space-x-2">
                <span>Hold your Aadhaar or PAN card steadily. System validates face biometrics + OCR checksums in real time.</span>
              </p>
            </div>
          ) : (
            /* ── Captured Image + Results ── */
            <div className="flex flex-col items-center w-full space-y-5">
              <div className="w-full grid grid-cols-1 md:grid-cols-12 gap-5 items-start">
                {/* Left: Captured ID with Cyber Glowing Frame */}
                <div className="md:col-span-5 flex flex-col items-center">
                  <div
                    className={`relative w-full rounded-xl overflow-hidden border shadow-lg bg-black aspect-[4/3] flex items-center justify-center transition-all duration-500 ${
                      result
                        ? isReal
                          ? 'cyber-glow-real border-teal-brand'
                          : 'cyber-glow-fake border-crimson-brand'
                        : 'border-border'
                    }`}
                  >
                    <img src={capturedImg} alt="Captured ID" className="w-full h-full object-contain" />

                    {/* Cyber Grid Pattern Background */}
                    <div
                      className="absolute inset-0 pointer-events-none opacity-10"
                      style={{
                        backgroundImage:
                          'linear-gradient(to right, rgba(45,212,191,0.3) 1px, transparent 1px), linear-gradient(to bottom, rgba(45,212,191,0.3) 1px, transparent 1px)',
                        backgroundSize: '20px 20px',
                      }}
                    />

                    {/* Cyber Scanning Laser Beam Overlay */}
                    {isVerifying && (
                      <div className="absolute inset-0 pointer-events-none">
                        <div
                          className="absolute left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-teal-brand to-transparent shadow-[0_0_15px_rgba(45,212,191,0.9)]"
                          style={{ top: `${scanLinePos}%`, transition: 'top 30ms linear' }}
                        />
                        <div className="absolute inset-0 bg-teal-brand/10 animate-pulse" />
                      </div>
                    )}

                    {/* Result Glowing Overlay Icon */}
                    {result && (
                      <div className="absolute top-2 right-2 pointer-events-none">
                        {isReal ? (
                          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-teal-brand/90 text-black text-[10px] font-mono font-bold shadow-lg">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            <span>REAL</span>
                          </span>
                        ) : isGovIdNotFound ? (
                          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-500/90 text-black text-[10px] font-mono font-bold shadow-lg">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            <span>NO ID</span>
                          </span>
                        ) : (
                          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-crimson-brand/90 text-white text-[10px] font-mono font-bold shadow-lg">
                            <ShieldAlert className="w-3.5 h-3.5" />
                            <span>FAKE</span>
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] font-mono text-text-muted mt-1.5 flex items-center space-x-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal-brand" />
                    <span>{isVerifying ? 'OCR Engine Analyzing Document...' : 'High-Res Optical Capture'}</span>
                  </span>

                  {/* Scanning Telemetry Console */}
                  {isVerifying && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="w-full mt-3 p-3 rounded-lg bg-canvas border border-teal-brand/30 shadow-md"
                    >
                      <div className="flex items-center space-x-2 mb-2">
                        <Loader2 className="w-3.5 h-3.5 text-teal-brand animate-spin" />
                        <span className="text-[10px] font-mono text-teal-brand uppercase tracking-wider font-semibold">
                          Ethical Inspection Pipeline Active
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        {SCAN_PHASES.map((phase, idx) => {
                          const PhIcon = phase.icon;
                          const isActive = idx === scanPhase;
                          const isPassed = idx < scanPhase;
                          return (
                            <div
                              key={phase.text}
                              className={`flex items-center space-x-2 text-[11px] font-mono transition-all duration-300 ${
                                isActive
                                  ? 'text-teal-brand font-semibold'
                                  : isPassed
                                  ? 'text-text-muted'
                                  : 'text-text-muted/40'
                              }`}
                            >
                              {isPassed ? (
                                <CheckCircle2 className="w-3 h-3 text-teal-brand flex-shrink-0" />
                              ) : isActive ? (
                                <PhIcon className="w-3 h-3 text-teal-brand animate-pulse flex-shrink-0" />
                              ) : (
                                <div className="w-3 h-3 rounded-full border border-border flex-shrink-0" />
                              )}
                              <span>{phase.text}</span>
                            </div>
                          );
                        })}
                      </div>
                    </motion.div>
                  )}
                </div>

                {/* Right: Verification Results with Cyber Glow & Badges */}
                <div className="md:col-span-7 flex flex-col space-y-4">
                  {/* ── Real / Fake / Not Found Verdict Banner with Cyber Glow ── */}
                  <AnimatePresence>
                    {result && (
                      <motion.div
                        initial={{ opacity: 0, x: 30 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.4, ease: 'easeOut' }}
                        className={`p-4 rounded-xl border flex items-start space-x-3.5 transition-all duration-500 ${
                          isReal
                            ? 'bg-teal-brand/10 border-teal-brand/60 text-teal-brand cyber-glow-real'
                            : isGovIdNotFound
                            ? 'bg-amber-500/10 border-amber-500/60 text-amber-500'
                            : 'bg-crimson-brand/10 border-crimson-brand/60 text-crimson-brand cyber-glow-fake'
                        }`}
                      >
                        {isReal ? (
                          <ShieldCheck className="w-6 h-6 flex-shrink-0 mt-0.5 text-teal-brand" />
                        ) : isGovIdNotFound ? (
                          <AlertTriangle className="w-6 h-6 flex-shrink-0 mt-0.5 text-amber-500" />
                        ) : (
                          <ShieldAlert className="w-6 h-6 flex-shrink-0 mt-0.5 text-crimson-brand" />
                        )}
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <h3 className="text-sm font-bold tracking-wide uppercase font-mono">
                              {isReal
                                ? 'VERIFIED REAL GOVERNMENT ID'
                                : isGovIdNotFound
                                ? 'GOVERNMENT ID NOT FOUND'
                                : 'SUSPECTED FAKE / UNVERIFIED DOCUMENT'}
                            </h3>
                            <span
                              className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                                isReal
                                  ? 'bg-teal-brand text-black'
                                  : isGovIdNotFound
                                  ? 'bg-amber-500 text-black'
                                  : 'bg-crimson-brand text-white'
                              }`}
                            >
                              {isReal ? 'REAL' : isGovIdNotFound ? 'NO ID' : 'FAKE'}
                            </span>
                          </div>
                          <p className="text-xs mt-1.5 opacity-90 leading-relaxed font-sans">{result.message}</p>
                          {isReal && (
                            <div className="flex items-center space-x-2 mt-2 pt-2 border-t border-teal-brand/30">
                              <Lock className="w-3.5 h-3.5 text-teal-brand" />
                              <span className="text-[11px] font-mono text-teal-brand font-medium">
                                Liveness Authenticated • Human Biometrics + Govt ID Match
                              </span>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* ── Authenticity Score Ring ── */}
                  <AnimatePresence>
                    {result && (
                      <motion.div
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.15 }}
                        className="p-4 rounded-xl bg-canvas/70 border border-border flex items-center space-x-5 shadow-sm"
                      >
                        {/* Circular Score */}
                        <div className="relative w-20 h-20 flex-shrink-0">
                          <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
                            <circle cx="40" cy="40" r="34" fill="none" stroke="var(--color-border)" strokeWidth="6" />
                            <circle
                              cx="40"
                              cy="40"
                              r="34"
                              fill="none"
                              stroke={
                                isReal
                                  ? 'var(--color-teal-brand)'
                                  : isGovIdNotFound
                                  ? 'var(--color-amber-brand)'
                                  : 'var(--color-crimson-brand)'
                              }
                              strokeWidth="6"
                              strokeLinecap="round"
                              strokeDasharray={`${(score / 100) * 213.6} 213.6`}
                              className="transition-all duration-1000 ease-out"
                            />
                          </svg>
                          <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <span
                              className={`text-lg font-bold font-mono ${
                                isReal
                                  ? 'text-teal-brand'
                                  : isGovIdNotFound
                                  ? 'text-amber-500'
                                  : 'text-crimson-brand'
                              }`}
                            >
                              {score}
                            </span>
                            <span className="text-[8px] font-mono text-text-muted uppercase">Score</span>
                          </div>
                        </div>

                        {/* Verification Factor Badges */}
                        <div className="flex-1">
                          <h4 className="text-[11px] font-mono text-text-muted uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                            <Fingerprint className="w-3.5 h-3.5 text-teal-brand" />
                            <span>Verification Telemetry Matrix</span>
                          </h4>
                          <div className="flex flex-wrap gap-1.5">
                            {checks.map((check, idx) => (
                              <motion.span
                                key={check.label}
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: 0.3 + idx * 0.1 }}
                                className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium border ${
                                  check.passed
                                    ? 'bg-teal-brand/10 border-teal-brand/40 text-teal-brand'
                                    : 'bg-crimson-brand/10 border-crimson-brand/40 text-crimson-brand'
                                }`}
                              >
                                {check.passed ? (
                                  <CheckCircle2 className="w-2.5 h-2.5" />
                                ) : (
                                  <XCircle className="w-2.5 h-2.5" />
                                )}
                                <span>{check.label}</span>
                              </motion.span>
                            ))}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* ── Extracted Face Portrait & Identity ── */}
                  <AnimatePresence>
                    {result && (
                      <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.4, delay: 0.25 }}
                        className="p-4 rounded-xl bg-canvas/70 border border-border flex items-center space-x-4 shadow-sm"
                      >
                        {result.photo_base64 ? (
                          <div className="relative flex-shrink-0">
                            <img
                              src={result.photo_base64}
                              alt="Extracted ID Photo"
                              className={`w-20 h-24 object-cover rounded-lg border-2 shadow-md ${
                                isReal ? 'border-teal-brand' : 'border-crimson-brand'
                              }`}
                            />
                            <div
                              className={`absolute -bottom-1.5 -right-1.5 rounded-full p-0.5 shadow ${
                                isReal ? 'bg-teal-brand text-canvas' : 'bg-crimson-brand text-white'
                              }`}
                            >
                              {isReal ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                            </div>
                          </div>
                        ) : (
                          <div className="w-20 h-24 rounded-lg border border-dashed border-border bg-surface flex flex-col items-center justify-center text-text-muted flex-shrink-0">
                            <User className="w-7 h-7 mb-1" />
                            <span className="text-[9px] font-mono">No Face</span>
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-1.5 text-xs text-teal-brand font-mono uppercase font-semibold">
                            <UserCheck className="w-3.5 h-3.5" />
                            <span>Cardholder Identity & Document Class</span>
                          </div>
                          <p className="text-sm font-bold text-text-primary mt-1 truncate">
                            {result.name || (isGovIdNotFound ? 'Human Face Identified (No ID)' : 'Name Not Detected')}
                          </p>
                          <div className="flex items-center space-x-2 mt-0.5">
                            <span className="text-xs font-mono font-bold text-text-secondary">
                              {result.id_type || (isGovIdNotFound ? 'Government ID Not Found' : 'Unclassified Document')}
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {result.qr_found && (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-teal-brand/10 border border-teal-brand/30 text-[10px] font-mono text-teal-brand">
                                <QrCode className="w-3 h-3" />
                                <span>QR Verified</span>
                              </span>
                            )}
                            {result.hologram_found && (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-brand/10 border border-amber-brand/30 text-[10px] font-mono text-amber-brand">
                                <Sparkles className="w-3 h-3" />
                                <span>Hologram Sheen</span>
                              </span>
                            )}
                            {result.aadhaar_verified && (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-teal-brand/10 border border-teal-brand/40 text-[10px] font-mono text-teal-brand font-bold">
                                <Hash className="w-3 h-3" />
                                <span>Aadhaar Verhoeff D5 Valid</span>
                              </span>
                            )}
                            {result.pan_verified && (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-teal-brand/10 border border-teal-brand/40 text-[10px] font-mono text-teal-brand font-bold">
                                <Hash className="w-3 h-3" />
                                <span>PAN Pattern Matched</span>
                              </span>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* ── Extracted Details Grid ── */}
              <AnimatePresence>
                {result && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.35 }}
                    className="w-full bg-canvas/90 border border-border rounded-xl p-5 shadow-inner"
                  >
                    <div className="flex items-center justify-between pb-3 border-b border-border mb-4">
                      <h4 className="text-xs font-mono text-text-muted uppercase tracking-wider flex items-center space-x-2">
                        <CreditCard className="w-4 h-4 text-teal-brand" />
                        <span>Extracted Government Credentials & Metadata</span>
                      </h4>
                      {result.id_type && (
                        <span className="px-2.5 py-0.5 rounded-full bg-teal-brand/10 border border-teal-brand/30 text-teal-brand text-xs font-mono font-medium">
                          {result.id_type}
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {/* ID Type */}
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.38 }}
                        className="p-3 rounded-lg bg-surface border border-border hover:border-teal-brand/30 transition-colors"
                      >
                        <div className="text-[11px] font-mono text-text-muted uppercase flex items-center space-x-1.5">
                          <Award className="w-3.5 h-3.5 text-teal-brand" />
                          <span>Government ID Type</span>
                        </div>
                        <div className="text-sm font-mono font-bold text-text-primary mt-1">
                          {result.id_type || (
                            <span className="text-crimson-brand font-medium text-xs">Government ID Not Found</span>
                          )}
                        </div>
                      </motion.div>

                      {/* ID Number */}
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="p-3 rounded-lg bg-surface border border-border hover:border-teal-brand/30 transition-colors group"
                      >
                        <div className="text-[11px] font-mono text-text-muted uppercase flex items-center space-x-1.5">
                          <CreditCard className="w-3.5 h-3.5 text-teal-brand" />
                          <span>ID Number</span>
                        </div>
                        <div className="text-sm font-mono font-bold text-text-primary mt-1 tracking-wider">
                          {result.id_number || (
                            <span className="text-text-muted font-normal italic text-xs">Not detected</span>
                          )}
                        </div>
                      </motion.div>

                      {/* Cardholder Name */}
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.45 }}
                        className="p-3 rounded-lg bg-surface border border-border hover:border-teal-brand/30 transition-colors"
                      >
                        <div className="text-[11px] font-mono text-text-muted uppercase flex items-center space-x-1.5">
                          <User className="w-3.5 h-3.5 text-teal-brand" />
                          <span>Cardholder Name</span>
                        </div>
                        <div className="text-sm font-semibold text-text-primary mt-1 truncate">
                          {result.name || (
                            <span className="text-text-muted font-normal italic text-xs">Not detected</span>
                          )}
                        </div>
                      </motion.div>

                      {/* Date of Birth */}
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="p-3 rounded-lg bg-surface border border-border hover:border-teal-brand/30 transition-colors"
                      >
                        <div className="text-[11px] font-mono text-text-muted uppercase flex items-center space-x-1.5">
                          <Calendar className="w-3.5 h-3.5 text-teal-brand" />
                          <span>Date of Birth</span>
                        </div>
                        <div className="text-sm font-mono font-medium text-text-primary mt-1">
                          {result.dob || (
                            <span className="text-text-muted font-normal italic text-xs">Not detected</span>
                          )}
                        </div>
                      </motion.div>

                      {/* Gender */}
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.55 }}
                        className="p-3 rounded-lg bg-surface border border-border hover:border-teal-brand/30 transition-colors"
                      >
                        <div className="text-[11px] font-mono text-text-muted uppercase">Gender</div>
                        <div className="text-sm font-mono font-medium text-text-primary mt-1">
                          {result.gender || (
                            <span className="text-text-muted font-normal italic text-xs">Not detected</span>
                          )}
                        </div>
                      </motion.div>

                      {/* PAN Holder Type (if PAN) */}
                      {result.pan_holder_type && (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.6 }}
                          className="p-3 rounded-lg bg-surface border border-border hover:border-teal-brand/30 transition-colors"
                        >
                          <div className="text-[11px] font-mono text-text-muted uppercase flex items-center space-x-1.5">
                            <Award className="w-3.5 h-3.5 text-teal-brand" />
                            <span>PAN Taxpayer Class</span>
                          </div>
                          <div className="text-sm font-mono font-medium text-text-primary mt-1">
                            {result.pan_holder_type}
                          </div>
                        </motion.div>
                      )}

                      {/* QR Code Status */}
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 }}
                        className="p-3 rounded-lg bg-surface border border-border hover:border-teal-brand/30 transition-colors"
                      >
                        <div className="text-[11px] font-mono text-text-muted uppercase flex items-center space-x-1.5">
                          <QrCode className="w-3.5 h-3.5 text-teal-brand" />
                          <span>Security QR Code</span>
                        </div>
                        <div className="text-xs font-mono font-medium mt-1">
                          {result.qr_found ? (
                            <span className="text-teal-brand font-semibold">Detected & Authenticated</span>
                          ) : (
                            <span className="text-text-muted">None Detected</span>
                          )}
                        </div>
                      </motion.div>

                      {/* Authenticity Verdict */}
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.65 }}
                        className="p-3 rounded-lg bg-surface border border-border hover:border-teal-brand/30 transition-colors"
                      >
                        <div className="text-[11px] font-mono text-text-muted uppercase">Final Verdict</div>
                        <div className="text-xs font-mono font-bold mt-1">
                          {isReal ? (
                            <span className="text-teal-brand">✅ REAL GOVT ID (AUTHENTIC)</span>
                          ) : isGovIdNotFound ? (
                            <span className="text-amber-500">⚠️ GOVT ID NOT FOUND (HUMAN ONLY)</span>
                          ) : (
                            <span className="text-crimson-brand">❌ FAKE / UNVERIFIED DOCUMENT</span>
                          )}
                        </div>
                      </motion.div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Error Message */}
              {errorMsg && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="w-full p-3 rounded-lg bg-crimson-brand/10 border border-crimson-brand/30 text-crimson-brand text-xs font-mono text-center"
                >
                  {errorMsg}
                </motion.div>
              )}
            </div>
          )}

          {/* ── Action Control Buttons ── */}
          <div className="mt-6 flex items-center space-x-3 w-full justify-center">
            {!capturedImg ? (
              <button
                onClick={capture}
                type="button"
                className="flex items-center space-x-2 px-6 py-2.5 rounded-full bg-teal-brand text-white font-semibold hover:opacity-90 transition-transform active:scale-95 shadow-lg shadow-teal-brand/20 cursor-pointer text-sm font-mono"
              >
                <Camera className="w-4 h-4" />
                <span>Capture ID Frame</span>
              </button>
            ) : (
              <>
                <button
                  onClick={retake}
                  disabled={isVerifying}
                  type="button"
                  className="flex items-center space-x-2 px-5 py-2 rounded-full border border-border text-text-secondary hover:text-text-primary hover:bg-canvas transition-colors disabled:opacity-50 cursor-pointer text-sm font-mono"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Scan Another</span>
                </button>

                {!result && (
                  <button
                    onClick={handleRequestVerify}
                    disabled={isVerifying}
                    type="button"
                    className="flex items-center space-x-2 px-6 py-2 rounded-full bg-teal-brand text-white font-semibold hover:opacity-90 transition-transform active:scale-95 shadow-lg shadow-teal-brand/20 disabled:opacity-70 disabled:scale-100 cursor-pointer text-sm font-mono"
                  >
                    {isVerifying ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Inspecting ID & Verifying Biometrics...</span>
                      </>
                    ) : (
                      <>
                        <ScanFace className="w-4 h-4" />
                        <span>Run Ethical Audit & Verify</span>
                      </>
                    )}
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </motion.div>

      {/* ── Sensitive Biometric Data OCR Permission Notification Modal ── */}
      <AnimatePresence>
        {showPermissionModal && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="w-full max-w-md bg-surface border border-amber-brand/60 rounded-xl shadow-2xl p-6 relative overflow-hidden text-left"
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
                      SENSITIVE BIOMETRIC DATA WARNING
                    </h3>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-brand/10 border border-amber-brand/30 text-amber-brand font-bold uppercase">
                      OCR AUDIT
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary mt-1 font-sans leading-relaxed">
                    Your data is sensitive, be careful!
                  </p>
                </div>
              </div>

              {/* Target Details Box */}
              <div className="p-3.5 rounded-lg bg-card border border-border mb-4 text-xs font-mono space-y-2">
                <div className="flex justify-between items-center text-text-muted text-[11px] pb-2 border-b border-border/60">
                  <span>Audit Engine:</span>
                  <span className="text-teal-brand font-bold">Apple Vision Neural OCR + Biometrics</span>
                </div>
                <p className="text-[11px] text-text-secondary font-sans leading-relaxed pt-1">
                  This OCR capture will scan and extract sensitive biometric face portraits, Aadhaar 12-digit UID numbers, PAN tax identifiers, and date of birth records.
                </p>
              </div>

              <div className="flex items-center space-x-2 mb-5 text-[11px] font-mono text-text-muted">
                <ShieldAlert className="w-4 h-4 text-amber-brand flex-shrink-0" />
                <span>Grant permission to allow OCR optical extraction & verification now?</span>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={handleCancelVerify}
                  className="px-4 py-2 rounded-lg border border-border hover:bg-canvas text-xs font-mono text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleAllowVerify}
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
  );
};
