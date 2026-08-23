// API client
const getApiBase = () => {
  let url = process.env.NEXT_PUBLIC_BACKEND_URL || '';
  if (url) {
    if (!url.includes('.') && !url.includes('localhost')) {
      url = `${url}.onrender.com`;
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = `https://${url}`;
    }
    return `${url.replace(/\/+$/, '')}/api`;
  }
  return '/api';
};

const API = getApiBase();

async function handleResponse(res: Response, defaultError: string) {
  const text = await res.text();
  let data: any;
  try {
    data = JSON.parse(text);
  } catch (e) {
    if (!res.ok) {
      throw new Error(text || `Server Error (${res.status})`);
    }
    throw new Error('Invalid server response');
  }

  if (!res.ok) {
    throw new Error(data?.detail || defaultError);
  }
  return data;
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('pp_token');
}

export function getUser(): Record<string, unknown> | null {
  if (typeof window === 'undefined') return null;
  const u = localStorage.getItem('pp_user');
  return u ? JSON.parse(u) : null;
}

export function setSession(token: string, user: Record<string, unknown>) {
  localStorage.setItem('pp_token', token);
  localStorage.setItem('pp_user', JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem('pp_token');
  localStorage.removeItem('pp_user');
}

export async function login(username: string, password: string) {
  const body = new URLSearchParams({ username, password });
  const res = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  return handleResponse(res, 'Login failed');
}

export interface Message { role: 'user' | 'assistant'; content: string; }

export async function sendChat(messages: Message[]) {
  let token = getToken();
  if (!token) {
    if (typeof window !== 'undefined') window.location.href = '/';
    throw new Error('Not authenticated');
  }

  let res = await fetch(`${API}/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ messages }),
  });

  if (res.status === 401) {
    const user = getUser();
    const username = (user?.username as string);
    if (!username) {
      if (typeof window !== 'undefined') window.location.href = '/';
      throw new Error('Session expired');
    }
    const authData = await login(username, 'pilot123');
    setSession(authData.access_token, authData.user);
    res = await fetch(`${API}/chat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authData.access_token}` },
      body: JSON.stringify({ messages }),
    });
  }

  return handleResponse(res, 'Chat failed');
}

export async function confirmAction(action_type: string, details: Record<string, unknown>, reason: string) {
  let token = getToken();
  if (!token) {
    if (typeof window !== 'undefined') window.location.href = '/';
    throw new Error('Not authenticated');
  }

  let res = await fetch(`${API}/chat/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ action_type, details, reason }),
  });

  if (res.status === 401) {
    const user = getUser();
    const username = (user?.username as string);
    if (!username) { if (typeof window !== 'undefined') window.location.href = '/'; throw new Error('Session expired'); }
    const authData = await login(username, 'pilot123');
    setSession(authData.access_token, authData.user);
    res = await fetch(`${API}/chat/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authData.access_token}` },
      body: JSON.stringify({ action_type, details, reason }),
    });
  }

  return handleResponse(res, 'Action failed');
}

export async function getProactiveIssues() {
  let token = getToken();
  if (!token) {
    if (typeof window !== 'undefined') window.location.href = '/';
    throw new Error('Not authenticated');
  }

  let res = await fetch(`${API}/dashboard/issues`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (res.status === 401) {
    const user = getUser();
    const username = (user?.username as string);
    if (!username) { if (typeof window !== 'undefined') window.location.href = '/'; throw new Error('Session expired'); }
    const authData = await login(username, 'pilot123');
    setSession(authData.access_token, authData.user);
    res = await fetch(`${API}/dashboard/issues`, {
      headers: { Authorization: `Bearer ${authData.access_token}` },
    });
  }

  return handleResponse(res, 'Failed to fetch issues');
}
