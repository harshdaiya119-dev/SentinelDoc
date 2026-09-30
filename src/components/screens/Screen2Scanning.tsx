import React, { useEffect, useState, useRef } from 'react';
import { ScanResponse } from '../../types';
import { scanDocument } from '../../services/api';
import { Activity, AlertCircle, ArrowLeft, Terminal, ShieldAlert } from 'lucide-react';
import { motion } from 'framer-motion';

interface Screen2ScanningProps {
  file: File;
  onScanComplete: (response: ScanResponse) => void;
  onBack: () => void;
}

interface LogEntry {
  id: string;
  time: string;
  type: 'SYS' | 'PARSER' | 'RECOGNIZER' | 'CHECKSUM' | 'SPATIAL' | 'SUCCESS';
  message: string;
}

const PHASES = [
  { id: 1, name: 'Structure Parsing', detail: 'Extracting text streams, paragraphs, runs & cells' },
  { id: 2, name: 'Presidio NER & Regex', detail: 'Pattern matching Aadhaar, PAN, Cards, Phone, Email' },
  { id: 3, name: 'Checksum Validation', detail: 'Verhoeff (D5) & Luhn algorithms verifying PII validity' },
  { id: 4, name: 'Spatial Coordinate Mapping', detail: 'Correlating vector bounding boxes & cell coordinates' },
  { id: 5, name: 'Severity Risk Scoring', detail: 'Compiling multi-tier regulatory risk assessment' },
];

