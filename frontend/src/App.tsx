import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { ChatInterface } from './components/ChatInterface';
import { DocumentManager } from './components/DocumentManager';
import { StudyWorkbench } from './components/StudyWorkbench';
import { AuthModal } from './components/AuthModal';
import { getCurrentUser, logoutUser, UserProfile } from './api/supabase';
import { DocumentItem, StatusResponse, HealthResponse, fetchDocuments, fetchStatus, fetchHealth } from './api/client';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('chat');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const userRef = useRef<UserProfile | null>(null);

  useEffect(() => {
    userRef.current = user;
  }, [user]);

  const loadDocuments = async (targetEmail?: string) => {
    try {
      const emailToUse = targetEmail !== undefined ? targetEmail : userRef.current?.email;
      const docsData = await fetchDocuments(emailToUse);
      setDocuments(docsData.documents || []);
    } catch (err) {
      console.error('Error fetching documents:', err);
    }
  };

  const loadSystemStatus = async () => {
    try {
      const [statusData, healthData] = await Promise.allSettled([
        fetchStatus(),
        fetchHealth(),
      ]);

      if (statusData.status === 'fulfilled') {
        setStatus(statusData.value);
      }
      if (healthData.status === 'fulfilled') {
        setHealth(healthData.value);
      }
    } catch (err) {
      console.error('Error fetching system status:', err);
    }
  };

  // Initial load
  useEffect(() => {
    getCurrentUser().then((u) => {
      if (u) {
        setUser(u);
        userRef.current = u;
        loadDocuments(u.email);
      } else {
        loadDocuments(undefined);
      }
    });

    loadSystemStatus();

    // Periodic system status sync (does not wipe documents)
    const statusInterval = setInterval(loadSystemStatus, 15000);
    return () => clearInterval(statusInterval);
  }, []);

  // Auto-poll documents when any document is still extracting/chunking/embedding
  useEffect(() => {
    const hasProcessingDocs = documents.some((d) =>
      ['UPLOADED', 'EXTRACTING', 'CHUNKING', 'EMBEDDING', 'INDEXING'].includes(d.processing_status)
    );

    if (hasProcessingDocs) {
      const pollTimer = setTimeout(() => {
        loadDocuments(userRef.current?.email);
      }, 2000);
      return () => clearTimeout(pollTimer);
    }
  }, [documents]);

  const handleToggleSelectDoc = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((dId) => dId !== id) : [...prev, id]
    );
  };

  const handleLogout = async () => {
    await logoutUser();
    setUser(null);
    userRef.current = null;
    setSelectedDocIds([]);
    await loadDocuments(undefined);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-secondary)' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        status={status}
        user={user}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
      />

      <main style={{ flex: 1, paddingBottom: 40, display: 'flex', flexDirection: 'column' }}>
        {/* Chat tab kept rendered with display toggle to preserve conversation state across tab switches */}
        <div style={{ display: activeTab === 'chat' ? 'flex' : 'none', flex: 1, flexDirection: 'column' }}>
          <ChatInterface
            documents={documents}
            selectedDocIds={selectedDocIds}
            currentUser={user}
            onOpenAuth={() => setIsAuthModalOpen(true)}
            onDocumentUploaded={() => loadDocuments(user?.email)}
          />
        </div>

        {/* Document Ingestion tab kept rendered with display toggle */}
        <div style={{ display: activeTab === 'documents' ? 'block' : 'none' }}>
          <DocumentManager
            documents={documents}
            selectedDocIds={selectedDocIds}
            currentUser={user}
            onOpenAuth={() => setIsAuthModalOpen(true)}
            onToggleSelectDoc={handleToggleSelectDoc}
            onRefreshDocs={() => loadDocuments(user?.email)}
          />
        </div>

        {/* Study Workbench tab kept rendered with display toggle */}
        <div style={{ display: activeTab === 'study' ? 'block' : 'none' }}>
          <StudyWorkbench
            documents={documents}
            selectedDocIds={selectedDocIds}
          />
        </div>
      </main>

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={(loggedUser) => {
          setUser(loggedUser);
          userRef.current = loggedUser;
          loadDocuments(loggedUser.email);
        }}
      />
    </div>
  );
};

export default App;
