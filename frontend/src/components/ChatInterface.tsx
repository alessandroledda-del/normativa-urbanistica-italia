import React, { useState } from 'react';
import { sendMessage, type ChatResponse } from '../api';
import { Send, Book } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  sources?: any[];
}

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: 'ai',
      content: "Ciao! Sono l'assistente AI per la normativa urbanistica italiana. Chiedimi qualsiasi cosa riguardo regolamenti nazionali, regionali, provinciali o comunali.",
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendMessage(input);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response.answer,
        sources: response.sources,
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (error) {
      console.error(error);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: "Si è verificato un errore durante la ricerca della normativa. Controlla che il backend sia in esecuzione.",
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="chat-container">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="message-bubble">
              <p>{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <Book size={16} className="text-muted" />
                    <span className="text-muted" style={{ fontWeight: 500 }}>Fonti Normative:</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {msg.sources.map((src, i) => (
                      <div key={i} style={{ backgroundColor: 'var(--bg-base)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '12px', padding: '4px 8px', backgroundColor: 'var(--primary-glow)', color: 'var(--primary)', borderRadius: '4px', textTransform: 'capitalize' }}>
                            {src.metadata.level}
                          </span>
                          {src.metadata.region && (
                            <span style={{ fontSize: '12px', padding: '4px 8px', backgroundColor: 'var(--bg-surface-hover)', borderRadius: '4px' }}>
                              {src.metadata.region}
                            </span>
                          )}
                          {src.metadata.commune && (
                            <span style={{ fontSize: '12px', padding: '4px 8px', backgroundColor: 'var(--bg-surface-hover)', borderRadius: '4px' }}>
                              Comune: {src.metadata.commune}
                            </span>
                          )}
                          {src.metadata.source && (
                            <a href={src.metadata.source} target="_blank" rel="noreferrer" style={{ fontSize: '12px', padding: '4px 8px', backgroundColor: 'var(--bg-surface-hover)', borderRadius: '4px', color: 'var(--secondary)', textDecoration: 'none' }}>
                              🔗 {src.metadata.title || 'Apri Link'}
                            </a>
                          )}
                        </div>
                        <p className="text-muted" style={{ fontSize: '13px', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          "{src.page_content}"
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message ai">
            <div className="message-bubble">
               <div className="loading-dots">
                 <span></span><span></span><span></span>
               </div>
            </div>
          </div>
        )}
      </div>

      <div className="input-area">
        <form className="input-wrapper" onSubmit={handleSend}>
          <input 
            type="text" 
            placeholder="Fai una domanda sulla normativa (es. Quali sono le distanze minime tra gli edifici?)" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button type="submit" className="btn" disabled={isLoading} style={{ opacity: isLoading ? 0.7 : 1 }}>
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
};
