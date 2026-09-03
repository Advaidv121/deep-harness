import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, RefreshCw, AlertCircle, Database, BrainCircuit, ShieldCheck, ChevronDown, ChevronUp } from 'lucide-react';
import { Message, useSSE } from '../hooks/useSSE.ts';

interface ChatProps {
  userId: string;
  userName: string;
  sessionId: string;
  onMemoryUpdate: () => void;
  onToggleInspector?: () => void;
  isInspectorOpen?: boolean;
}

export const Chat: React.FC<ChatProps> = ({
  userId,
  userName,
  sessionId,
  onMemoryUpdate,
  onToggleInspector,
  isInspectorOpen
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [expandedFacts, setExpandedFacts] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { isStreaming, streamingContent, currentRetrievedFacts, error, streamMessage } = useSSE(onMemoryUpdate);

  // Load or initialize welcome message when session/user changes
  useEffect(() => {
    const saved = localStorage.getItem(`chat_history_${userId}_${sessionId}`);
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
        return;
      } catch (e) {}
    }

    setMessages([
      {
        id: `welcome_${Date.now()}`,
        role: 'assistant',
        content: `Hey ${userName}! I'm Sam, your lifelong AI companion. I track our conversations with bi-temporal memory so I'll always remember your evolving preferences and never bring up outdated habits. What's on your mind?`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  }, [userId, sessionId, userName]);

  // Persist messages to localStorage per session
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(`chat_history_${userId}_${sessionId}`, JSON.stringify(messages));
    }
  }, [messages, userId, sessionId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || isStreaming) return;

    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    if (!textToSend) setInput('');

    await streamMessage(text, sessionId, userId, (fullResponse, retrieved, extracted) => {
      const assistantMessage: Message = {
        id: `asst_${Date.now()}`,
        role: 'assistant',
        content: fullResponse,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        retrievedFacts: retrieved,
        extractedFacts: extracted
      };
      setMessages(prev => [...prev, assistantMessage]);
      onMemoryUpdate();
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleFactExpansion = (msgId: string) => {
    setExpandedFacts(prev => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const samplePrompts = [
    { label: "🔍 Test Recall", text: "What are my current diet, pet, and work preferences?" },
    { label: "⚡ Contradiction Trap", text: "Actually, I changed my diet and now strictly follow a keto regimen with meat." },
    { label: "🛡️ Abstention Probe", text: "What is my mother's maiden name?" },
    { label: "🎭 Persona Probe", text: "Sam, tell me about yourself, your core values, and what you enjoy." },
  ];

  return (
    <div className="flex flex-col h-full bg-panel rounded-2xl border border-border overflow-hidden shadow-2xl">
      {/* Top Header */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-border bg-background/60 backdrop-blur">
        <div className="flex items-center space-x-3.5">
          <div className="relative">
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 rounded-full ring-2 ring-panel" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-gray-100 text-sm">Sam</h2>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="w-3 h-3" />
                Contradiction-Proof
              </span>
            </div>
            <p className="text-[11px] text-muted">Chatting with <span className="text-gray-300 font-medium">{userName}</span> ({userId})</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {onToggleInspector && (
            <button
              onClick={onToggleInspector}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition flex items-center gap-1.5 ${
                isInspectorOpen
                  ? 'bg-sky-500/15 border-sky-500/40 text-sky-400'
                  : 'bg-background hover:bg-border/60 border-border text-gray-300'
              }`}
            >
              <BrainCircuit className="w-3.5 h-3.5" />
              <span>Memory & Profile</span>
            </button>
          )}

          <button
            onClick={() => {
              localStorage.removeItem(`chat_history_${userId}_${sessionId}`);
              setMessages([]);
            }}
            className="p-2 text-muted hover:text-gray-200 hover:bg-border/50 rounded-xl transition"
            title="Clear Chat Thread"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-sky-500/20 border border-sky-500/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot className="w-4 h-4 text-sky-400" />
              </div>
            )}

            <div className={`max-w-[80%] space-y-1.5`}>
              <div
                className={`p-4 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-sky-600 text-white rounded-tr-none shadow-md shadow-sky-600/15'
                    : 'bg-background border border-border text-gray-200 rounded-tl-none shadow-sm'
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>

                {/* Retrieved Context Accordion */}
                {msg.retrievedFacts && msg.retrievedFacts.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-border/60">
                    <button
                      onClick={() => toggleFactExpansion(msg.id)}
                      className="flex items-center justify-between w-full text-[11px] text-sky-400 font-medium hover:text-sky-300 transition"
                    >
                      <span className="flex items-center gap-1.5">
                        <Database className="w-3 h-3" />
                        Proactively Retrieved Memory ({msg.retrievedFacts.length} facts)
                      </span>
                      {expandedFacts[msg.id] ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>

                    {expandedFacts[msg.id] && (
                      <div className="mt-2 space-y-1">
                        {msg.retrievedFacts.map((fact, idx) => (
                          <div key={idx} className="text-[11px] text-muted bg-panel px-2.5 py-1 rounded-lg border border-border/50">
                            • {fact}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Extracted Facts Tag */}
                {msg.extractedFacts && msg.extractedFacts.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-border/40 flex flex-wrap gap-1.5">
                    {msg.extractedFacts.map((ef, idx) => (
                      <span
                        key={idx}
                        className={`text-[10px] px-2 py-0.5 rounded-md font-mono border ${
                          ef.action === 'UPDATE'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        }`}
                      >
                        [{ef.action}] {ef.fact}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <span className={`text-[10px] text-muted block px-1 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                {msg.timestamp}
              </span>
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                <User className="w-4 h-4 text-indigo-300" />
              </div>
            )}
          </div>
        ))}

        {/* Live Streaming Assistant Message */}
        {isStreaming && (
          <div className="flex gap-3.5 justify-start">
            <div className="w-8 h-8 rounded-full bg-sky-500/20 border border-sky-500/30 flex items-center justify-center flex-shrink-0 mt-0.5 animate-pulse">
              <Bot className="w-4 h-4 text-sky-400" />
            </div>
            <div className="max-w-[80%] space-y-1.5">
              <div className="p-4 rounded-2xl text-sm leading-relaxed bg-background border border-border text-gray-200 rounded-tl-none shadow-sm">
                <div className="whitespace-pre-wrap">{streamingContent || '...'}</div>
                {currentRetrievedFacts.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-border/60">
                    <div className="flex items-center gap-1.5 text-[11px] text-sky-400 font-medium mb-1">
                      <Database className="w-3 h-3" />
                      <span>Retrieved Context ({currentRetrievedFacts.length} facts)</span>
                    </div>
                    <div className="text-[11px] text-muted italic">
                      {currentRetrievedFacts.join(' • ')}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Test Chips */}
      <div className="px-6 py-2.5 bg-background/40 border-t border-border/50 flex flex-wrap gap-2 items-center">
        <span className="text-[11px] text-muted font-medium mr-1">Quick Scenarios:</span>
        {samplePrompts.map((p, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(p.text)}
            disabled={isStreaming}
            className="text-[11px] px-2.5 py-1 rounded-full bg-background hover:bg-border/60 text-gray-300 border border-border transition flex items-center gap-1.5 disabled:opacity-50"
          >
            <Sparkles className="w-3 h-3 text-sky-400" />
            {p.label}
          </button>
        ))}
      </div>

      {/* Input Field */}
      <div className="p-4 bg-background/70 border-t border-border backdrop-blur">
        <div className="relative flex items-center">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message Sam as ${userName}... (Press Enter to send)`}
            rows={1}
            disabled={isStreaming}
            className="w-full bg-panel border border-border rounded-xl px-4 py-3 pr-12 text-sm text-gray-100 placeholder-muted focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 resize-none transition"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isStreaming}
            className="absolute right-2 p-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg disabled:opacity-40 transition shadow-md shadow-sky-600/20"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
