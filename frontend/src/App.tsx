import { useState, useEffect } from 'react';
import {
  Cpu,
  Plus,
  MessageSquare,
  Trash2,
  MapPin,
  Briefcase
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
  const [authDisplayName, setAuthDisplayName] = useState<string>(() => {
    return localStorage.getItem('dh_auth_display_name') || '';
  });

  const [profiles, setProfiles] = useState<Profile[]>(() => {
    const saved = localStorage.getItem('companion_profiles');
    return saved ? JSON.parse(saved) : DEFAULT_PROFILES;
  });

  const [activeProfileId, setActiveProfileId] = useState<string>(() => {
    return localStorage.getItem('active_profile_id') || 'alex_prod';
  });

  const [threads, setThreads] = useState<Record<string, ChatThread[]>>(() => {
    const saved = localStorage.getItem('companion_threads');
    return saved
      ? JSON.parse(saved)
      : {
          alex_prod: [
            { id: 'chat_main_1', title: 'Work Outage & Meditation', createdAt: 'Today' }
          ],
          clara_orbital: [
            { id: 'chat_clara_1', title: 'Orbital Trajectory & Coffee', createdAt: 'Today' }
          ],
          maya_architect: [
            { id: 'chat_maya_1', title: 'Chicago Studio & Kittens', createdAt: 'Today' }
          ]
        };
  });

  const [activeSessionId, setActiveSessionId] = useState<string>('chat_main_1');
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);
  const [refreshKey, setRefreshKey] = useState<number>(0);
  const [customUserModal, setCustomUserModal] = useState<boolean>(false);
  const [newUserName, setNewUserName] = useState<string>('');
  const [newUserRole, setNewUserRole] = useState<string>('');
  const [newUserLocation, setNewUserLocation] = useState<string>('');

  const handleLogin = (token: string, _username: string, displayName: string) => {
    localStorage.setItem('dh_auth_token', token);
    localStorage.setItem('dh_auth_display_name', displayName);
    setAuthToken(token);
    setAuthDisplayName(displayName);
  };

  const handleLogout = () => {
    localStorage.removeItem('dh_auth_token');
    localStorage.removeItem('dh_auth_display_name');
    setAuthToken(null);
    setAuthDisplayName('');
  };

  const activeProfile = profiles.find((p) => p.id === activeProfileId) || profiles[0];
  const profileThreads = threads[activeProfile.id] || [];

  // Persist active profile
  useEffect(() => {
    localStorage.setItem('active_profile_id', activeProfileId);
  }, [activeProfileId]);

  // Persist threads
  useEffect(() => {
    localStorage.setItem('companion_threads', JSON.stringify(threads));
  }, [threads]);

  // ─── Auth gate: must be AFTER all hooks (Rules of Hooks) ───────
  if (!authToken) {
    return <Login onLogin={handleLogin} />;
  }

  const handleProfileSelect = (profileId: string) => {
    setActiveProfileId(profileId);
    const existingThreads = threads[profileId] || [];
    if (existingThreads.length === 0) {
      const newSid = `session_${Date.now()}`;
      setThreads((prev) => ({
        ...prev,
        [profileId]: [{ id: newSid, title: 'New Conversation', createdAt: 'Just now' }]
      }));
      setActiveSessionId(newSid);
    } else {
      setActiveSessionId(existingThreads[0].id);
    }
    setRefreshKey((k) => k + 1);
  };

  const handleCreateNewChat = () => {
    const newSid = `session_${Date.now()}`;
    const newThread: ChatThread = {
      id: newSid,
      title: `Conversation ${profileThreads.length + 1}`,
      createdAt: 'Just now'
    };

    setThreads((prev) => ({
      ...prev,
      [activeProfile.id]: [newThread, ...(prev[activeProfile.id] || [])]
    }));
    setActiveSessionId(newSid);
  };

  const handleDeleteThread = (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation();
    localStorage.removeItem(`chat_history_${activeProfile.id}_${threadId}`);
    const remaining = profileThreads.filter((t) => t.id !== threadId);
    setThreads((prev) => ({
      ...prev,
      [activeProfile.id]: remaining
    }));
    if (activeSessionId === threadId && remaining.length > 0) {
      setActiveSessionId(remaining[0].id);
    }
  };

  const handleAddCustomProfile = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserName.trim()) return;

    const id = `user_${newUserName.toLowerCase().replace(/[^a-z0-9]/g, '_')}_${Date.now().toString().slice(-4)}`;
    const newProf: Profile = {
      id,
      name: newUserName.trim(),
      role: newUserRole.trim() || 'Software Engineer',
      location: newUserLocation.trim() || 'Remote',
      avatarBg: 'from-amber-500 to-orange-600'
    };

    setProfiles((prev) => [...prev, newProf]);
    localStorage.setItem('companion_profiles', JSON.stringify([...profiles, newProf]));
    setActiveProfileId(id);
    setCustomUserModal(false);
    setNewUserName('');
    setNewUserRole('');
    setNewUserLocation('');
    handleProfileSelect(id);
  };

  const handleMemoryUpdate = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="flex h-screen bg-background text-gray-100 overflow-hidden font-sans">
      {/* 1. Left Sidebar (Profiles & Chat History) */}
      <aside className="w-72 bg-panel border-r border-border flex flex-col flex-shrink-0">
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
                onClick={() => setActiveSessionId(th.id)}
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
      <main className="flex-1 flex flex-col h-full overflow-hidden p-4 gap-4">
        <div className="flex-1 h-full overflow-hidden">
          <Chat
            userId={activeProfile.id}
            userName={activeProfile.name}
            sessionId={activeSessionId}
            onMemoryUpdate={handleMemoryUpdate}
            onToggleInspector={() => setIsInspectorOpen(!isInspectorOpen)}
            isInspectorOpen={isInspectorOpen}
          />
        </div>
      </main>

      {/* 3. Collapsible Right Memory & Profile Inspector */}
      {isInspectorOpen && (
        <aside className="w-96 p-4 pl-0 h-full overflow-hidden flex-shrink-0">
          <MemoryPanel
            refreshKey={refreshKey}
            userId={activeProfile.id}
            onClose={() => setIsInspectorOpen(false)}
          />
        </aside>
      )}

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
