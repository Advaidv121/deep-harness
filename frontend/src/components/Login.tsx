import { useState } from 'react';
import { Cpu, Lock, User, ArrowRight } from 'lucide-react';

interface LoginProps {
  onLogin: (token: string, username: string, displayName: string) => void;
}

export function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Login failed');
      }

      const data = await res.json();
      onLogin(data.token, data.username, data.display_name);
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20 mb-4">
            <Cpu className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-100 tracking-tight">Deep Harness</h1>
          <p className="text-sm text-muted mt-1">AI Companion Memory Engine</p>
        </div>

        {/* Login Card */}
        <div className="bg-panel border border-border rounded-2xl p-6 shadow-xl">
          <div className="flex items-center gap-2 mb-6">
            <Lock className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-semibold text-gray-200">Sign In</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-muted font-medium mb-1.5">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter username"
                  className="w-full bg-background border border-border rounded-xl pl-10 pr-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-sky-500 transition placeholder:text-gray-500"
                  required
                  autoFocus
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-muted font-medium mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className="w-full bg-background border border-border rounded-xl pl-10 pr-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-sky-500 transition placeholder:text-gray-500"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition flex items-center justify-center gap-2 shadow-md shadow-sky-600/20"
            >
              {loading ? (
                <span className="animate-pulse">Signing in...</span>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-[10px] text-muted mt-6">
          Powered by Bedrock Llama 3.3 · Postgres + Qdrant RRF
        </p>
      </div>
    </div>
  );
}
