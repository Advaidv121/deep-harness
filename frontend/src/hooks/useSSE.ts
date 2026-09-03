import { useState, useCallback } from 'react';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  retrievedFacts?: string[];
  extractedFacts?: Array<{
    fact: string;
    category?: string;
    action: string;
    salience_score: number;
    supersedes_text?: string | null;
  }>;
}

export function useSSE(onMemoryUpdate?: () => void) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [currentRetrievedFacts, setCurrentRetrievedFacts] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const streamMessage = useCallback(async (
    message: string,
    sessionId: string = 'default_session',
    userId: string = 'default_user',
    onComplete?: (fullResponse: string, retrieved: string[], extracted: any[]) => void
  ) => {
    setIsStreaming(true);
    setStreamingContent('');
    setCurrentRetrievedFacts([]);
    setError(null);

    let accumulated = '';
    let retrieved: string[] = [];
    let extracted: any[] = [];

    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          user_id: userId,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported by response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;

          const jsonStr = trimmed.replace(/^data:\s*/, '');
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);

            if (data.type === 'context') {
              retrieved = data.retrieved_facts || [];
              setCurrentRetrievedFacts(retrieved);
            } else if (data.type === 'token') {
              accumulated += data.token;
              setStreamingContent(accumulated);
            } else if (data.type === 'done') {
              extracted = data.extracted_facts || [];
              if (data.memory_updated && onMemoryUpdate) {
                onMemoryUpdate();
              }
            }
          } catch (e) {
            // Ignore malformed chunks
          }
        }
      }

      if (onComplete) {
        onComplete(accumulated, retrieved, extracted);
      }
    } catch (err: any) {
      setError(err.message || 'Streaming failed');
    } finally {
      setIsStreaming(false);
      setStreamingContent('');
      setCurrentRetrievedFacts([]);
    }
  }, [onMemoryUpdate]);

  return {
    isStreaming,
    streamingContent,
    currentRetrievedFacts,
    error,
    streamMessage
  };
}
