import React from 'react';
import { Archive, ArrowRight, Clock, AlertTriangle } from 'lucide-react';

export interface Tombstone {
  id: string;
  fact_id: string;
  user_id: string;
  reason: string;
  superseded_by?: string | null;
  created_at: string;
}

export interface Fact {
  id: string;
  content: string;
  category: string;
  salience_score: number;
  valid_from: string;
  valid_until?: string | null;
  created_at: string;
  invalidated_at?: string | null;
  linked_to?: string | null;
  is_active: boolean;
}

interface AuditTrailProps {
  tombstones: Tombstone[];
  allFacts: Fact[];
  loading: boolean;
}

export const AuditTrail: React.FC<AuditTrailProps> = ({ tombstones, allFacts, loading }) => {
  const factMap = new Map(allFacts.map(f => [f.id, f]));

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 text-sm text-muted">
        <Clock className="w-4 h-4 animate-spin mr-2" />
        Loading Bi-Temporal Audit Trail...
      </div>
    );
  }

  if (tombstones.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-muted bg-background/40 rounded-xl border border-dashed border-border">
        <Archive className="w-8 h-8 mb-2 text-border" />
        <p className="text-sm font-medium">No Invalidated Facts Yet</p>
        <p className="text-xs text-muted max-w-xs mt-1">
          When preferences change or facts are contradicted, superseded entries will appear here with an immutable audit log.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-muted mb-1 px-1">
        <span>Immutable Tombstone Log ({tombstones.length})</span>
        <span className="flex items-center gap-1 text-amber-400/90">
          <AlertTriangle className="w-3.5 h-3.5" />
          Zero Data Loss
        </span>
      </div>

      {tombstones.map((t) => {
        const supersededFact = factMap.get(t.fact_id);
        const replacementFact = t.superseded_by ? factMap.get(t.superseded_by) : null;

        return (
          <div
            key={t.id}
            className="p-3.5 bg-background/80 border border-border/80 rounded-xl space-y-2 text-xs relative overflow-hidden"
          >
            {/* Red Invalidation Accent Line */}
            <div className="absolute top-0 left-0 bottom-0 w-1 bg-red-500/60" />

            <div className="flex items-center justify-between text-[11px] text-muted">
              <span className="font-mono text-red-400 uppercase tracking-wider font-semibold">
                [{t.reason}]
              </span>
              <span>{new Date(t.created_at).toLocaleString()}</span>
            </div>

            {/* Superseded (Invalidated) Content */}
            <div className="pl-1">
              <p className="text-gray-400 line-through decoration-red-400/80 decoration-2">
                {supersededFact ? supersededFact.content : `Fact ID: ${t.fact_id}`}
              </p>
            </div>

            {/* Replacement Fact Link */}
            {replacementFact && (
              <div className="mt-2 pt-2 border-t border-border/40 flex items-start gap-1.5 text-emerald-400 pl-1">
                <ArrowRight className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-[10px] uppercase font-bold text-emerald-500 block">Superseded By:</span>
                  <p className="text-gray-200 font-medium">{replacementFact.content}</p>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
