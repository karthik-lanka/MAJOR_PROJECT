import React, { useState } from 'react';
import { LogIn, UserPlus, Mail, User, Lock, Sparkles, CheckCircle2, AlertCircle, X, Eye, EyeOff } from 'lucide-react';
import { registerAccount, loginAccount, loginWithValidEmail, UserProfile } from '../api/supabase';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: UserProfile) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  
  // Login fields
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);

  // Register fields
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    if (regPassword !== regConfirmPassword) {
      setError('Passwords do not match. Please verify both password fields.');
      return;
    }

    if (regPassword.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await registerAccount(regName, regEmail, regPassword);
      setSuccessMsg('Account registered successfully! Signing you into your study workspace...');
      setTimeout(() => {
        onSuccess(user);
        onClose();
      }, 900);
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please check your information.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setIsLoading(true);

    try {
      const user = await loginAccount(loginEmail, loginPassword, rememberMe);
      setSuccessMsg(`Welcome back, ${user.name || user.email}! Opening workspace...`);
      setTimeout(() => {
        onSuccess(user);
        onClose();
      }, 700);
    } catch (err: any) {
      setError(err.message || 'Invalid email or password.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoSignIn = async (demoEmail: string, demoName: string) => {
    setError(null);
    setIsLoading(true);
    try {
      const user = await loginWithValidEmail(demoEmail, demoName, rememberMe);
      onSuccess(user);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Demo login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.45)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: 20,
    }}>
      <div style={{
        width: '100%',
        maxWidth: 440,
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '16px',
        padding: '30px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
        position: 'relative',
        color: '#0d0d0d',
      }}>
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: 18,
            right: 18,
            background: '#f3f4f6',
            border: 'none',
            borderRadius: '50%',
            width: 32,
            height: 32,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#6b7280',
            cursor: 'pointer',
            transition: 'background 0.15s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = '#e5e7eb')}
          onMouseLeave={(e) => (e.currentTarget.style.background = '#f3f4f6')}
        >
          <X size={16} />
        </button>

        {/* Brand header */}
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <div style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: '#0d0d0d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 12px',
          }}>
            <Sparkles size={22} color="#ffffff" />
          </div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, margin: '0 0 6px 0', color: '#0d0d0d' }}>
            {authMode === 'login' ? 'Sign In to StudyAssistant' : 'Create Your Account'}
          </h2>
          <p style={{ fontSize: '0.84rem', color: '#6b7280', margin: 0 }}>
            {authMode === 'login'
              ? 'Enter your credentials to access your private study sessions'
              : 'Register first to organize and save your academic notes and queries'}
          </p>
        </div>

        {/* Tab Switcher: Sign In vs Register */}
        <div style={{
          display: 'flex',
          background: '#f3f4f6',
          padding: 4,
          borderRadius: 10,
          marginBottom: 20,
          border: '1px solid #e5e7eb',
        }}>
          <button
            type="button"
            onClick={() => { setAuthMode('login'); setError(null); }}
            style={{
              flex: 1,
              padding: '8px 12px',
              fontSize: '0.85rem',
              fontWeight: authMode === 'login' ? 600 : 500,
              background: authMode === 'login' ? '#ffffff' : 'transparent',
              color: authMode === 'login' ? '#0d0d0d' : '#6b7280',
              border: authMode === 'login' ? '1px solid #e5e7eb' : 'none',
              borderRadius: 7,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              boxShadow: authMode === 'login' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <LogIn size={15} />
            <span>Sign In</span>
          </button>

          <button
            type="button"
            onClick={() => { setAuthMode('register'); setError(null); }}
            style={{
              flex: 1,
              padding: '8px 12px',
              fontSize: '0.85rem',
              fontWeight: authMode === 'register' ? 600 : 500,
              background: authMode === 'register' ? '#ffffff' : 'transparent',
              color: authMode === 'register' ? '#0d0d0d' : '#6b7280',
              border: authMode === 'register' ? '1px solid #e5e7eb' : 'none',
              borderRadius: 7,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              boxShadow: authMode === 'register' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <UserPlus size={15} />
            <span>Register</span>
          </button>
        </div>

        {/* Error / Success Notifications */}
        {error && (
          <div style={{
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            padding: '10px 12px',
            color: '#dc2626',
            fontSize: '0.82rem',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginBottom: 16,
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div style={{
            background: '#ecfdf5',
            border: '1px solid #a7f3d0',
            borderRadius: '8px',
            padding: '10px 12px',
            color: '#059669',
            fontSize: '0.82rem',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginBottom: 16,
          }}>
            <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Forms */}
        {authMode === 'login' ? (
          /* LOGIN FORM */
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>
                Email Address
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} style={{ position: 'absolute', left: 12, top: 11, color: '#9ca3af' }} />
                <input
                  type="email"
                  required
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="student@university.edu"
                  style={{
                    width: '100%',
                    background: '#ffffff',
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    padding: '9px 14px 9px 36px',
                    color: '#0d0d0d',
                    fontSize: '0.88rem',
                    outline: 'none',
                    transition: 'border-color 0.15s ease',
                  }}
                  onFocus={(e) => (e.target.style.borderColor = '#0d0d0d')}
                  onBlur={(e) => (e.target.style.borderColor = '#d1d5db')}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} style={{ position: 'absolute', left: 12, top: 11, color: '#9ca3af' }} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="Enter your password"
                  style={{
                    width: '100%',
                    background: '#ffffff',
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    padding: '9px 38px 9px 36px',
                    color: '#0d0d0d',
                    fontSize: '0.88rem',
                    outline: 'none',
                    transition: 'border-color 0.15s ease',
                  }}
                  onFocus={(e) => (e.target.style.borderColor = '#0d0d0d')}
                  onBlur={(e) => (e.target.style.borderColor = '#d1d5db')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: 12,
                    top: 10,
                    background: 'none',
                    border: 'none',
                    color: '#9ca3af',
                    cursor: 'pointer',
                    padding: 0,
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.82rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: '#4b5563' }}>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  style={{ accentColor: '#0d0d0d' }}
                />
                <span>Remember me on this browser</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading || !loginEmail.trim()}
              className="btn btn-primary"
              style={{
                width: '100%',
                padding: '10px',
                marginTop: 4,
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                fontSize: '0.88rem',
                fontWeight: 600,
              }}
            >
              <LogIn size={16} />
              <span>{isLoading ? 'Signing In...' : 'Sign In'}</span>
            </button>

            <div style={{ textAlign: 'center', fontSize: '0.82rem', color: '#6b7280', marginTop: 4 }}>
              Don't have an account yet?{' '}
              <button
                type="button"
                onClick={() => { setAuthMode('register'); setError(null); }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#0d0d0d',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0,
                }}
              >
                Register now
              </button>
            </div>
          </form>
        ) : (
          /* REGISTER FORM */
          <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>
                Full Name <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <div style={{ position: 'relative' }}>
                <User size={16} style={{ position: 'absolute', left: 12, top: 11, color: '#9ca3af' }} />
                <input
                  type="text"
                  required
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  placeholder="e.g. Alex Johnson"
                  style={{
                    width: '100%',
                    background: '#ffffff',
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    padding: '9px 14px 9px 36px',
                    color: '#0d0d0d',
                    fontSize: '0.88rem',
                    outline: 'none',
                    transition: 'border-color 0.15s ease',
                  }}
                  onFocus={(e) => (e.target.style.borderColor = '#0d0d0d')}
                  onBlur={(e) => (e.target.style.borderColor = '#d1d5db')}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>
                Student / User Email <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} style={{ position: 'absolute', left: 12, top: 11, color: '#9ca3af' }} />
                <input
                  type="email"
                  required
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="student@university.edu"
                  style={{
                    width: '100%',
                    background: '#ffffff',
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    padding: '9px 14px 9px 36px',
                    color: '#0d0d0d',
                    fontSize: '0.88rem',
                    outline: 'none',
                    transition: 'border-color 0.15s ease',
                  }}
                  onFocus={(e) => (e.target.style.borderColor = '#0d0d0d')}
                  onBlur={(e) => (e.target.style.borderColor = '#d1d5db')}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
              <div>
                <label style={{ fontSize: '0.82rem', fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>
                  Password <span style={{ color: '#dc2626' }}>*</span>
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock size={15} style={{ position: 'absolute', left: 10, top: 11, color: '#9ca3af' }} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="Min 6 chars"
                    style={{
                      width: '100%',
                      background: '#ffffff',
                      border: '1px solid #d1d5db',
                      borderRadius: '8px',
                      padding: '9px 10px 9px 32px',
                      color: '#0d0d0d',
                      fontSize: '0.84rem',
                      outline: 'none',
                    }}
                    onFocus={(e) => (e.target.style.borderColor = '#0d0d0d')}
                    onBlur={(e) => (e.target.style.borderColor = '#d1d5db')}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.82rem', fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>
                  Confirm Password <span style={{ color: '#dc2626' }}>*</span>
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock size={15} style={{ position: 'absolute', left: 10, top: 11, color: '#9ca3af' }} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={regConfirmPassword}
                    onChange={(e) => setRegConfirmPassword(e.target.value)}
                    placeholder="Repeat password"
                    style={{
                      width: '100%',
                      background: '#ffffff',
                      border: '1px solid #d1d5db',
                      borderRadius: '8px',
                      padding: '9px 10px 9px 32px',
                      color: '#0d0d0d',
                      fontSize: '0.84rem',
                      outline: 'none',
                    }}
                    onFocus={(e) => (e.target.style.borderColor = '#0d0d0d')}
                    onBlur={(e) => (e.target.style.borderColor = '#d1d5db')}
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || !regEmail.trim() || !regName.trim() || !regPassword.trim()}
              className="btn btn-primary"
              style={{
                width: '100%',
                padding: '10px',
                marginTop: 4,
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                fontSize: '0.88rem',
                fontWeight: 600,
              }}
            >
              <UserPlus size={16} />
              <span>{isLoading ? 'Creating Account...' : 'Complete Registration'}</span>
            </button>

            <div style={{ textAlign: 'center', fontSize: '0.82rem', color: '#6b7280', marginTop: 4 }}>
              Already registered?{' '}
              <button
                type="button"
                onClick={() => { setAuthMode('login'); setError(null); }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#0d0d0d',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0,
                }}
              >
                Sign in here
              </button>
            </div>
          </form>
        )}

        {/* Quick Demo Accounts */}
        <div style={{ borderTop: '1px solid #e5e7eb', marginTop: 20, paddingTop: 16 }}>
          <div style={{ fontSize: '0.74rem', color: '#6b7280', textAlign: 'center', marginBottom: 10, fontWeight: 500 }}>
            Quick Test Accounts:
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
            <button
              type="button"
              onClick={() => handleDemoSignIn('alex@university.edu', 'Alex (CSE Student)')}
              disabled={isLoading}
              className="btn btn-secondary"
              style={{ fontSize: '0.78rem', padding: '7px 10px', borderRadius: 8, border: '1px solid #e5e7eb' }}
            >
              Alex (Student A)
            </button>
            <button
              type="button"
              onClick={() => handleDemoSignIn('priya@university.edu', 'Priya (Scholar B)')}
              disabled={isLoading}
              className="btn btn-secondary"
              style={{ fontSize: '0.78rem', padding: '7px 10px', borderRadius: 8, border: '1px solid #e5e7eb' }}
            >
              Priya (Scholar B)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
