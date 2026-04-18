import { ChatInterface } from './components/ChatInterface';
import { DocumentUpload } from './components/DocumentUpload';
import { Map } from 'lucide-react';

function App() {
  return (
    <div className="app-container">
      {/* Sidebar - Admin & Context */}
      <aside className="sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '40px' }}>
          <div style={{ 
            padding: '12px', 
            background: 'linear-gradient(135deg, var(--primary), var(--secondary))', 
            borderRadius: 'var(--radius-sm)', 
            color: '#fff',
            boxShadow: '0 4px 16px var(--primary-glow)'
          }}>
            <Map size={24} />
          </div>
          <div>
            <h1 className="brand" style={{ fontSize: '22px', margin: 0, lineHeight: 1.2 }}>AI Urbanistica</h1>
            <span className="text-muted" style={{ fontSize: '13px', display: 'block', marginTop: '2px' }}>Assistente Normativo Agentic</span>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
           <DocumentUpload />
        </div>
        
        <div style={{ marginTop: 'auto', paddingTop: '24px', borderTop: '1px solid var(--border-color)' }}>
          <p className="text-muted" style={{ fontSize: '12px', textAlign: 'center' }}>
            Il database normativo è aggiornato dagli utenti.
          </p>
        </div>
      </aside>

      {/* Main Chat Content */}
      <main className="main-content">
        <ChatInterface />
      </main>
    </div>
  );
}

export default App;
