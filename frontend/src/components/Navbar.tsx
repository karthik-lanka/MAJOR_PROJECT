import React from 'react';
import { Sparkles, BookOpen, FileText, LogIn, LogOut, User as UserIcon } from 'lucide-react';
import { StatusResponse } from '../api/client';
import { UserProfile } from '../api/supabase';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  status: StatusResponse | null;
  user: UserProfile | null;
  onOpenAuth: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  user,
  onOpenAuth,
  onLogout,
}) => {
  const tabs = [
    { id: 'chat', label: 'Study Q&A Chat', icon: Sparkles },
    { id: 'documents', label: 'Document Ingestion', icon: FileText },
    { id: 'study', label: 'Study Workbench', icon: BookOpen },
  ];

  return (
    <header style={{
      background: '#ffffff',
      borderBottom: '1px solid #e5e7eb',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      padding: '12px 24px',
    }}>
      <div style={{
        maxWidth: 1600,
        width: '100%',
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 16,
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 38,
            height: 38,
            borderRadius: 10,
            background: '#0d0d0d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Sparkles size={20} color="#ffffff" />
          </div>
          <div>
            <h1 style={{
              fontSize: '1.15rem',
              fontWeight: 700,
              margin: 0,
              color: '#0d0d0d',
              letterSpacing: '-0.02em',
            }}>
              StudyAssistant
            </h1>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          background: '#f3f4f6',
          padding: '4px',
          borderRadius: '10px',
          border: '1px solid #e5e7eb',
        }}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '7px 14px',
                  borderRadius: '7px',
                  fontSize: '0.85rem',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? '#0d0d0d' : '#6b7280',
                  background: isActive ? '#ffffff' : 'transparent',
                  border: isActive ? '1px solid #e5e7eb' : '1px solid transparent',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                }}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* User Auth Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: '#f9fafb',
                padding: '4px 12px 4px 6px',
                borderRadius: '999px',
                border: '1px solid #e5e7eb',
              }}>
                <div style={{
                  width: 26,
                  height: 26,
                  borderRadius: '50%',
                  background: '#0d0d0d',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: '#ffffff',
                }}>
                  {(user.name || user.email)[0].toUpperCase()}
                </div>
                <span style={{
                  fontSize: '0.84rem',
                  color: '#111827',
                  fontWeight: 500,
                  maxWidth: 140,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {user.name || user.email.split('@')[0]}
                </span>
              </div>
              <button
                onClick={onLogout}
                className="btn btn-secondary"
                title="Sign out"
                style={{
                  padding: '6px 12px',
                  fontSize: '0.82rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <LogOut size={14} />
                <span>Logout</span>
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="btn btn-primary"
              style={{
                padding: '8px 16px',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                borderRadius: '8px',
              }}
            >
              <LogIn size={15} />
              <span>Sign In / Register</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
