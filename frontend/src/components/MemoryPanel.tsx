import React, { useState, useEffect } from 'react';
import { Database, FileText, PlusCircle, CheckCircle, AlertOctagon, History, Tag, Activity, X, Search, Sparkles } from 'lucide-react';
import { AuditTrail, Fact, Tombstone } from './AuditTrail.tsx';

interface MemorySnapshot {
  user_md: string;
  memory_md: string;
  user_md_chars: number;
  user_md_max: number;
  memory_md_chars: number;
  memory_md_max: number;
}

interface RetrievedFact {
  id: string;
  content: string;
  category: string;
  rrf_score: number;
}

interface MemoryPanelProps {
  refreshKey: number;
  userId: string;
  onClose?: () => void;
}

export const MemoryPanel: React.FC<MemoryPanelProps> = ({ refreshKey, userId, onClose }) => {
  const [activeTab, setActiveTab] = useState<'facts' | 'rag' | 'audit' | 'snapshot' | 'manage'>('facts');
  const [snapshot, setSnapshot] = useState<MemorySnapshot | null>(null);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [tombstones, setTombstones] = useState<Tombstone[]>([]);
  const [loading, setLoading] = useState(false);

  // RAG Search Sandbox State
  const [ragQuery, setRagQuery] = useState('');
  const [ragResults, setRagResults] = useState<RetrievedFact[]>([]);
  const [ragSearching, setRagSearching] = useState(false);

  // Manage Form State
  const [action, setAction] = useState<'add' | 'replace' | 'remove'>('add');
  const [target, setTarget] = useState<'USER' | 'MEMORY'>('MEMORY');
  const [content, setContent] = useState('');
  const [oldText, setOldText] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [snapRes, factsRes, tombsRes] = await Promise.all([
        fetch(`/api/v1/memory/snapshot?user_id=${encodeURIComponent(userId)}`),
        fetch(`/api/v1/facts?active_only=false&user_id=${encodeURIComponent(userId)}`),
        fetch(`/api/v1/tombstones?user_id=${encodeURIComponent(userId)}`)
      ]);

      if (snapRes.ok) setSnapshot(await snapRes.json());
      if (factsRes.ok) setFacts(await factsRes.json());
      if (tombsRes.ok) setTombstones(await tombsRes.json());
    } catch (e) {
      console.error('Failed to load memory data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [refreshKey, userId]);

  const handleRagSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!ragQuery.trim()) return;
    setRagSearching(true);
    try {
      const res = await fetch(`/api/v1/memory/retrieve?query=${encodeURIComponent(ragQuery)}&user_id=${encodeURIComponent(userId)}&limit=8`);
      if (res.ok) {
        setRagResults(await res.json());
      }
    } catch (err) {
      console.error('RAG query failed', err);
    } finally {
      setRagSearching(false);
    }
  };

  const handleManageSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);
    setSubmitting(true);

    try {
      const res = await fetch('/api/v1/memory/manage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          target,
          content: action !== 'remove' ? content : undefined,
          old_text: action !== 'add' ? oldText : undefined,
          category: 'preference',
          salience_score: 1.0,
          user_id: userId
        })
      });

      const data = await res.json();
      if (!res.ok) {
        if (data.detail && data.detail.error === 'MemoryCapacityExceeded') {
          throw new Error(data.detail.message);
        }
        throw new Error(data.detail || 'Memory operation failed');
      }

      setFormSuccess(data.message);
      setContent('');
      setOldText('');
      await fetchData();
    } catch (err: any) {
      setFormError(err.message || 'Error managing memory');
    } finally {
      setSubmitting(false);
    }
  };

  const activeFacts = facts.filter(f => f.is_active);
  const getPercentage = (chars: number, max: number) => Math.min(100, Math.round((chars / max) * 100));

  return (
    <div className="flex flex-col h-full bg-panel rounded-2xl border border-border overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="p-4 border-b border-border bg-background/50 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-100 text-sm">Memory & RAG Inspector</h3>
              <p className="text-[11px] text-muted">User Profile: <span className="text-sky-400 font-mono font-medium">{userId}</span></p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20 font-mono">
              {activeFacts.length} Active in DB
            </span>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1.5 text-muted hover:text-gray-200 hover:bg-border/50 rounded-lg transition"
                title="Close Inspector"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Character Limit Meters */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-2.5 bg-background/80 rounded-xl border border-border space-y-1.5">
            <div className="flex justify-between text-[11px]">
              <span className="text-muted font-medium">USER.md Profile</span>
              <span className="font-mono text-gray-300">
                {snapshot?.user_md_chars ?? 0} / {snapshot?.user_md_max ?? 1500}
              </span>
            </div>
            <div className="w-full h-1.5 bg-panel rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  getPercentage(snapshot?.user_md_chars ?? 0, snapshot?.user_md_max ?? 1500) > 85
                    ? 'bg-amber-500'
                    : 'bg-sky-500'
                }`}
                style={{ width: `${getPercentage(snapshot?.user_md_chars ?? 0, snapshot?.user_md_max ?? 1500)}%` }}
              />
            </div>
          </div>

          <div className="p-2.5 bg-background/80 rounded-xl border border-border space-y-1.5">
            <div className="flex justify-between text-[11px]">
              <span className="text-muted font-medium">MEMORY.md Context</span>
              <span className="font-mono text-gray-300">
                {snapshot?.memory_md_chars ?? 0} / {snapshot?.memory_md_max ?? 2200}
              </span>
            </div>
            <div className="w-full h-1.5 bg-panel rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  getPercentage(snapshot?.memory_md_chars ?? 0, snapshot?.memory_md_max ?? 2200) > 85
                    ? 'bg-amber-500'
                    : 'bg-indigo-500'
                }`}
                style={{ width: `${getPercentage(snapshot?.memory_md_chars ?? 0, snapshot?.memory_md_max ?? 2200)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-border text-xs gap-2 pt-1 overflow-x-auto">
          <button
            onClick={() => setActiveTab('facts')}
            className={`pb-2 font-medium flex items-center gap-1.5 border-b-2 whitespace-nowrap transition ${
              activeTab === 'facts' ? 'border-sky-400 text-sky-400' : 'border-transparent text-muted hover:text-gray-300'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            Facts ({activeFacts.length})
          </button>
          <button
            onClick={() => setActiveTab('rag')}
            className={`pb-2 font-medium flex items-center gap-1.5 border-b-2 whitespace-nowrap transition ${
              activeTab === 'rag' ? 'border-indigo-400 text-indigo-400' : 'border-transparent text-muted hover:text-gray-300'
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            RAG Sandbox
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`pb-2 font-medium flex items-center gap-1.5 border-b-2 whitespace-nowrap transition ${
              activeTab === 'audit' ? 'border-amber-400 text-amber-400' : 'border-transparent text-muted hover:text-gray-300'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            Tombstones ({tombstones.length})
          </button>
          <button
            onClick={() => setActiveTab('snapshot')}
            className={`pb-2 font-medium flex items-center gap-1.5 border-b-2 whitespace-nowrap transition ${
              activeTab === 'snapshot' ? 'border-sky-400 text-sky-400' : 'border-transparent text-muted hover:text-gray-300'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Markdown
          </button>
          <button
            onClick={() => setActiveTab('manage')}
            className={`pb-2 font-medium flex items-center gap-1.5 border-b-2 whitespace-nowrap transition ${
              activeTab === 'manage' ? 'border-emerald-400 text-emerald-400' : 'border-transparent text-muted hover:text-gray-300'
            }`}
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Mutate
          </button>
        </div>
      </div>

      {/* Tab Body */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Tab 1: Active Facts */}
        {activeTab === 'facts' && (
          <div className="space-y-2.5">
            {activeFacts.length === 0 ? (
              <div className="p-8 text-center text-muted text-xs">No active facts stored for {userId} yet.</div>
            ) : (
              activeFacts.map((fact) => (
                <div
                  key={fact.id}
                  className="p-3 bg-background rounded-xl border border-border/80 hover:border-border transition space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 font-medium text-[10px]">
                      <Tag className="w-3 h-3" />
                      {fact.category.toUpperCase()}
                    </span>
                    <span className="text-[10px] text-muted font-mono">
                      Salience: {(fact.salience_score * 100).toFixed(0)}%
                    </span>
                  </div>

                  <p className="text-gray-200 leading-relaxed text-xs">{fact.content}</p>

                  <div className="flex items-center justify-between text-[10px] text-muted pt-1 border-t border-border/40 font-mono">
                    <span>Valid From: {new Date(fact.valid_from).toLocaleDateString()}</span>
                    {fact.linked_to && (
                      <span className="text-emerald-400">Linked #{fact.linked_to.slice(0, 8)}</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 2: RAG Sandbox */}
        {activeTab === 'rag' && (
          <div className="space-y-3 text-xs">
            <form onSubmit={handleRagSearch} className="flex gap-2">
              <input
                type="text"
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                placeholder="Test RAG query (e.g. pet, diet, work)..."
                className="flex-1 bg-background border border-border rounded-xl px-3 py-2 text-xs text-gray-100 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="submit"
                disabled={ragSearching || !ragQuery.trim()}
                className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-xl disabled:opacity-50 transition flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Search</span>
              </button>
            </form>

            <div className="space-y-2">
              {ragResults.length === 0 ? (
                <div className="p-6 text-center text-muted text-xs bg-background/50 rounded-xl border border-border/50">
                  {ragSearching ? 'Computing Vector Cosine & BM25 RRF Fusion...' : 'Type a query above to inspect live RAG hybrid ranking.'}
                </div>
              ) : (
                ragResults.map((rf, idx) => (
                  <div key={rf.id || idx} className="p-3 bg-background rounded-xl border border-border space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        Rank #{idx + 1} • RRF Score: {rf.rrf_score.toFixed(4)}
                      </span>
                      <span className="text-[10px] text-muted uppercase font-mono">{rf.category}</span>
                    </div>
                    <p className="text-gray-200">{rf.content}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Tab 3: Audit Trail / Tombstones */}
        {activeTab === 'audit' && (
          <AuditTrail tombstones={tombstones} allFacts={facts} loading={loading} />
        )}

        {/* Tab 4: Markdown Snapshot */}
        {activeTab === 'snapshot' && (
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs font-semibold text-gray-300">USER.md Profile</span>
                <span className="text-[11px] text-muted font-mono">{snapshot?.user_md_chars ?? 0} chars</span>
              </div>
              <pre className="p-3 bg-background border border-border rounded-xl text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap font-mono">
                {snapshot?.user_md || 'No profile defined.'}
              </pre>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs font-semibold text-gray-300">MEMORY.md Context</span>
                <span className="text-[11px] text-muted font-mono">{snapshot?.memory_md_chars ?? 0} chars</span>
              </div>
              <pre className="p-3 bg-background border border-border rounded-xl text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap font-mono">
                {snapshot?.memory_md || 'No shared memories defined.'}
              </pre>
            </div>
          </div>
        )}

        {/* Tab 5: Manage Form */}
        {activeTab === 'manage' && (
          <form onSubmit={handleManageSubmit} className="space-y-3 text-xs">
            {formError && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 flex items-start gap-2">
                <AlertOctagon className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{formError}</span>
              </div>
            )}

            {formSuccess && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 flex items-start gap-2">
                <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{formSuccess}</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-muted font-medium mb-1">Action</label>
                <select
                  value={action}
                  onChange={(e: any) => setAction(e.target.value)}
                  className="w-full bg-background border border-border rounded-lg p-2 text-gray-100 focus:outline-none focus:border-sky-500"
                >
                  <option value="add">Add Fact</option>
                  <option value="replace">Replace / Invalidate</option>
                  <option value="remove">Remove (Tombstone)</option>
                </select>
              </div>

              <div>
                <label className="block text-muted font-medium mb-1">Target</label>
                <select
                  value={target}
                  onChange={(e: any) => setTarget(e.target.value)}
                  className="w-full bg-background border border-border rounded-lg p-2 text-gray-100 focus:outline-none focus:border-sky-500"
                >
                  <option value="MEMORY">MEMORY.md (2,200 chars)</option>
                  <option value="USER">USER.md (1,500 chars)</option>
                </select>
              </div>
            </div>

            {action !== 'add' && (
              <div>
                <label className="block text-muted font-medium mb-1">
                  Old Fact / Substring to Supersede <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={oldText}
                  onChange={(e) => setOldText(e.target.value)}
                  placeholder="Exact text or phrase being invalidated..."
                  className="w-full bg-background border border-border rounded-lg p-2 text-gray-100 focus:outline-none focus:border-sky-500"
                  required
                />
              </div>
            )}

            {action !== 'remove' && (
              <div>
                <label className="block text-muted font-medium mb-1">
                  New Fact Content <span className="text-sky-400">*</span>
                </label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Enter atomic declarative fact..."
                  rows={3}
                  className="w-full bg-background border border-border rounded-lg p-2 text-gray-100 focus:outline-none focus:border-sky-500 resize-none"
                  required
                />
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2 bg-sky-600 hover:bg-sky-500 text-white font-medium rounded-lg disabled:opacity-50 transition shadow-md shadow-sky-600/20"
            >
              {submitting ? 'Applying...' : 'Apply Memory Operation'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
