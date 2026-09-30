import React, { useEffect, useState } from 'react';
import { ReportResponse } from '../../types';
import { downloadRiskReportPdf } from '../../services/api';
import {
  Download,
  FileDown,
  RotateCcw,
  ShieldAlert,
  CheckCircle,
  FileJson,
  Code,
  Copy,
  Check,
  X,
} from 'lucide-react';
import { motion } from 'framer-motion';

interface Screen5ReportProps {
  originalFile: File;
  reportData: ReportResponse;
  redactedBlob: Blob | null;
  onReset: () => void;
}

export const Screen5Report: React.FC<Screen5ReportProps> = ({
  originalFile,
  reportData,
  redactedBlob,
  onReset,
}) => {
  const [downloadingPdf, setDownloadingPdf] = useState<boolean>(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [showJsonModal, setShowJsonModal] = useState<boolean>(false);
  const [copiedJson, setCopiedJson] = useState<boolean>(false);

  const handleDownloadJson = () => {
    const jsonStr = JSON.stringify(reportData, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SentinelDoc_Audit_${originalFile.name}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(reportData, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  // Animate the risk score number count-up
  const [displayScore, setDisplayScore] = useState<number>(0);

  useEffect(() => {
    let start = 0;
    const end = reportData.risk_score;
    if (end === 0) {
      setDisplayScore(0);
      return;
    }
    const duration = 1200; // 1.2s
    const startTime = performance.now();

    const frame = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / duration);
      // easeOutExpo
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = Math.round(start + (end - start) * eased);
      setDisplayScore(current);

      if (progress < 1) {
        requestAnimationFrame(frame);
      }
    };

    const animId = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(animId);
  }, [reportData.risk_score]);

  const getRiskColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'high':
        return {
          stroke: '#EF4444',
          bg: 'bg-crimson-brand/10',
          border: 'border-crimson-brand/30',
          text: 'text-crimson-brand',
          badge: 'bg-crimson-brand/15 text-crimson-brand border-crimson-brand/40',
        };
      case 'medium':
        return {
          stroke: '#F5A524',
          bg: 'bg-amber-brand/10',
          border: 'border-amber-brand/30',
          text: 'text-amber-brand',
          badge: 'bg-amber-brand/15 text-amber-brand border-amber-brand/40',
        };
      case 'low':
      default:
        return {
          stroke: '#2DD4BF',
          bg: 'bg-teal-brand/10',
          border: 'border-teal-brand/30',
          text: 'text-teal-brand',
          badge: 'bg-teal-brand/15 text-teal-brand border-teal-brand/40',
        };
    }
  };

  const riskTheme = getRiskColor(reportData.risk_level);

  // SVG Radial calculation
  const radius = 68;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (reportData.risk_score / 100) * circumference;

  // Handler: Download Redacted File
  const handleDownloadRedacted = () => {
    if (!redactedBlob) return;
    const url = URL.createObjectURL(redactedBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `redacted_${originalFile.name}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Handler: Download Official Risk Report PDF
  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    setDownloadError(null);
    try {
      const pdfBlob = await downloadRiskReportPdf(originalFile);
      const url = URL.createObjectURL(pdfBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `SentinelDoc_Risk_Report_${originalFile.name}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to download PDF report';
      setDownloadError(msg);
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-semibold tracking-tight text-text-primary">
              Executive Compliance & Risk Audit
            </h2>
            <span className={`px-2 py-0.5 rounded text-xs font-mono font-semibold uppercase border ${riskTheme.badge}`}>
              {reportData.risk_level} RISK LEVEL
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Official compliance evaluation for{' '}
            <span className="font-mono text-text-primary">{reportData.file_name}</span>. Generated via
            SentinelDoc Risk Engine.
          </p>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="self-start sm:self-center px-3 py-1.5 rounded-md bg-surface border border-border hover:border-border-focus text-xs font-mono text-text-secondary hover:text-text-primary transition-colors flex items-center space-x-1.5"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Scan Another Document</span>
        </button>
      </div>

      {/* Main Grid: Radial Gauge & Executive Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 my-6">
        {/* Left Column: Animated Radial SVG Risk Score Gauge */}
        <div className="lg:col-span-4 rounded-md bg-surface border border-border p-6 flex flex-col items-center justify-center text-center">
          <div className="text-xs font-mono uppercase text-text-muted tracking-wider mb-4">
            Composite Privacy Hazard Index
          </div>

          <div className="relative w-44 h-44 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 160 160">
              {/* Background track circle */}
              <circle
                cx="80"
                cy="80"
                r={radius}
                className="stroke-canvas"
                strokeWidth="12"
                fill="none"
              />
              {/* Animated Progress Circle */}
              <motion.circle
                cx="80"
                cy="80"
                r={radius}
                stroke={riskTheme.stroke}
                strokeWidth="12"
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset }}
                transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
                strokeLinecap="round"
                fill="none"
              />
            </svg>

            {/* Score Center Label */}
            <div className="absolute flex flex-col items-center justify-center">
              <span className={`text-4xl font-mono font-bold tracking-tight font-mono-data ${riskTheme.text}`}>
                {displayScore}
              </span>
              <span className="text-[11px] font-mono text-text-muted mt-0.5 uppercase tracking-wider">
                out of 100
              </span>
            </div>
          </div>

          <div className="mt-4">
            <span className={`inline-block px-3 py-1 rounded text-xs font-mono font-semibold uppercase border ${riskTheme.badge}`}>
              {reportData.risk_level} Risk Category
            </span>
            <p className="text-[11px] text-text-muted mt-2 font-mono max-w-xs">
              Normalized score based on statutory exposure weights and sub-linear recurrence scaling.
            </p>
          </div>
        </div>

        {/* Right Column: Statutory Exposure & Threat Assessment */}
        <div className="lg:col-span-8 flex flex-col justify-between space-y-4">
          {/* Executive Verdict Box */}
          <div className={`p-4 rounded-md border ${riskTheme.bg} ${riskTheme.border}`}>
            <div className="flex items-start space-x-3">
              <ShieldAlert className={`w-5 h-5 flex-shrink-0 mt-0.5 ${riskTheme.text}`} />
              <div>
                <h4 className={`text-xs font-mono uppercase font-bold tracking-wider ${riskTheme.text}`}>
                  Compliance Assessment Verdict
                </h4>
                <p className="text-xs text-text-primary font-medium mt-1 leading-relaxed">
                  {reportData.summary.compliance_verdict}
                </p>
                <div className="text-[11px] text-text-secondary mt-1 font-mono">
                  Primary Vector: <span className="text-text-primary">{reportData.summary.primary_threat}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Severity Breakdown Counts */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
            <div className="p-3 rounded-md bg-surface border border-border">
              <div className="text-[10px] text-text-muted uppercase">Critical (Tier 1)</div>
              <div className="text-xl font-bold text-crimson-brand mt-1 font-mono-data">
                {reportData.summary.critical_count}
              </div>
              <div className="text-[10px] text-text-muted mt-0.5">Aadhaar, Cards</div>
            </div>

            <div className="p-3 rounded-md bg-surface border border-border">
              <div className="text-[10px] text-text-muted uppercase">High (Tier 2)</div>
              <div className="text-xl font-bold text-crimson-brand/90 mt-1 font-mono-data">
                {reportData.summary.high_count}
              </div>
              <div className="text-[10px] text-text-muted mt-0.5">PAN, DOB</div>
            </div>

            <div className="p-3 rounded-md bg-surface border border-border">
              <div className="text-[10px] text-text-muted uppercase">Medium (Tier 3)</div>
              <div className="text-xl font-bold text-amber-brand mt-1 font-mono-data">
                {reportData.summary.medium_count}
              </div>
              <div className="text-[10px] text-text-muted mt-0.5">Phone, Address</div>
            </div>

            <div className="p-3 rounded-md bg-surface border border-border">
              <div className="text-[10px] text-text-muted uppercase">Low (Tier 4)</div>
              <div className="text-xl font-bold text-teal-brand mt-1 font-mono-data">
                {reportData.summary.low_count}
              </div>
              <div className="text-[10px] text-text-muted mt-0.5">Email, Person</div>
            </div>
          </div>

          {/* Regulatory Mandates Checklist */}
          <div className="p-3.5 rounded-md bg-surface border border-border font-mono text-xs">
            <div className="text-[11px] uppercase text-text-muted mb-2 tracking-wider">
              Statutory Exposure Mapping
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-3.5 h-3.5 text-teal-brand" />
                <span className="text-[11px] text-text-secondary">DPDP Act 2023 (Sec 8)</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-3.5 h-3.5 text-teal-brand" />
                <span className="text-[11px] text-text-secondary">RBI Card Tokenization</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-3.5 h-3.5 text-teal-brand" />
                <span className="text-[11px] text-text-secondary">UIDAI Aadhaar Act</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Findings Breakdown Table */}
      <div className="my-6 rounded-md bg-surface border border-border overflow-hidden">
        <div className="p-3 bg-surface border-b border-border flex items-center justify-between text-xs font-mono">
          <span className="text-text-primary font-semibold tracking-wide">
            DETECTED PII INVENTORY ({reportData.total_findings} Total)
          </span>
          <span className="text-[11px] text-text-muted">
            Audited against Presidio & Mathematical Checksums
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-border bg-canvas text-text-muted text-[10px] uppercase">
                <th className="p-2.5">Entity Type</th>
                <th className="p-2.5">Detections</th>
                <th className="p-2.5">Severity Tier</th>
                <th className="p-2.5">Confidence Sample</th>
                <th className="p-2.5">Statutory Standard</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {Object.entries(reportData.findings_by_type).map(([type, count]) => {
                const sampleFinding = reportData.findings.find((f) => f.entity_type === type);
                return (
                  <tr key={type} className="hover:bg-card-hover">
                    <td className="p-2.5 font-bold text-text-primary">{type}</td>
                    <td className="p-2.5 font-mono-data text-text-primary">{count}</td>
                    <td className="p-2.5">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-canvas border border-border text-text-secondary">
                        {type === 'AADHAAR' || type === 'CREDIT_CARD'
                          ? 'Tier 1 (Critical)'
                          : type === 'PAN' || type === 'DATE_OF_BIRTH'
                          ? 'Tier 2 (High)'
                          : type === 'PHONE' || type === 'ADDRESS'
                          ? 'Tier 3 (Medium)'
                          : 'Tier 4 (Low)'}
                      </span>
                    </td>
                    <td className="p-2.5 text-teal-brand font-mono-data">
                      {sampleFinding ? `${(sampleFinding.confidence * 100).toFixed(0)}%` : 'N/A'}
                    </td>
                    <td className="p-2.5 text-text-muted text-[11px]">
                      {sampleFinding?.reasoning.split(';')[0] || 'Standard PII detection'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Dual Action Download Bar */}
      <div className="p-6 rounded-md bg-surface border border-border flex flex-col sm:flex-row items-center justify-between gap-4 mt-8">
        <div>
          <h3 className="text-sm font-semibold text-text-primary tracking-tight">
            Ready for Secure Distribution
          </h3>
          <p className="text-xs text-text-secondary mt-0.5">
            Export the sanitized document binary or generate a compliance-ready PDF audit report.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          {/* Action 1: Download Redacted File */}
          <button
            type="button"
            onClick={handleDownloadRedacted}
            disabled={!redactedBlob}
            className="flex-1 sm:flex-none px-4 py-2.5 rounded-md bg-teal-brand text-canvas hover:bg-teal-brand/90 font-medium text-xs tracking-wide transition-all flex items-center justify-center space-x-2 shadow-sm cursor-pointer disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>Download Redacted Document</span>
          </button>

          {/* Action 2: Download PDF Report */}
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="flex-1 sm:flex-none px-4 py-2.5 rounded-md bg-canvas border border-border hover:border-border-focus text-text-primary hover:text-teal-brand font-medium text-xs tracking-wide transition-all flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
          >
            <FileDown className="w-4 h-4 text-teal-brand" />
            <span>{downloadingPdf ? 'Generating PDF...' : 'Download Risk Report (PDF)'}</span>
          </button>

          {/* Action 3: Download Audit JSON */}
          <button
            type="button"
            onClick={handleDownloadJson}
            title="Download full findings and risk assessment as JSON"
            className="flex-1 sm:flex-none px-3.5 py-2.5 rounded-md bg-canvas border border-border hover:border-teal-brand/50 text-text-secondary hover:text-teal-brand font-mono text-xs tracking-wide transition-all flex items-center justify-center space-x-1.5 cursor-pointer"
          >
            <FileJson className="w-4 h-4 text-teal-brand" />
            <span>Download JSON</span>
          </button>

          {/* Action 4: View Raw JSON Toggle */}
          <button
            type="button"
            onClick={() => setShowJsonModal(!showJsonModal)}
            title="View live JSON telemetry payload"
            className={`px-3 py-2.5 rounded-md border font-mono text-xs transition-all flex items-center justify-center space-x-1.5 cursor-pointer ${
              showJsonModal
                ? 'bg-teal-brand/10 border-teal-brand text-teal-brand'
                : 'bg-canvas border-border hover:border-border-focus text-text-muted hover:text-text-primary'
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            <span>{showJsonModal ? 'Hide JSON' : 'View JSON'}</span>
          </button>
        </div>
      </div>

      {/* Interactive JSON Viewer Panel */}
      {showJsonModal && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          className="mt-6 rounded-md bg-[#0D1117] border border-border p-4 font-mono text-xs shadow-xl text-left"
        >
          <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-3">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-crimson-brand/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-brand/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-teal-brand/80" />
              <span className="text-white/60 text-[11px] ml-2 font-mono">
                {reportData.file_name} — Audit Findings Telemetry (.json)
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={handleCopyJson}
                className="px-2.5 py-1 rounded bg-white/10 hover:bg-white/20 text-white/80 hover:text-white text-[11px] flex items-center space-x-1 transition-colors"
              >
                {copiedJson ? (
                  <>
                    <Check className="w-3 h-3 text-teal-brand" />
                    <span className="text-teal-brand">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy JSON</span>
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={handleDownloadJson}
                className="px-2.5 py-1 rounded bg-teal-brand/20 hover:bg-teal-brand/30 text-teal-brand text-[11px] flex items-center space-x-1 transition-colors"
              >
                <Download className="w-3 h-3" />
                <span>Save</span>
              </button>
              <button
                type="button"
                onClick={() => setShowJsonModal(false)}
                className="p-1 text-white/50 hover:text-white transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="max-h-96 overflow-y-auto overflow-x-auto text-[11px] leading-relaxed text-teal-200/90 font-mono scrollbar-thin">
            <pre className="p-2 select-all whitespace-pre">
              {JSON.stringify(reportData, null, 2)}
            </pre>
          </div>
        </motion.div>
      )}

      {downloadError && (
        <div className="mt-3 text-xs text-crimson-brand font-mono text-right">
          {downloadError}
        </div>
      )}
    </div>
  );
};