export const Screen2Scanning: React.FC<Screen2ScanningProps> = ({
  file,
  onScanComplete,
  onBack,
}) => {
  const [currentPhase, setCurrentPhase] = useState<number>(1);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const scanPromiseRef = useRef<Promise<ScanResponse> | null>(null);

  const getTimestamp = () => {
    const now = new Date();
    return now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0');
  };

  const addLog = (
    type: 'SYS' | 'PARSER' | 'RECOGNIZER' | 'CHECKSUM' | 'SPATIAL' | 'SUCCESS',
    message: string
  ) => {
    setLogs((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
        time: getTimestamp(),
        type,
        message,
      },
    ]);
  };

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  useEffect(() => {
    let isMounted = true;

    const runTelemetry = async () => {
      addLog('SYS', `Ingesting target binary: '${file.name}' (${file.size} bytes)`);
      addLog('SYS', `Spawning SentinelDoc detection engine on port 8000`);

      // Kick off the actual API request
      const p = scanDocument(file);
      p.catch(() => {});
      scanPromiseRef.current = p;

      // Phase 1
      await new Promise((r) => setTimeout(r, 300));
      if (!isMounted) return;
      setCurrentPhase(1);
      addLog('PARSER', `Detecting container structure for .${file.name.split('.').pop()}`);
      addLog('PARSER', `Parsing layout blocks, line indexes, and coordinate grids...`);

      // Phase 2
      await new Promise((r) => setTimeout(r, 450));
      if (!isMounted) return;
      setCurrentPhase(2);
      addLog('RECOGNIZER', `Activating Microsoft Presidio NER analyzer (en_core_web_sm)`);
      addLog('RECOGNIZER', `Evaluating regex signatures: AADHAAR, PAN, CREDIT_CARD, PHONE, EMAIL`);

      // Phase 3
      await new Promise((r) => setTimeout(r, 450));
      if (!isMounted) return;
      setCurrentPhase(3);
      addLog('CHECKSUM', `Executing Verhoeff D5 dihedral group permutations for 12-digit Aadhaar candidates`);
      addLog('CHECKSUM', `Executing Luhn mod-10 double-add-double algorithm on credit card candidates`);

      // Phase 4
      await new Promise((r) => setTimeout(r, 400));
      if (!isMounted) return;
      setCurrentPhase(4);
      addLog('SPATIAL', `Correlating detected candidate spans with page bounding box coordinates`);
      addLog('SPATIAL', `Validating layout bounds and non-destructive overlay rectangles`);

      // Phase 5: Await API completion
      try {
        const response = await scanPromiseRef.current;
        if (!isMounted) return;

        setCurrentPhase(5);
        addLog(
          'SUCCESS',
          `Scan completed successfully! ${response.total_findings} personal data candidate(s) flagged.`
        );

        response.findings.forEach((f, idx) => {
          if (idx < 5) {
            addLog(
              'RECOGNIZER',
              `[MATCH] ${f.entity_type} (conf: ${(f.confidence * 100).toFixed(0)}%) -> "${f.matched_text}"`
            );
          }
        });
        if (response.findings.length > 5) {
          addLog('RECOGNIZER', `... and ${response.findings.length - 5} additional findings mapped.`);
        }

        // Smooth transition to screen 3
        await new Promise((r) => setTimeout(r, 600));
        if (isMounted) {
          onScanComplete(response);
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : 'Unknown scanning error occurred';
        setError(msg);
        addLog('SYS', `[ERROR] Ingestion aborted: ${msg}`);
      }
    };

    runTelemetry();

    return () => {
      isMounted = false;
    };
  }, [file]);

  const getLogBadgeColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'SYS':
        return 'text-text-muted';
      case 'PARSER':
        return 'text-amber-brand';
      case 'RECOGNIZER':
        return 'text-teal-brand';
      case 'CHECKSUM':
        return 'text-teal-brand font-semibold';
      case 'SPATIAL':
        return 'text-text-primary';
      case 'SUCCESS':
        return 'text-teal-brand font-semibold';
      default:
        return 'text-text-secondary';
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6">
      {/* Top Banner */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Activity className="w-5 h-5 text-teal-brand animate-pulse" />
          <h2 className="text-lg font-semibold tracking-tight text-text-primary">
            Real-Time Analysis Telemetry
          </h2>
        </div>
        <div className="font-mono text-xs text-text-muted">
          TARGET: <span className="text-text-primary font-semibold">{file.name}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Visual Scan Beam & Multi-Phase Pipeline */}
        <div className="lg:col-span-5 space-y-4">
          {/* Wireframe Scanner with Sweeping Beam */}
          <div className="relative h-48 rounded-md bg-canvas border border-border overflow-hidden flex flex-col items-center justify-center p-4">
            {/* Background grid lines */}
            <div
              className="absolute inset-0 opacity-10"
              style={{
                backgroundImage:
                  'linear-gradient(#2DD4BF 1px, transparent 1px), linear-gradient(90deg, #2DD4BF 1px, transparent 1px)',
                backgroundSize: '20px 20px',
              }}
            />

            {/* Document silhouette */}
            <div className="relative z-10 w-28 h-36 bg-surface border border-border rounded p-2.5 flex flex-col justify-between shadow-lg">
              <div className="space-y-1.5">
                <div className="w-12 h-1.5 bg-border rounded" />
                <div className="w-20 h-1 bg-border/60 rounded" />
                <div className="w-16 h-1 bg-border/60 rounded" />
                <div className="w-18 h-1 bg-teal-brand/40 rounded animate-pulse" />
              </div>
              <div className="space-y-1.5">
                <div className="w-14 h-1 bg-amber-brand/40 rounded animate-pulse" />
                <div className="w-10 h-1 bg-border/60 rounded" />
                <div className="w-16 h-1 bg-crimson-brand/40 rounded animate-pulse" />
              </div>
              <div className="flex justify-between items-center text-[8px] font-mono text-text-muted">
                <span>SEC-DOC</span>
                <ShieldAlert className="w-3 h-3 text-teal-brand" />
              </div>
            </div>

            {/* Animated Laser Beam */}
            {!error && (
              <>
                <motion.div
                  className="absolute left-0 right-0 h-0.5 bg-teal-brand shadow-[0_0_12px_#2DD4BF,0_0_24px_#2DD4BF] z-20"
                  animate={{
                    top: ['15%', '85%', '15%'],
                  }}
                  transition={{
                    duration: 2.2,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                />
                
                {/* Scan Particles */}
                {Array.from({ length: 15 }).map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute w-1 h-1 bg-teal-brand rounded-full z-10 shadow-[0_0_5px_#2DD4BF]"
                    initial={{
                      x: Math.random() * 200 - 100,
                      y: Math.random() * 150 - 75,
                      opacity: 0,
                      scale: 0
                    }}
                    animate={{
                      y: [null, Math.random() * 200 - 100],
                      opacity: [0, 0.8, 0],
                      scale: [0, Math.random() * 1.5 + 0.5, 0]
                    }}
                    transition={{
                      duration: Math.random() * 1.5 + 0.5,
                      repeat: Infinity,
                      ease: 'linear',
                      delay: Math.random() * 2
                    }}
                  />
                ))}
              </>
            )}

            <div className="relative z-10 mt-2 font-mono text-[11px] text-text-muted">
              {error ? (
                <span className="text-crimson-brand font-medium">SCAN ABORTED</span>
              ) : (
                <span className="text-teal-brand">ENGINE ACTIVE // INGESTION IN PROGRESS</span>
              )}
            </div>
          </div>

          {/* Pipeline Tracker */}
          <div className="p-4 rounded-md bg-surface border border-border space-y-3">
            <div className="text-xs font-mono uppercase text-text-muted tracking-wider">
              Pipeline Checkpoints
            </div>
            <div className="space-y-2.5">
              {PHASES.map((phase) => {
                const isComplete = currentPhase > phase.id;
                const isActive = currentPhase === phase.id && !error;
                return (
                  <div key={phase.id} className="flex items-start space-x-2.5 text-xs">
                    <div
                      className={`w-4 h-4 rounded-full mt-0.5 flex-shrink-0 flex items-center justify-center font-mono text-[9px] border ${
                        isComplete
                          ? 'bg-teal-brand border-teal-brand text-canvas font-bold'
                          : isActive
                          ? 'bg-teal-brand/10 border-teal-brand text-teal-brand animate-pulse'
                          : 'bg-canvas border-border text-text-muted'
                      }`}
                    >
                      {phase.id}
                    </div>
                    <div>
                      <div
                        className={`font-medium ${
                          isActive
                            ? 'text-teal-brand'
                            : isComplete
                            ? 'text-text-primary'
                            : 'text-text-muted'
                        }`}
                      >
                        {phase.name}
                      </div>
                      <div className="text-[11px] text-text-muted font-mono">{phase.detail}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Streaming Terminal Log */}
        <div className="lg:col-span-7 flex flex-col">
          <div className="p-4 rounded-md bg-canvas border border-border flex-1 flex flex-col font-mono text-xs min-h-[380px] max-h-[480px]">
            {/* Terminal Header */}
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-border">
              <div className="flex items-center space-x-2 text-text-secondary">
                <Terminal className="w-4 h-4 text-teal-brand" />
                <span className="font-semibold text-text-primary tracking-wide">
                  sentineldoc@engine: ~/logs/scan.stream
                </span>
              </div>
              <span className="text-[10px] text-teal-brand uppercase tracking-wider font-mono">
                {error ? 'ERR_HALTED' : 'LIVE'}
              </span>
            </div>

            {/* Terminal Output */}
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-2 font-mono-data">
              {logs.map((log) => (
                <div key={log.id} className="leading-relaxed flex items-start space-x-2">
                  <span className="text-text-muted select-none text-[11px] flex-shrink-0">
                    [{log.time}]
                  </span>
                  <span
                    className={`text-[10px] px-1 rounded bg-surface border border-border select-none flex-shrink-0 ${getLogBadgeColor(
                      log.type
                    )}`}
                  >
                    {log.type}
                  </span>
                  <span className="text-text-primary break-all">{log.message}</span>
                </div>
              ))}
              <div ref={terminalEndRef} />
            </div>

            {/* Error Message & Retry */}
            {error && (
              <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
                <div className="flex items-center space-x-2 text-crimson-brand">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span className="text-xs">{error}</span>
                </div>
                <button
                  type="button"
                  onClick={onBack}
                  className="px-3 py-1 rounded bg-surface border border-border hover:border-border-focus text-text-primary text-xs flex items-center space-x-1"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Return to Upload</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
