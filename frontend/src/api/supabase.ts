import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://abbtrncznmkpwobuxidh.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_YYRIJ0bFC7aX0SYBxH5k_g_LDlps3h5';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});

export interface UserProfile {
  id: string;
  email: string;
  name?: string;
}

export interface RegisteredUser {
  id: string;
  email: string;
  name: string;
  password?: string;
  createdAt: string;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(email: string): boolean {
  return EMAIL_REGEX.test(email.trim());
}

const REGISTERED_USERS_KEY = 'study_assistant_registered_users';

// Initialize default seed accounts so existing demo logins work smoothly
function initializeRegisteredUsers(): Record<string, RegisteredUser> {
  try {
    const raw = localStorage.getItem(REGISTERED_USERS_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (err) {
    console.warn('Error reading registered users:', err);
  }

  const defaultUsers: Record<string, RegisteredUser> = {
    'alex@university.edu': {
      id: 'alex@university.edu',
      email: 'alex@university.edu',
      name: 'Alex (CSE Student)',
      password: 'password123',
      createdAt: new Date().toISOString(),
    },
    'priya@university.edu': {
      id: 'priya@university.edu',
      email: 'priya@university.edu',
      name: 'Priya (Scholar B)',
      password: 'password123',
      createdAt: new Date().toISOString(),
    },
    'student@university.edu': {
      id: 'student@university.edu',
      email: 'student@university.edu',
      name: 'Student Scholar',
      password: 'password123',
      createdAt: new Date().toISOString(),
    },
  };

  try {
    localStorage.setItem(REGISTERED_USERS_KEY, JSON.stringify(defaultUsers));
  } catch {}

  return defaultUsers;
}

export function getRegisteredUsers(): Record<string, RegisteredUser> {
  return initializeRegisteredUsers();
}

export async function getCurrentUser(): Promise<UserProfile | null> {
  try {
    const localUser = localStorage.getItem('study_assistant_user');
    if (localUser) {
      return JSON.parse(localUser);
    }
    const sessionUser = sessionStorage.getItem('study_assistant_user');
    if (sessionUser) {
      return JSON.parse(sessionUser);
    }
  } catch (err) {
    console.warn('Error reading saved session:', err);
  }
  return null;
}

export async function registerAccount(
  name: string,
  email: string,
  password?: string
): Promise<UserProfile> {
  const cleanEmail = email.trim().toLowerCase();
  const cleanName = name.trim();

  if (!isValidEmail(cleanEmail)) {
    throw new Error('Please enter a valid email address (e.g. name@university.edu)');
  }

  if (!cleanName) {
    throw new Error('Please provide your full display name');
  }

  if (password !== undefined && password.trim().length < 6) {
    throw new Error('Password must be at least 6 characters long');
  }

  const registered = getRegisteredUsers();

  if (registered[cleanEmail]) {
    throw new Error('An account with this email already exists. Please sign in instead.');
  }

  const newUser: RegisteredUser = {
    id: cleanEmail,
    email: cleanEmail,
    name: cleanName,
    password: password ? password.trim() : 'password123',
    createdAt: new Date().toISOString(),
  };

  registered[cleanEmail] = newUser;
  try {
    localStorage.setItem(REGISTERED_USERS_KEY, JSON.stringify(registered));
  } catch (err) {
    console.error('Failed to save registered user:', err);
  }

  return {
    id: cleanEmail,
    email: cleanEmail,
    name: cleanName,
  };
}

export async function loginAccount(
  email: string,
  password?: string,
  rememberMe = true
): Promise<UserProfile> {
  const cleanEmail = email.trim().toLowerCase();
  if (!isValidEmail(cleanEmail)) {
    throw new Error('Please enter a valid email address (e.g. name@university.edu)');
  }

  const registered = getRegisteredUsers();
  const userRecord = registered[cleanEmail];

  if (!userRecord) {
    throw new Error('Account not found with this email. Please register first.');
  }

  if (password && userRecord.password && userRecord.password !== password.trim()) {
    throw new Error('Incorrect password. Please verify your password and try again.');
  }

  const profile: UserProfile = {
    id: userRecord.id,
    email: userRecord.email,
    name: userRecord.name,
  };

  const serialized = JSON.stringify(profile);
  if (rememberMe) {
    localStorage.setItem('study_assistant_user', serialized);
  } else {
    sessionStorage.setItem('study_assistant_user', serialized);
  }

  return profile;
}

export async function loginWithValidEmail(
  email: string,
  name?: string,
  rememberMe = true
): Promise<UserProfile> {
  const cleanEmail = email.trim().toLowerCase();
  if (!isValidEmail(cleanEmail)) {
    throw new Error('Please enter a valid email address (e.g. user@domain.com)');
  }

  const registered = getRegisteredUsers();
  let userRecord = registered[cleanEmail];

  if (!userRecord) {
    // If not registered yet, auto-register for seamless testing
    userRecord = {
      id: cleanEmail,
      email: cleanEmail,
      name: name?.trim() || cleanEmail.split('@')[0],
      password: 'password123',
      createdAt: new Date().toISOString(),
    };
    registered[cleanEmail] = userRecord;
    try {
      localStorage.setItem(REGISTERED_USERS_KEY, JSON.stringify(registered));
    } catch {}
  }

  const profile: UserProfile = {
    id: cleanEmail,
    email: cleanEmail,
    name: userRecord.name || (name?.trim() || cleanEmail.split('@')[0]),
  };

  const serialized = JSON.stringify(profile);
  if (rememberMe) {
    localStorage.setItem('study_assistant_user', serialized);
  } else {
    sessionStorage.setItem('study_assistant_user', serialized);
  }

  return profile;
}

export async function demoLogin(name = 'Student Scholar'): Promise<UserProfile> {
  return loginWithValidEmail('student@university.edu', name, true);
}

export async function logoutUser(): Promise<void> {
  localStorage.removeItem('study_assistant_user');
  sessionStorage.removeItem('study_assistant_user');
  try {
    await supabase.auth.signOut().catch(() => {});
  } catch {}
}


