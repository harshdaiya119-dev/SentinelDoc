import React, { useState } from 'react';
import { Finding, ScanResponse, getEntitySeverity } from '../../types';
import {
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  CheckSquare,
  Square,
  ArrowRight,
  ArrowLeft,
  Eye,
  EyeOff,
  SlidersHorizontal,
  Info,
  FileJson,
} from 'lucide-react';

interface Screen3FindingsProps {
  scanResult: ScanResponse;
  selectedFindingIds: Set<string>;
  onToggleFinding: (id: string) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onInvertSelection: () => void;
  onProceedToRedact: () => void;
  onBack: () => void;
  isRedacting: boolean;
}

export const Screen3Findings: React.FC<Screen3FindingsProps> = ({
  scanResult,
  selectedFindingIds,
  onToggleFinding,
  onSelectAll,
  onDeselectAll,
  onInvertSelection,
  onProceedToRedact,
  onBack,
  isRedacting,
}) => {
  // Group findings by entity type
  const groupedFindings = React.useMemo(() => {
    const map = new Map<string, Finding[]>();
    for (const finding of scanResult.findings) {
      const list = map.get(finding.entity_type) || [];
      list.push(finding);
      map.set(finding.entity_type, list);
    }
    return map;
  }, [scanResult.findings]);

  // Collapsed / Expanded state per entity type (all open by default)
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    for (const type of groupedFindings.keys()) {
      initial[type] = true;
    }
    return initial;
  });

  // Mask / Unmask peek per finding ID
  const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set());

  const toggleGroup = (type: string) => {
    setOpenGroups((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  const toggleReveal = (id: string) => {
    setRevealedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const maskSnippet = (text: string, type: string): string => {
    if (text.length <= 4) return '****';
    const t = type.toUpperCase();
    if (t === 'AADHAAR') {
      const digits = text.replace(/\s+/g, '');
      if (digits.length === 12) {
        return `XXXX XXXX ${digits.slice(8)}`;
      }
    }
    if (t === 'CREDIT_CARD') {
      const clean = text.replace(/[\s-]+/g, '');
      if (clean.length >= 12) {
        return `**** **** **** ${clean.slice(-4)}`;
      }
    }
    if (t === 'PAN') {
      return `${text.slice(0, 2)}***${text.slice(-2)}`;
    }
    if (t === 'PHONE') {
      return `+91 ***** **${text.slice(-3)}`;
    }
    if (t === 'EMAIL') {
      const [user, domain] = text.split('@');
      if (user && domain) {
        return `${user.slice(0, 2)}***@${domain}`;
      }
    }
    return `${text.slice(0, 2)}${'*'.repeat(Math.min(text.length - 4, 8))}${text.slice(-2)}`;
  };

  const formatLocation = (loc: Finding['location']): string => {
    if (!loc) return 'Unknown Position';
    const parts: string[] = [];
    if (loc.page != null) parts.push(`Page ${loc.page}`);
    if (loc.paragraph_index != null) parts.push(`Paragraph ${loc.paragraph_index + 1}`);
    if (loc.sheet_name) parts.push(`Sheet '${loc.sheet_name}'`);
    if (loc.cell) parts.push(`Cell ${loc.cell}`);
    if (loc.line != null) parts.push(`Line ${loc.line}`);
    if (loc.bbox) {
      parts.push(`Box [${Math.round(loc.bbox.x0)}, ${Math.round(loc.bbox.top)}]`);
    }
    return parts.length > 0 ? parts.join(' • ') : 'Body stream';
  };

  const getSeverityBadge = (type: string) => {
    const sev = getEntitySeverity(type);
    switch (sev) {
      case 'CRITICAL':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-crimson-brand/10 border border-crimson-brand/30 text-crimson-brand font-semibold">
            Critical Severity
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-crimson-brand/10 border border-crimson-brand/30 text-crimson-brand">
            High Severity
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-amber-brand/10 border border-amber-brand/30 text-amber-brand">
            Medium Severity
          </span>
        );
      case 'LOW':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-teal-brand/10 border border-teal-brand/30 text-teal-brand">
            Low Severity
          </span>
        );
    }
  };

  const selectedCount = selectedFindingIds.size;
  const totalCount = scanResult.findings.length;

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6">
      {/* Header and Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-semibold tracking-tight text-text-primary">
              Personal Data Findings Review
            </h2>
            <span className="px-2 py-0.5 rounded-md bg-canvas border border-border text-xs font-mono font-semibold text-teal-brand">
              {totalCount} DETECTIONS
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Target file: <span className="font-mono text-text-primary">{scanResult.file_name}</span>.
            Review flagged entities, inspect reasoning, and customize selective redactions.
          </p>
        </div>

        {/* Selection Status Counter */}
        <div className="flex items-center space-x-3 self-end sm:self-center">
          <div className="text-right">
            <div className="text-xs font-mono font-medium text-text-primary">
              <span className="text-teal-brand font-bold">{selectedCount}</span> of{' '}
              <span className="font-bold">{totalCount}</span> selected
            </div>
            <div className="text-[10px] text-text-muted font-mono">
              Selective Masking Enabled
            </div>
          </div>
        </div>
      </div>

      {/* Batch Actions Bar */}
      <div className="my-4 p-3 rounded-md bg-surface border border-border flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
        <div className="flex items-center space-x-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-text-muted" />
          <span className="text-text-muted uppercase text-[11px]">Batch Controls:</span>
          <button
            type="button"
            onClick={onSelectAll}
            className="px-2.5 py-1 rounded bg-canvas border border-border hover:border-teal-brand/40 text-text-primary transition-colors hover:text-teal-brand"
          >
            Select All
          </button>
          <button
            type="button"
            onClick={onDeselectAll}
            className="px-2.5 py-1 rounded bg-canvas border border-border hover:border-border-focus text-text-muted hover:text-text-primary transition-colors"
          >
            Deselect All
          </button>
          <button
            type="button"
            onClick={onInvertSelection}
            className="px-2.5 py-1 rounded bg-canvas border border-border hover:border-border-focus text-text-secondary hover:text-text-primary transition-colors"
          >
            Invert
          </button>
          <button
            type="button"
            onClick={() => {
              const jsonStr = JSON.stringify(scanResult, null, 2);
              const blob = new Blob([jsonStr], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `SentinelDoc_Scan_${scanResult.file_name}.json`;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
            }}
            title="Download full findings payload in JSON format"
            className="px-2.5 py-1 rounded bg-canvas border border-border hover:border-teal-brand/40 text-text-secondary hover:text-teal-brand transition-colors flex items-center space-x-1 cursor-pointer"
          >
            <FileJson className="w-3.5 h-3.5 text-teal-brand" />
            <span>Export JSON</span>
          </button>
        </div>

        <div className="text-[11px] text-text-muted">
          Only checked findings will be masked in the redacted output.
        </div>
      </div>

      {/* Zero Findings State */}
      {totalCount === 0 && (
        <div className="p-8 text-center rounded-md bg-surface border border-border my-6">
          <ShieldAlert className="w-10 h-10 text-teal-brand mx-auto mb-3" />
          <h3 className="text-base font-semibold text-text-primary">No Personal Data Flagged</h3>
          <p className="text-xs text-text-secondary mt-1 max-w-md mx-auto">
            SentinelDoc scanned this document using Presidio NER and checksum algorithms, but found
            no high-risk PII candidates matching Aadhaar, PAN, Credit Card, phone, or email patterns.
          </p>
          <button
            type="button"
            onClick={onBack}
            className="mt-4 px-4 py-2 rounded-md bg-canvas border border-border hover:border-border-focus text-xs font-mono text-text-primary"
          >
            Upload Another Document
          </button>
        </div>
      )}

      {/* Grouped Accordions */}
      <div className="space-y-4 my-6">
        {Array.from(groupedFindings.entries()).map(([entityType, findings]) => {
          const isOpen = openGroups[entityType] ?? true;
          const groupSelectedCount = findings.filter((f) =>
            selectedFindingIds.has(f.id)
          ).length;
          const allGroupSelected = groupSelectedCount === findings.length;

          const toggleGroupSelection = () => {
            if (allGroupSelected) {
              // Deselect all in group
              findings.forEach((f) => {
                if (selectedFindingIds.has(f.id)) onToggleFinding(f.id);
              });
            } else {
              // Select all in group
              findings.forEach((f) => {
                if (!selectedFindingIds.has(f.id)) onToggleFinding(f.id);
              });
            }
          };

          return (
            <div
              key={entityType}
              className="rounded-md bg-surface border border-border overflow-hidden"
            >
              {/* Accordion Header */}
              <div className="p-3.5 bg-surface hover:bg-card-hover transition-colors flex items-center justify-between border-b border-border">
                <div className="flex items-center space-x-3">
                  <button
                    type="button"
                    onClick={toggleGroupSelection}
                    className="text-text-muted hover:text-teal-brand transition-colors"
                    title={allGroupSelected ? 'Deselect entire group' : 'Select entire group'}
                  >
                    {allGroupSelected ? (
                      <CheckSquare className="w-4 h-4 text-teal-brand" />
                    ) : groupSelectedCount > 0 ? (
                      <div className="w-4 h-4 rounded border border-teal-brand/60 bg-teal-brand/20 flex items-center justify-center">
                        <div className="w-2 h-0.5 bg-teal-brand" />
                      </div>
                    ) : (
                      <Square className="w-4 h-4 text-border-focus" />
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleGroup(entityType)}
                    className="flex items-center space-x-2 text-left"
                  >
                    {isOpen ? (
                      <ChevronDown className="w-4 h-4 text-text-muted" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-text-muted" />
                    )}
                    <span className="font-mono text-sm font-semibold text-text-primary tracking-tight">
                      {entityType}
                    </span>
                    <span className="text-xs font-mono text-text-muted">
                      ({groupSelectedCount}/{findings.length})
                    </span>
                  </button>

                  {getSeverityBadge(entityType)}
                </div>

                <div className="text-xs font-mono text-text-muted hidden sm:block">
                  Avg Conf:{' '}
                  <span className="text-teal-brand font-bold font-mono-data">
                    {(
                      (findings.reduce((acc, f) => acc + f.confidence, 0) / findings.length) *
                      100
                    ).toFixed(0)}
                    %
                  </span>
                </div>
              </div>

              {/* Accordion Content */}
              {isOpen && (
                <div className="divide-y divide-border/60">
                  {findings.map((f) => {
                    const isSelected = selectedFindingIds.has(f.id);
                    const isRevealed = revealedIds.has(f.id);

                    return (
                      <div
                        key={f.id}
                        className={`p-3 sm:px-4 sm:py-3 transition-colors ${
                          isSelected ? 'bg-canvas/40' : 'bg-canvas/80 opacity-60'
                        }`}
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                          <div className="flex items-start space-x-3">
                            <button
                              type="button"
                              onClick={() => onToggleFinding(f.id)}
                              className="mt-0.5 text-text-muted hover:text-teal-brand transition-colors"
                            >
                              {isSelected ? (
                                <CheckSquare className="w-4 h-4 text-teal-brand" />
                              ) : (
                                <Square className="w-4 h-4 text-border-focus" />
                              )}
                            </button>

                            <div>
                              <div className="flex items-center space-x-2">
                                <span className="font-mono text-xs font-semibold text-text-primary">
                                  {isRevealed ? f.matched_text : maskSnippet(f.matched_text, f.entity_type)}
                                </span>
                                <button
                                  type="button"
                                  onClick={() => toggleReveal(f.id)}
                                  className="text-text-muted hover:text-text-primary"
                                  title={isRevealed ? 'Hide raw PII' : 'Reveal unmasked snippet'}
                                >
                                  {isRevealed ? (
                                    <EyeOff className="w-3.5 h-3.5" />
                                  ) : (
                                    <Eye className="w-3.5 h-3.5" />
                                  )}
                                </button>
                                <span className="text-[10px] font-mono text-text-muted">
                                  [{f.id}]
                                </span>
                              </div>

                              <div className="flex items-center space-x-2 text-[11px] text-text-muted font-mono mt-0.5">
                                <span>{formatLocation(f.location)}</span>
                              </div>

                              <div className="flex items-center space-x-1.5 text-xs text-text-secondary mt-1">
                                <Info className="w-3 h-3 text-teal-brand/70 flex-shrink-0" />
                                <span className="italic text-[11px]">{f.reasoning}</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center space-x-2 self-end sm:self-center pl-7 sm:pl-0 font-mono-data">
                            <span className="text-[11px] text-text-muted font-mono">Confidence:</span>
                            <span
                              className={`text-xs font-mono font-semibold px-2 py-0.5 rounded border ${
                                f.confidence >= 0.85
                                  ? 'bg-teal-brand/10 border-teal-brand/30 text-teal-brand'
                                  : f.confidence >= 0.6
                                  ? 'bg-amber-brand/10 border-amber-brand/30 text-amber-brand'
                                  : 'bg-surface border-border text-text-secondary'
                              }`}
                            >
                              {(f.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Navigation Footer */}
      <div className="pt-6 border-t border-border flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-2 rounded-md bg-surface border border-border hover:border-border-focus text-xs font-mono text-text-secondary hover:text-text-primary transition-colors flex items-center space-x-1.5"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Upload</span>
        </button>

        <button
          type="button"
          onClick={onProceedToRedact}
          disabled={isRedacting || totalCount === 0}
          className={`px-5 py-2.5 rounded-md font-medium text-xs tracking-wide transition-all flex items-center space-x-2 ${
            isRedacting || totalCount === 0
              ? 'bg-surface border border-border text-text-muted cursor-not-allowed'
              : 'bg-teal-brand text-canvas hover:bg-teal-brand/90 shadow-sm cursor-pointer'
          }`}
        >
          <span>
            {isRedacting ? 'Applying Selective Redactions...' : 'Proceed to Redaction Preview'}
          </span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
