import { useState, useEffect } from 'react';
import {
  Cpu,
  Plus,
  MessageSquare,
  Trash2,
  MapPin,
  Briefcase,
  Menu,
  X,
  PanelRightOpen
} from 'lucide-react';
import { Chat } from './components/Chat.tsx';
import { MemoryPanel } from './components/MemoryPanel.tsx';
import { Login } from './components/Login.tsx';

interface Profile {
  id: string;
  name: string;
  role: string;
  location: string;
  avatarBg: string;
}

const DEFAULT_PROFILES: Profile[] = [
  {
    id: 'alex_prod',
    name: 'Alex',
    role: 'Senior Distributed Systems Engineer',
    location: 'San Francisco, CA',
    avatarBg: 'from-sky-500 to-indigo-600'
  },
  {
    id: 'clara_orbital',
    name: 'Clara',
    role: 'Orbital Mechanics Researcher',
    location: 'Tokyo / Denver',
    avatarBg: 'from-purple-500 to-pink-600'
  },
  {
    id: 'maya_architect',
    name: 'Maya',
    role: 'Sustainable Architect',
    location: 'Chicago, IL',
    avatarBg: 'from-emerald-500 to-teal-600'
  }
];

interface ChatThread {
  id: string;
  title: string;
  createdAt: string;
}

