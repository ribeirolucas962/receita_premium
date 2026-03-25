// ============================================================
// Chef IA Premium — Módulo de API
// Centraliza todas as chamadas ao backend FastAPI
// ============================================================

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://receita-premium.onrender.com';
const TOKEN_KEY = 'chef_premium_token';
const USER_KEY  = 'chef_premium_user';

// ── Token ────────────────────────────────────────────────────
function getToken()          { return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY); }
function setToken(token)     { localStorage.setItem(TOKEN_KEY, token); }
function removeToken()       { localStorage.removeItem(TOKEN_KEY); sessionStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); }

function getUser()           { try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; } }
function setUser(user)       { localStorage.setItem(USER_KEY, JSON.stringify(user)); }

function estaLogado()        { return !!getToken(); }

// ── Fetch com autenticação ───────────────────────────────────
async function apiFetch(rota, opcoes = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(opcoes.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${rota}`, { ...opcoes, headers });

  if (res.status === 401) {
    removeToken();
    window.location.href = '/login.html';
    return;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Erro ${res.status}`);
  return data;
}

// ── Auth ─────────────────────────────────────────────────────
async function cadastrar(nome, email, senha) {
  const data = await apiFetch('/auth/cadastro', {
    method: 'POST',
    body: JSON.stringify({ nome, email, senha })
  });
  setToken(data.token);
  setUser({ nome: data.nome, plano: data.plano });
  return data;
}

async function login(email, senha) {
  const data = await apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, senha })
  });
  setToken(data.token);
  setUser({ nome: data.nome, plano: data.plano });
  return data;
}

async function logout() {
  removeToken();
  window.location.href = '/login.html';
}

async function carregarPerfil() {
  const data = await apiFetch('/auth/perfil');
  setUser({ nome: data.nome, plano: data.plano, email: data.email });
  return data;
}

// ── Receitas ─────────────────────────────────────────────────
async function listarReceitas(filtros = {}) {
  const params = new URLSearchParams();
  if (filtros.categoria)  params.set('categoria', filtros.categoria);
  if (filtros.dificuldade) params.set('dificuldade', filtros.dificuldade);
  const query = params.toString() ? `?${params}` : '';
  return apiFetch(`/receitas${query}`);
}

async function detalheReceita(id) {
  return apiFetch(`/receitas/${id}`);
}

// ── Favoritos ────────────────────────────────────────────────
async function listarFavoritos()       { return apiFetch('/favoritos'); }
async function salvarFavorito(id)      { return apiFetch(`/favoritos/${id}`, { method: 'POST' }); }
async function removerFavorito(id)     { return apiFetch(`/favoritos/${id}`, { method: 'DELETE' }); }

// ── Planos ───────────────────────────────────────────────────
async function listarPlanos()          { return apiFetch('/planos'); }

// ── Guard — redireciona se não logado ────────────────────────
function requireAuth() {
  if (!estaLogado()) {
    window.location.href = '/login.html';
    return false;
  }
  return true;
}

// ── Renderiza nome/plano no header se existir ────────────────
function renderUserHeader() {
  const user = getUser();
  const el   = document.getElementById('user-header');
  if (!el || !user) return;

  const badge = user.plano === 'gratuito'
    ? `<span class="plan-badge free">Gratuito</span>`
    : `<span class="plan-badge premium">${user.plano === 'anual' ? 'Anual' : 'Premium'}</span>`;

  el.innerHTML = `
    <span class="user-name">${user.nome.split(' ')[0]}</span>
    ${badge}
    <button class="logout-btn" onclick="logout()">Sair</button>
  `;
}