export default function App() {
  // ─── Auth state (must be declared before any conditional return) ──
  const [authToken, setAuthToken] = useState<string | null>(() => {
    return localStorage.getItem('dh_auth_token');
  });
  const [authUsername, setAuthUsername] = useState<string>(() => {
    return localStorage.getItem('dh_auth_username') || '';
  });
  const [authDisplayName, setAuthDisplayName] = useState<string>(() => {
    return localStorage.getItem('dh_auth_display_name') || '';
  });

  const [profiles, setProfiles] = useState<Profile[]>(DEFAULT_PROFILES);

  const [activeProfileId, setActiveProfileId] = useState<string>(() => {
    return localStorage.getItem('active_profile_id') || 'alex_prod';
  });

  const [threads, setThreads] = useState<Record<string, ChatThread[]>>({});

  const [activeSessionId, setActiveSessionId] = useState<string>(() => {
    return localStorage.getItem('companion_active_session_id') || 'chat_main_1';
  });
  const [prefsHydrated, setPrefsHydrated] = useState(false);
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState<boolean>(false);
  const [refreshKey, setRefreshKey] = useState<number>(0);
  const [customUserModal, setCustomUserModal] = useState<boolean>(false);
  const [newUserName, setNewUserName] = useState<string>('');
  const [newUserRole, setNewUserRole] = useState<string>('');
  const [newUserLocation, setNewUserLocation] = useState<string>('');

  const handleLogin = (token: string, username: string, displayName: string) => {
    localStorage.setItem('dh_auth_token', token);
    localStorage.setItem('dh_auth_username', username);
    localStorage.setItem('dh_auth_display_name', displayName);
    setAuthToken(token);
    setAuthUsername(username);
    setAuthDisplayName(displayName);
  };

  const handleLogout = () => {
    localStorage.removeItem('dh_auth_token');
    localStorage.removeItem('dh_auth_username');
    localStorage.removeItem('dh_auth_display_name');
    setAuthToken(null);
    setAuthUsername('');
    setAuthDisplayName('');
  };

  const activeProfile = profiles.find((p) => p.id === activeProfileId) || profiles[0];
  const profileThreads = threads[activeProfile.id] || [];

  // Persist active profile
  useEffect(() => {
    localStorage.setItem('active_profile_id', activeProfileId);
    if (!prefsHydrated || !authUsername) return;
    fetch(`/api/v1/preferences?login_username=${encodeURIComponent(authUsername)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active_profile_id: activeProfileId })
    }).catch(() => {});
  }, [activeProfileId]);

  // Persist active session (local + DB cross-device)
  useEffect(() => {
    localStorage.setItem('companion_active_session_id', activeSessionId);
    if (!prefsHydrated || !authUsername) return;
    fetch(`/api/v1/preferences?login_username=${encodeURIComponent(authUsername)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active_thread_id: activeSessionId })
    }).catch(() => {});
  }, [activeSessionId]);

  // Fetch threads from DB (per profile)
  const fetchThreads = async (userId: string) => {
    try {
      const res = await fetch(`/api/v1/threads?user_id=${encodeURIComponent(userId)}`);
      if (res.ok) {
        const data = await res.json();
        const mapped: ChatThread[] = data.map((t: any) => ({
          id: t.id,
          title: t.title,
          createdAt: new Date(t.updated_at || t.created_at).toLocaleDateString()
        }));
        setThreads((prev) => ({ ...prev, [userId]: mapped }));
        // align activeSessionId if not in list
        if (mapped.length > 0 && !mapped.some((m) => m.id === activeSessionId) && userId === activeProfileId) {
          // only switch if current active belongs to this profile's fetch; defer via timeout to avoid race
          setActiveSessionId(mapped[0].id);
        }
      }
    } catch {}
  };

  useEffect(() => {
    if (activeProfileId) fetchThreads(activeProfileId);
  }, [activeProfileId]);

  // Ensure activeSessionId always belongs to the active profile
  useEffect(() => {
    const list = threads[activeProfileId];
    if (list && list.length > 0 && !list.some((t) => t.id === activeSessionId)) {
      setActiveSessionId(list[0].id);
    }
  }, [activeProfileId]); // only on profile change

  // Fetch profiles from DB (persists across devices)
  useEffect(() => {
    if (!authToken) return;
    fetch('/api/v1/profiles')
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          const mapped: Profile[] = data.map((p: any) => ({
            id: p.id,
            name: p.name,
            role: p.role,
            location: p.location,
            avatarBg: p.avatar_bg || 'from-amber-500 to-orange-600',
          }));
          setProfiles(mapped);
        }
      })
      .catch(() => {
        // fallback to defaults (already set)
      });
    // also restore cross-device last-opened from DB
    if (authUsername) {
      fetch(`/api/v1/preferences?login_username=${encodeURIComponent(authUsername)}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((pref) => {
          if (pref?.active_profile_id) setActiveProfileId(pref.active_profile_id);
          if (pref?.active_thread_id) setActiveSessionId(pref.active_thread_id);
        })
        .catch(() => {})
        .finally(() => setPrefsHydrated(true));
    } else {
      setPrefsHydrated(true);
    }
  }, [authToken]);

  // ─── Auth gate: must be AFTER all hooks (Rules of Hooks) ───────
  if (!authToken) {
    return <Login onLogin={handleLogin} />;
  }

  const handleProfileSelect = (profileId: string) => {
    setActiveProfileId(profileId);
    setMobileSidebarOpen(false);
    setRefreshKey((k) => k + 1);
  };

  const handleCreateNewChat = async () => {
    try {
      const res = await fetch('/api/v1/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: activeProfile.id, title: 'New Conversation' })
      });
      if (res.ok) {
        const t = await res.json();
        const newThread: ChatThread = { id: t.id, title: t.title, createdAt: 'Just now' };
        setThreads((prev) => ({ ...prev, [activeProfile.id]: [newThread, ...(prev[activeProfile.id] || [])] }));
        setActiveSessionId(t.id);
        setMobileSidebarOpen(false);
        return;
      }
    } catch {}
    // fallback local
    const newSid = `session_${Date.now()}`;
    const newThread: ChatThread = { id: newSid, title: 'New Conversation', createdAt: 'Just now' };
    setThreads((prev) => ({ ...prev, [activeProfile.id]: [newThread, ...(prev[activeProfile.id] || [])] }));
    setActiveSessionId(newSid);
    setMobileSidebarOpen(false);
  };

  const handleDeleteThread = async (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation();
    try {
      await fetch(`/api/v1/threads/${threadId}?user_id=${encodeURIComponent(activeProfile.id)}`, { method: 'DELETE' });
    } catch {}
    const remaining = profileThreads.filter((t) => t.id !== threadId);
    setThreads((prev) => ({ ...prev, [activeProfile.id]: remaining }));
    if (activeSessionId === threadId && remaining.length > 0) {
      setActiveSessionId(remaining[0].id);
    } else if (remaining.length === 0) {
      // auto-create will happen via fetchThreads next load; create one now
      handleCreateNewChat();
    }
  };

  const handleAddCustomProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserName.trim()) return;

    try {
      const res = await fetch('/api/v1/profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newUserName.trim(),
          role: newUserRole.trim() || 'Software Engineer',
          location: newUserLocation.trim() || 'Remote',
        }),
      });
      if (!res.ok) throw new Error('Failed to create profile');
      const created = await res.json();
      const newProf: Profile = {
        id: created.id,
        name: created.name,
        role: created.role,
        location: created.location,
        avatarBg: created.avatar_bg || 'from-amber-500 to-orange-600',
      };
      setProfiles((prev) => [...prev, newProf]);
      setActiveProfileId(newProf.id);
      setCustomUserModal(false);
      setNewUserName('');
      setNewUserRole('');
      setNewUserLocation('');
      handleProfileSelect(newProf.id);
    } catch (err) {
      console.error('Create profile failed', err);
      // fallback: local add if backend unreachable
      const id = `user_${newUserName.toLowerCase().replace(/[^a-z0-9]/g, '_')}_${Date.now().toString().slice(-4)}`;
      const newProf: Profile = {
        id,
        name: newUserName.trim(),
        role: newUserRole.trim() || 'Software Engineer',
        location: newUserLocation.trim() || 'Remote',
        avatarBg: 'from-amber-500 to-orange-600',
      };
      setProfiles((prev) => [...prev, newProf]);
      setActiveProfileId(id);
      setCustomUserModal(false);
      setNewUserName('');
      setNewUserRole('');
      setNewUserLocation('');
      handleProfileSelect(id);
    }
  };

  const handleMemoryUpdate = () => {
    setRefreshKey((prev) => prev + 1);
    // refresh thread list order (updated_at bumped)
    fetchThreads(activeProfile.id);
  };

  const handleUpdateThreadTitle = async (title: string) => {
    // optimistic local update
    setThreads((prev) => {
      const list = prev[activeProfile.id] || [];
      const idx = list.findIndex((t) => t.id === activeSessionId);
      if (idx === -1) return prev;
      if (list[idx].title !== 'New Conversation') return prev;
      const updated = [...list];
      updated[idx] = { ...updated[idx], title };
      return { ...prev, [activeProfile.id]: updated };
    });
    try {
      await fetch(`/api/v1/threads/${activeSessionId}?user_id=${encodeURIComponent(activeProfile.id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title })
      });
    } catch {}
  };

  return (
    <div className="flex flex-col lg:flex-row h-[100dvh] lg:h-screen bg-background text-gray-100 overflow-hidden font-sans">
      {/* Mobile top bar */}
      <header className="flex lg:hidden items-center justify-between px-3 py-2.5 bg-panel border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setMobileSidebarOpen(true)}
            className="p-2 -ml-1 text-gray-300 hover:text-white hover:bg-border/50 rounded-xl transition"
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-md shadow-sky-500/20">
              <Cpu className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-bold text-[11px] tracking-wider text-gray-100 uppercase">Deep Harness</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="hidden sm:inline text-[10px] text-muted truncate max-w-[110px]">{activeProfile.name}</span>
          <button
            onClick={() => setIsInspectorOpen(true)}
            className={`p-2 rounded-xl border transition ${isInspectorOpen ? 'bg-sky-500/15 border-sky-500/30 text-sky-400' : 'bg-background border-border text-gray-400'}`}
            aria-label="Open memory inspector"
          >
            <PanelRightOpen className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Backdrop for mobile sidebar */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}
      {/* Backdrop for mobile inspector */}
      {isInspectorOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsInspectorOpen(false)}
        />
      )}

      {/* 1. Left Sidebar (Profiles & Chat History) */}
      <aside
        className={`bg-panel border-r border-border flex flex-col flex-shrink-0
          lg:w-72 lg:h-full lg:static lg:translate-x-0
          fixed inset-y-0 left-0 z-50 w-[82vw] max-w-[300px] h-[100dvh]
          transform transition-transform duration-300 lg:flex
          ${mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
      >
        {/* Mobile close button row */}
        <div className="flex lg:hidden items-center justify-between px-4 py-3 border-b border-border">
          <span className="text-xs font-semibold text-gray-200">Menu</span>
          <button onClick={() => setMobileSidebarOpen(false)} className="p-1.5 text-muted hover:text-white rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>
        {/* App Branding */}
        <div className="h-14 px-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-md shadow-sky-500/20">
              <Cpu className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-xs tracking-wider text-gray-100 uppercase">
                Deep Harness
              </h1>
              <p className="text-[10px] text-muted">Companion Memory</p>
            </div>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
            v1.0
          </span>
        </div>

        {/* Logged in as */}
        <div className="px-4 py-2 border-b border-border flex items-center justify-between text-[11px]">
          <span className="text-muted">
            Signed in as <span className="text-gray-300 font-medium">{authDisplayName}</span>
          </span>
          <button
            onClick={handleLogout}
            className="text-red-400 hover:text-red-300 transition text-[10px] font-medium"
          >
            Logout
          </button>
        </div>

        {/* Profile Switcher Section */}
        <div className="p-3 border-b border-border space-y-2">
          <div className="flex items-center justify-between text-[11px] text-muted font-medium px-1">
            <span>ACTIVE PROFILE</span>
            <button
              onClick={() => setCustomUserModal(true)}
              className="text-sky-400 hover:text-sky-300 transition flex items-center gap-0.5"
            >
              <Plus className="w-3 h-3" />
              <span>New</span>
            </button>
          </div>

          <div className="relative">
            <select
              value={activeProfileId}
              onChange={(e) => handleProfileSelect(e.target.value)}
              className="w-full bg-background border border-border rounded-xl p-2 text-xs text-gray-100 focus:outline-none focus:border-sky-500 cursor-pointer"
            >
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  👤 {p.name} ({p.role.split(' ')[0]})
                </option>
              ))}
            </select>
          </div>

          {/* Quick Profile Summary Card */}
          <div className="p-2.5 bg-background/70 border border-border/80 rounded-xl space-y-1 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-200">{activeProfile.name}</span>
              <span className="text-[10px] text-sky-400 font-mono bg-sky-500/10 px-1.5 py-0.5 rounded">
                {activeProfile.id}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-muted">
              <Briefcase className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">{activeProfile.role}</span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-muted">
              <MapPin className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">{activeProfile.location}</span>
            </div>
          </div>
        </div>

        {/* New Chat Button */}
        <div className="p-3 border-b border-border">
          <button
            onClick={handleCreateNewChat}
            className="w-full py-2.5 px-3 bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium rounded-xl transition flex items-center justify-center gap-2 shadow-md shadow-sky-600/20"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat Thread</span>
          </button>
        </div>

        {/* Chat History Threads */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <div className="px-2 py-1 text-[10px] font-semibold text-muted tracking-wider uppercase">
            Chat Threads ({profileThreads.length})
          </div>

          {profileThreads.length === 0 ? (
            <div className="p-4 text-center text-xs text-muted">No chat history yet.</div>
          ) : (
            profileThreads.map((th) => (
              <div
                key={th.id}
                onClick={() => {
                  setActiveSessionId(th.id);
                  setMobileSidebarOpen(false);
                }}
                className={`group flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition ${
                  activeSessionId === th.id
                    ? 'bg-sky-500/15 text-sky-300 border border-sky-500/30'
                    : 'text-gray-300 hover:bg-background/80 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <MessageSquare
                    className={`w-3.5 h-3.5 flex-shrink-0 ${
                      activeSessionId === th.id ? 'text-sky-400' : 'text-muted'
                    }`}
                  />
                  <span className="truncate font-medium">{th.title}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteThread(e, th.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 rounded transition"
                  title="Delete Thread"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* System Backend Status */}
        <div className="p-3 border-t border-border bg-background/40 space-y-1.5 text-[11px] text-muted">
          <div className="flex items-center justify-between">
            <span>LLM Backbone:</span>
            <span className="text-gray-300 font-mono">Bedrock Llama 3.3</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Store / Search:</span>
            <span className="text-gray-300 font-mono">Postgres + Qdrant RRF</span>
          </div>
        </div>
      </aside>

      {/* 2. Main Chat View */}
      <main className="flex-1 flex flex-col min-h-0 min-w-0 overflow-hidden p-2 sm:p-3 lg:p-4 gap-2 lg:gap-4">
        <div className="flex-1 min-h-0 overflow-hidden">
          <Chat
            userId={activeProfile.id}
            userName={activeProfile.name}
            sessionId={activeSessionId}
            onMemoryUpdate={handleMemoryUpdate}
            onToggleInspector={() => setIsInspectorOpen(!isInspectorOpen)}
            isInspectorOpen={isInspectorOpen}
            onOpenMenu={() => setMobileSidebarOpen(true)}
            onUpdateTitle={handleUpdateThreadTitle}
          />
        </div>
      </main>

      {/* 3. Right Memory & Profile Inspector — drawer on mobile, sidebar on desktop */}
      {/* Desktop inspector */}
      {isInspectorOpen && (
        <aside className="hidden lg:flex w-96 p-4 pl-0 h-full overflow-hidden flex-shrink-0">
          <MemoryPanel
            refreshKey={refreshKey}
            userId={activeProfile.id}
            onClose={() => setIsInspectorOpen(false)}
          />
        </aside>
      )}
      {/* Mobile inspector drawer */}
      <aside
        className={`lg:hidden fixed inset-y-0 right-0 z-50 w-[92vw] max-w-[420px] h-[100dvh] p-3 transform transition-transform duration-300 ${
          isInspectorOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <MemoryPanel
          refreshKey={refreshKey}
          userId={activeProfile.id}
          onClose={() => setIsInspectorOpen(false)}
        />
      </aside>
      {/* Modal: Create Custom Profile */}
      {customUserModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-panel border border-border rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <h3 className="font-semibold text-base text-gray-100">Create New User Profile</h3>
            <p className="text-xs text-muted">
              Creates a dedicated profile with isolated bi-temporal facts, distinct memory bounds, and zero cross-talk.
            </p>

            <form onSubmit={handleAddCustomProfile} className="space-y-3 text-xs">
              <div>
                <label className="block text-muted font-medium mb-1">Full Name</label>
                <input
                  type="text"
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                  placeholder="e.g. Jordan Lee"
                  className="w-full bg-background border border-border rounded-xl p-2.5 text-gray-100 focus:outline-none focus:border-sky-500"
                  required
                />
              </div>

              <div>
                <label className="block text-muted font-medium mb-1">Occupation / Role</label>
                <input
                  type="text"
                  value={newUserRole}
                  onChange={(e) => setNewUserRole(e.target.value)}
                  placeholder="e.g. Cloud Architect / Student"
                  className="w-full bg-background border border-border rounded-xl p-2.5 text-gray-100 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-muted font-medium mb-1">Location</label>
                <input
                  type="text"
                  value={newUserLocation}
                  onChange={(e) => setNewUserLocation(e.target.value)}
                  placeholder="e.g. Austin, TX"
                  className="w-full bg-background border border-border rounded-xl p-2.5 text-gray-100 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCustomUserModal(false)}
                  className="flex-1 py-2 bg-background hover:bg-border/60 text-gray-300 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 bg-sky-600 hover:bg-sky-500 text-white font-medium rounded-xl transition shadow-md shadow-sky-600/20"
                >
                  Create Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
