/**
 * BankSathi — One-Stop Indian Banking & Decision Assistant
 *
 * Provides dual-mode execution (FastAPI backend + robust client-side fallback),
 * multi-bank comparison, scheme finder, transparent EMI calculations, and emergency desk.
 */

const state = {
  knowledge: [],
  banks: [],
  backendAvailable: true,
  activeView: 'chat',
  seniorCitizenFD: false,
};

let BACKEND_BASE = 'http://127.0.0.1:8001';

// Currency Formatter (INR)
function formatINR(num) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(num);
}

// ---------------------------------------------------------------------------
// Initialization & Data Loading
// ---------------------------------------------------------------------------
async function initApp() {
  // 1. Immediately setup views & chatbot on millisecond 0 (never blocked)
  setupNavigation();
  setupChatbot();
  setupBankSelector();
  setupSchemeFinder();
  setupEMICalculator();
  setupEmergencyDesk();

  // 2. Load Local Static Data (Banks and Schemes)
  try {
    const [kbRes, banksRes] = await Promise.all([
      fetch('data/banking-knowledge.json'),
      fetch('data/banks-data.json')
    ]);
    const kbData = await kbRes.json();
    const banksData = await banksRes.json();
    state.knowledge = kbData.entries || [];
    state.banks = banksData.banks || [];
    if (typeof renderBankCards === 'function') renderBankCards();
    if (typeof renderBestRateBanner === 'function') renderBestRateBanner();
  } catch (err) {
    console.error('Error loading static data:', err);
  }

  // 3. Probe backend in background with fast 1.2s timeout (checks 8001 first, then 8000, 8080)
  const candidatePorts = ['8001', '8000', '8080'];
  state.backendAvailable = false;

  for (const port of candidatePorts) {
    try {
      const url = `http://127.0.0.1:${port}`;
      const healthRes = await fetch(`${url}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(1200),
      });
      if (healthRes.ok) {
        const hData = await healthRes.json();
        if (hData.service === 'BankSathi') {
          BACKEND_BASE = url;
          state.backendAvailable = true;
          const statusEl = document.getElementById('backendStatus');
          if (statusEl) {
            statusEl.textContent = 'Backend Active · Gemini AI & Bank Data Connected';
            statusEl.style.color = '#86efac';
          }
          break;
        }
      }
    } catch {
      // ignore and try next candidate
    }
  }

  if (!state.backendAvailable) {
    const statusEl = document.getElementById('backendStatus');
    if (statusEl) {
      statusEl.textContent = 'Client Engine · 8 Banks & Schemes Loaded';
    }
  }
}

// ---------------------------------------------------------------------------
// Navigation Management
// ---------------------------------------------------------------------------
function setupNavigation() {
  const navButtons = document.querySelectorAll('.nav-item');
  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const viewId = btn.dataset.view;
      if (!viewId) return;

      navButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      document.querySelectorAll('.panel').forEach(panel => {
        panel.classList.remove('active');
        panel.classList.add('hidden');
      });

      const activePanel = document.getElementById(viewId);
      if (activePanel) {
        activePanel.classList.remove('hidden');
        activePanel.classList.add('active');
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Conversational AI Assistant
// ---------------------------------------------------------------------------
function setupChatbot() {
  const conversation = document.getElementById('conversation');
  const chatForm = document.getElementById('chatForm');
  const questionInput = document.getElementById('question');
  const clearBtn = document.getElementById('clearChat');
  const welcomeTemplate = document.getElementById('welcomeMessage');

  // Insert welcome message
  conversation.appendChild(welcomeTemplate.content.cloneNode(true));

  // Initialize Google-like search autocomplete
  setupAutocomplete(questionInput, chatForm);

  // Delegated click handler for suggestion chips inside chat
  conversation.addEventListener('click', (e) => {
    const chip = e.target.closest('[data-chip-query]');
    if (chip) {
      const q = chip.getAttribute('data-chip-query');
      if (q) {
        questionInput.value = q;
        chatForm.dispatchEvent(new Event('submit'));
      }
    }
  });

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = questionInput.value.trim();
    if (!query) return;

    // Hide suggestions on submit
    const dropdown = document.getElementById('autocompleteDropdown');
    if (dropdown) dropdown.classList.add('hidden');

    addChatMessage(query, 'user');
    questionInput.value = '';

    // Show temporary typing status
    const botMsgEl = addChatMessage('Analyzing your banking query...', 'bot', true);

    const responseHTML = (await processChatQuery(query)) || generateClientResponse(query.toLowerCase(), query);
    botMsgEl.innerHTML = `<div class="avatar">₹</div><div class="bubble">${responseHTML}</div>`;
  });

  // Quick Chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', async () => {
      const text = chip.textContent;
      addChatMessage(text, 'user');
      const botMsgEl = addChatMessage('Thinking...', 'bot', true);
      const responseHTML = (await processChatQuery(text)) || generateClientResponse(text.toLowerCase(), text);
      botMsgEl.innerHTML = `<div class="avatar">₹</div><div class="bubble">${responseHTML}</div>`;
    });
  });

  clearBtn.addEventListener('click', () => {
    conversation.innerHTML = '';
    conversation.appendChild(welcomeTemplate.content.cloneNode(true));
  });
}

// ---------------------------------------------------------------------------
// Google-Like Search Autocomplete Engine
// ---------------------------------------------------------------------------
const AUTOCOMPLETE_SUGGESTIONS = [
  { text: "Compare SBI vs HDFC FD rates", category: "Comparison" },
  { text: "Compare SBI vs ICICI vs Axis home loan", category: "Comparison" },
  { text: "Which bank offers the highest FD rate?", category: "FD Rates" },
  { text: "Which bank best for 50+ and senior citizens", category: "Senior Citizens" },
  { text: "Bank account opening age guidelines in India", category: "RBI Rules" },
  { text: "Invest 1000 per month best bank scheme", category: "Monthly Savings" },
  { text: "Saving account which bank is best", category: "Savings Account" },
  { text: "Zero interest loan for 1 month options", category: "Credit" },
  { text: "Best bank for students and education loans", category: "Students" },
  { text: "MUDRA loan for small business and shopkeeper", category: "Business Credit" },
  { text: "Stand-Up India loan for women entrepreneurs", category: "Women Scheme" },
  { text: "Sukanya Samriddhi Yojana eligibility and 8.20% rate", category: "Small Savings" },
  { text: "Public Provident Fund (PPF) 7.10% tax free", category: "Tax Saving" },
  { text: "Atal Pension Yojana (APY) monthly chart", category: "Pension" },
  { text: "Senior Citizens Savings Scheme (SCSS 8.20%)", category: "Senior Citizens" },
  { text: "Mahila Samman Savings Certificate (MSSC 7.50%)", category: "Women Scheme" },
  { text: "Post Office Monthly Income Scheme (POMIS)", category: "Monthly Income" },
  { text: "Kisan Credit Card (KCC) 4% agriculture loan", category: "Farmers" },
  { text: "ATM cash not dispensed but money deducted", category: "Dispute Help" },
  { text: "UPI failed money deducted from bank account", category: "UPI Help" },
  { text: "Someone called asking for my bank OTP", category: "Fraud Emergency" },
  { text: "How to file complaint to RBI Banking Ombudsman", category: "Grievance" },
  { text: "Total bank in portal and supported banks", category: "Portal Info" },
  { text: "Kotak 811 zero balance account features", category: "Zero Balance" },
  { text: "AU Small Finance Bank 8.50% FD returns", category: "High Yield SFB" },
  { text: "Equitas Small Finance Bank 7.25% savings", category: "High Yield SFB" },
  { text: "India Post Payments Bank (IPPB) doorstep banking", category: "Payments Bank" },
  { text: "Standard Chartered Bank international accounts", category: "Foreign Bank" },
  { text: "HSBC India premier zero fee remittances", category: "Foreign Bank" },
  { text: "DICGC 5 lakh bank deposit insurance safety", category: "Consumer Rights" },
  { text: "Positive Pay System for high value cheques", category: "Security" },
  { text: "What is CIBIL credit score required for home loan", category: "Loan Eligibility" }
];

function setupAutocomplete(inputEl, formEl) {
  const dropdown = document.getElementById('autocompleteDropdown');
  if (!dropdown || !inputEl) return;

  let activeIndex = -1;
  let currentMatches = [];

  function renderSuggestions(matches, query) {
    currentMatches = matches;
    activeIndex = -1;

    if (!matches.length) {
      dropdown.classList.add('hidden');
      dropdown.innerHTML = '';
      return;
    }

    const qLower = query.toLowerCase();
    dropdown.innerHTML = matches.map((item, idx) => {
      // Highlight matching substring
      const text = item.text;
      const matchPos = text.toLowerCase().indexOf(qLower);
      let displayHTML = text;
      if (matchPos !== -1) {
        const before = text.substring(0, matchPos);
        const match = text.substring(matchPos, matchPos + query.length);
        const after = text.substring(matchPos + query.length);
        displayHTML = `${escapeHTML(before)}<span class="match-text">${escapeHTML(match)}</span>${escapeHTML(after)}`;
      }

      return `
        <div class="autocomplete-item" data-index="${idx}">
          <span class="search-icon">🔍</span>
          <span>${displayHTML}</span>
          <span class="category-tag">${escapeHTML(item.category)}</span>
        </div>
      `;
    }).join('');

    dropdown.classList.remove('hidden');

    // Click handler for items
    dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
      item.addEventListener('mousedown', (e) => {
        e.preventDefault();
        const idx = parseInt(item.getAttribute('data-index'), 10);
        if (currentMatches[idx]) {
          inputEl.value = currentMatches[idx].text;
          dropdown.classList.add('hidden');
          formEl.dispatchEvent(new Event('submit'));
        }
      });
    });
  }

  // Live Input Listener with Debounce
  let debounceTimer;
  inputEl.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = inputEl.value.trim();

    if (q.length < 1) {
      dropdown.classList.add('hidden');
      dropdown.innerHTML = '';
      return;
    }

    debounceTimer = setTimeout(() => {
      const qLower = q.toLowerCase();
      // Match from curated list + dynamic banks + schemes
      const matches = AUTOCOMPLETE_SUGGESTIONS.filter(s => 
        s.text.toLowerCase().includes(qLower) || s.category.toLowerCase().includes(qLower)
      ).slice(0, 6);

      renderSuggestions(matches, q);
    }, 80);
  });

  // Keyboard navigation
  inputEl.addEventListener('keydown', (e) => {
    if (dropdown.classList.contains('hidden') || !currentMatches.length) return;

    const items = dropdown.querySelectorAll('.autocomplete-item');

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      updateActiveItem(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
      updateActiveItem(items);
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0 && currentMatches[activeIndex]) {
        e.preventDefault();
        inputEl.value = currentMatches[activeIndex].text;
        dropdown.classList.add('hidden');
        formEl.dispatchEvent(new Event('submit'));
      }
    } else if (e.key === 'Escape') {
      dropdown.classList.add('hidden');
    }
  });

  function updateActiveItem(items) {
    items.forEach((it, i) => {
      if (i === activeIndex) {
        it.classList.add('active');
        inputEl.value = currentMatches[i].text;
      } else {
        it.classList.remove('active');
      }
    });
  }

  // Close when clicking outside
  document.addEventListener('click', (e) => {
    if (!inputEl.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });
}

function addChatMessage(text, sender = 'user', isTemporary = false) {
  const conversation = document.getElementById('conversation');
  const article = document.createElement('article');
  article.className = `chat-message ${sender}`;

  if (sender === 'user') {
    article.innerHTML = `<div class="bubble">${escapeHTML(text)}</div>`;
  } else {
    article.innerHTML = `<div class="avatar">₹</div><div class="bubble">${text}</div>`;
  }

  conversation.appendChild(article);
  article.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return article;
}

async function processChatQuery(query) {
  const qLower = query.toLowerCase();

  // Try FastAPI backend if active
  if (state.backendAvailable) {
    try {
      const res = await fetch(`${BACKEND_BASE}/api/intent/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: 3 }),
        signal: AbortSignal.timeout(25000),
      });
      if (res.ok) {
        const data = await res.json();
        const formatted = formatBackendResponse(data, query);
        if (formatted && formatted.trim()) {
          return formatted;
        }
      }
    } catch (e) {
      console.warn('Backend query failed, using client fallback:', e);
    }
  }

  // Client-Side Intelligence Engine
  return generateClientResponse(qLower, query);
}

function renderMarkdown(md) {
  if (!md) return '';
  // Basic HTML escape
  let text = String(md)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Headers
  text = text.replace(/^### (.*$)/gim, '<h4 class="ai-h3">$1</h4>');
  text = text.replace(/^## (.*$)/gim, '<h3 class="ai-h2">$1</h3>');
  text = text.replace(/^# (.*$)/gim, '<h2 class="ai-h1">$1</h2>');

  // Bold & Italic
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Markdown links [text](url)
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1 ↗</a>');

  // Bullet items (lines starting with - or * or •)
  text = text.replace(/^\s*[-*•]\s+(.*$)/gim, '<li class="ai-li">$1</li>');
  // Group bullet items into ul
  text = text.replace(/((?:<li class="ai-li">.*?<\/li>\s*)+)/gs, '<ul class="ai-ul">$1</ul>');

  // Numbered list items (e.g. 1. 2.)
  text = text.replace(/^\s*(\d+)\.\s+(.*$)/gim, '<li class="ai-oli"><strong>$1.</strong> $2</li>');
  // Group numbered items into ol
  text = text.replace(/((?:<li class="ai-oli">.*?<\/li>\s*)+)/gs, '<ol class="ai-ol">$1</ol>');

  // Paragraphs
  const paragraphs = text.split(/\n{2,}/);
  text = paragraphs.map(p => {
    p = p.trim();
    if (!p) return '';
    if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol')) return p;
    return `<p class="ai-p">${p.replace(/\n/g, '<br>')}</p>`;
  }).join('');

  return `<div class="ai-text-block">${text}</div>`;
}

function formatBackendResponse(data, rawQuery) {
  // 1. If Gemini Generative AI response is available (Online Mode)
  if (data.ai_response && data.ai_response.trim()) {
    return `<div class="ai-card-wrapper">${renderMarkdown(data.ai_response)}</div>`;
  }

  // 2. Offline / Local Intelligence Mode (Zero Internet)
  let html = `
    <div class="ai-badge-header">
      <span class="tag-badge tag-offline"><span class="offline-icon">⚡</span> Local Bank Intelligence (Offline Mode · Zero Internet)</span>
      <span class="chat-meta-badge">Intent: ${data.intent} · Lang: ${data.language} (${Math.round(data.confidence * 100)}%)</span>
    </div>
  `;

  if (data.bank_response) {
    const br = data.bank_response;
    // Portal Banks Roster
    if (br.type === 'portal_banks_list') {
      html += `<strong>🏛️ ${br.title}</strong><p>${br.summary}</p>`;
      html += `<div style="display:flex; flex-direction:column; gap:6px; margin-top:8px;">`;
      if (br.public_sector && br.public_sector.length) {
        html += `<div style="background:#f1f5f9; padding:8px 12px; border-radius:6px;"><b>Public Sector PSUs:</b> ${br.public_sector.join(', ')}</div>`;
      }
      if (br.private_sector && br.private_sector.length) {
        html += `<div style="background:#f8fafc; padding:8px 12px; border-radius:6px; border:1px solid #e2e8f0;"><b>Private Sector Banks:</b> ${br.private_sector.join(', ')}</div>`;
      }
      if (br.small_finance && br.small_finance.length) {
        html += `<div style="background:#faf5ff; padding:8px 12px; border-radius:6px; border:1px solid #e9d5ff;"><b>Small Finance Banks (High Returns):</b> ${br.small_finance.join(', ')}</div>`;
      }
      if (br.international && br.international.length) {
        html += `<div style="background:#f0fdf4; padding:8px 12px; border-radius:6px; border:1px solid #bbf7d0;"><b>Foreign / International Banks:</b> ${br.international.join(', ')}</div>`;
      }
      if (br.payments_bank && br.payments_bank.length) {
        html += `<div style="background:#fff7ed; padding:8px 12px; border-radius:6px; border:1px solid #fed7aa;"><b>Payments Banks (Doorstep):</b> ${br.payments_bank.join(', ')}</div>`;
      }
      html += `</div><p style="font-size:0.8rem; color:#475569; margin-top:6px;">${br.features_tracked}</p>`;
      return html;
    }

    // IFSC & Branch Info (Offline Mode)
    if (br.type === 'ifsc_branch_info') {
      html += `
        <strong>🏛️ ${br.bank_name} — ${br.branch}</strong>
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:10px 14px; margin:8px 0;">
          <div style="font-size:0.85rem; color:#166534;">Verified 11-Character IFSC Code:</div>
          <div style="font-size:1.3rem; font-weight:700; color:#15803d; letter-spacing:1px; margin:4px 0;">${br.ifsc}</div>
          <div style="font-size:0.82rem; color:#475569;"><b>MICR Code:</b> ${br.micr} · <b>Address:</b> ${br.address}</div>
        </div>
        <p style="font-size:0.82rem; color:#64748b;">Format: First 4 letters bank code, 5th character '0', last 6 characters branch code.</p>
        <p><a href="${br.rbi_portal}" target="_blank" rel="noopener">Search on Official RBI IFSC Portal ↗</a></p>
      `;
      return html;
    }

    // Generic IFSC Guide
    if (br.type === 'ifsc_generic_guide') {
      html += `
        <strong>🔍 ${br.title}</strong>
        <p>${br.summary}</p>
        <p style="font-size:0.85rem; background:#f8fafc; padding:6px 10px; border-radius:6px; border:1px solid #e2e8f0;"><b>${br.structure}</b></p>
        <ul>
      `;
      br.check_sources.forEach(s => {
        html += `<li>${s}</li>`;
      });
      html += `</ul><p><a href="${br.official_portal}" target="_blank" rel="noopener">Visit RBI Official IFSC Directory ↗</a></p>`;
      return html;
    }

    // Account Opening Age Guidelines
    if (br.type === 'account_age_guidelines') {
      html += `<strong>📅 ${br.title}</strong><p>${br.summary}</p><div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">`;
      br.age_brackets.forEach(b => {
        html += `
          <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:8px 10px;">
            <b style="color:#0369a1;">${b.bracket}</b>
            <p style="font-size:0.84rem; margin:2px 0;">${b.rules}</p>
          </div>
        `;
      });
      html += `</div><p style="margin-top:6px;"><a href="${br.official_portal}" target="_blank" rel="noopener">RBI Official Portal ↗</a></p>`;
      return html;
    }

    // Monthly Investment Guide
    if (br.type === 'monthly_investment_guide') {
      html += `<strong>💰 ${br.title}</strong><p>${br.summary}</p><div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">`;
      br.schemes.forEach(s => {
        html += `
          <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:8px 10px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <b style="color:#166534;">${s.name}</b>
              <span class="tag-badge badge-success" style="font-size:0.75rem;">${s.expected_return}</span>
            </div>
            <p style="font-size:0.82rem; margin:4px 0 0 0; color:#374151;">${s.details}</p>
          </div>
        `;
      });
      html += `</div>`;
      return html;
    }

    // Savings Account Ranking
    if (br.type === 'savings_ranking') {
      html += `<strong>🏦 ${br.title}</strong><p>${br.summary}</p><div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">`;
      br.recommendations.forEach(r => {
        html += `
          <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:8px 10px;">
            <b style="color:#1d4ed8;">${r.bank}</b>
            <p style="font-size:0.84rem; margin:2px 0 0 0;">${r.highlights}</p>
          </div>
        `;
      });
      html += `</div>`;
      return html;
    }

    // Student Recommendation
    if (br.type === 'student_recommendation') {
      html += `<strong>🎓 ${br.title}</strong><p>${br.summary}</p><div style="display:flex; flex-direction:column; gap:10px; margin-top:8px;">`;
      br.recommendations.forEach(r => {
        html += `
          <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px 12px;">
            <b style="color:#2563eb;">${r.bank}</b> <span class="tag-badge" style="margin-left:6px; font-size:0.68rem;">${r.category}</span>
            <p style="font-size:0.84rem; margin:4px 0;">${r.highlights}</p>
            <p style="font-size:0.8rem; color:#475569;"><b>Education Loan:</b> ${r.education_loan}</p>
          </div>
        `;
      });
      html += `</div><p style="margin-top:8px;"><a href="${br.official_portal}" target="_blank" rel="noopener">Check ${br.portal_name} ↗</a></p>`;
      return html;
    }

    // Zero Interest / 1-Month Loan
    if (br.type === 'zero_interest_loan') {
      html += `<strong>💳 ${br.title}</strong><p>${br.summary}</p><ul>`;
      br.options.forEach(opt => {
        html += `<li><b>${opt.method}:</b> ${opt.details}</li>`;
      });
      html += `</ul><div class="tag-badge badge-danger" style="margin-top:8px;">${br.warning}</div>`;
      return html;
    }

    // Senior Citizen
    if (br.type === 'senior_citizen_recommendation') {
      html += `<strong>👴 ${br.title}</strong><p>${br.summary}</p><div class="bank-specs-grid" style="margin-top:8px;">`;
      br.top_banks.forEach(b => {
        html += `
          <div class="spec-item" style="border-left:3px solid #f59e0b; padding-left:8px;">
            <b>${b.short_name} (${b.type})</b>
            <span>Peak Rate: <b style="color:#2563eb;">${b.peak_rate_display}</b></span>
            <span>Scheme: ${b.special_scheme}</span>
          </div>
        `;
      });
      html += `</div>`;
      return html;
    }

    // Women Entrepreneur / Mahila
    if (br.type === 'women_recommendation') {
      html += `<strong>👩 ${br.title}</strong><p>${br.summary}</p><div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">`;
      br.recommendations.forEach(r => {
        html += `
          <div style="background:#fdf2f8; border:1px solid #fbcfe8; border-radius:8px; padding:8px 12px;">
            <b style="color:#be185d;">${r.scheme}</b>
            <p style="font-size:0.84rem; margin:3px 0;">${r.coverage}</p>
          </div>
        `;
      });
      html += `</div><p style="margin-top:6px;"><a href="${br.official_portal}" target="_blank" rel="noopener">Stand-Up Mitra Portal ↗</a></p>`;
      return html;
    }

    // Business & MSME / Shopkeeper
    if (br.type === 'business_recommendation') {
      html += `<strong>🏬 ${br.title}</strong><p>${br.summary}</p><ul>`;
      br.options.forEach(opt => {
        html += `<li><b>${opt.name}:</b> ${opt.details}</li>`;
      });
      html += `</ul><p><a href="${br.official_portal}" target="_blank" rel="noopener">Official MUDRA Portal ↗</a></p>`;
      return html;
    }

    // Fixed Deposit Rate Ranking
    if (br.type === 'fd_rate_ranking') {
      html += `<strong>📈 ${br.title}</strong><p>${br.summary}</p><div class="bank-specs-grid" style="margin-top:8px;">`;
      br.top_banks.forEach(b => {
        html += `
          <div class="spec-item" style="border-left:3px solid #10b981; padding-left:8px;">
            <b>${b.short_name} (${b.type})</b>
            <span>1-Yr: <b>${b.rate_1yr}</b></span>
            <span>Peak: <b style="color:#2563eb;">${b.peak_rate_display}</b> (${b.special_scheme})</span>
          </div>
        `;
      });
      html += `</div><p style="font-size:0.8rem; color:#047857; margin-top:6px;">${br.safety_note}</p>`;
      return html;
    }

    // Home Loan Ranking
    if (br.type === 'home_loan_ranking') {
      html += `<strong>🏠 ${br.title}</strong><p>${br.summary}</p><div class="bank-specs-grid" style="margin-top:8px;">`;
      br.top_banks.forEach(b => {
        html += `
          <div class="spec-item" style="border-left:3px solid #3b82f6; padding-left:8px;">
            <b>${b.short_name} (${b.type})</b>
            <span>Starting: <b style="color:#2563eb;">${b.starting_rate_display}</b></span>
            <span>Fee: ${b.processing_fee}</span>
          </div>
        `;
      });
      html += `</div><p style="font-size:0.8rem; color:#1e40af; margin-top:6px;">${br.tip}</p>`;
      return html;
    }

    // Transaction Dispute
    if (br.type === 'transaction_dispute') {
      html += `<strong>⚠️ ${br.title}</strong><p>${br.summary}</p><ul>`;
      br.steps.forEach(s => {
        html += `<li>${s}</li>`;
      });
      html += `</ul><p style="font-size:0.82rem; color:#475569;"><b>Dispute Line:</b> ${br.helpline}</p>`;
      return html;
    }

    // Fraud / Security Alert
    if (br.type === 'fraud_security_alert') {
      html += `<div class="tag-badge badge-danger">High Priority Action</div>`;
      html += `<strong>${br.title}</strong><p>${br.summary}</p><ul>`;
      br.actions.forEach(a => {
        html += `<li>${a}</li>`;
      });
      html += `</ul><p><a href="${br.cyber_portal}" target="_blank" rel="noopener">National Cybercrime Reporting Portal ↗</a></p>`;
      return html;
    }

    // Greeting
    if (br.type === 'greeting') {
      html += `<strong>${br.title}</strong><p>${br.summary}</p><div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:8px;">`;
      br.suggestions.forEach(s => {
        const cleanVal = s.replace(/^[^\w]+/, '').trim();
        html += `<span class="chip" style="font-size:0.8rem; cursor:pointer;" data-chip-query="${escapeHTML(cleanVal)}">${escapeHTML(s)}</span>`;
      });
      html += `</div>`;
      return html;
    }

    // Single Bank Detail
    if (br.type === 'bank_detail' && br.bank) {
      const b = br.bank;
      html += `<strong>${b.name} (${b.shortName})</strong><p>${br.summary}</p>`;
      html += `
        <ul>
          <li><b>Savings Interest:</b> ${b.savings.interestRate.upTo10Lakh}% p.a. (Min balance in Metro: ₹${b.savings.minBalance.metro.toLocaleString('en-IN')})</li>
          <li><b>Fixed Deposit (1-Year):</b> ${b.fixedDeposit.rate1Year.general}% (Senior Citizen: ${b.fixedDeposit.rate1Year.seniorCitizen}%)</li>
          <li><b>Home Loan Starting:</b> ${b.loans.homeLoan.startingRate}% p.a. (${b.loans.homeLoan.benchmarkType})</li>
          <li><b>24x7 Customer Care:</b> ${b.customerSupport.tollFree.join(', ')}</li>
        </ul>
        <p><a href="${b.customerSupport.officialWebsite}" target="_blank" rel="noopener">Official ${b.shortName} Portal ↗</a></p>
      `;
      return html;
    }
  }

  // Standard Knowledge Base Match
  const qClean = canonicalizeQuery(rawQuery);
  const matchedSchemes = state.knowledge.filter(k => {
    const hay = `${k.name} ${k.category} ${k.tags.join(' ')} ${k.summary}`.toLowerCase();
    return hay.includes(data.intent.toLowerCase().replace('_', ' '));
  });

  if (matchedSchemes.length > 0) {
    const s = matchedSchemes[0];
    html += `<strong>${s.name}</strong><p>${s.summary}</p><p><b>Eligibility:</b> ${s.eligibility}</p><p><b>Key Benefit:</b> ${s.benefits[0]}</p><p><a href="${s.source}" target="_blank" rel="noopener">Official ${s.authority} Source ↗</a></p>`;
    return html;
  }

  return generateClientResponse(rawQuery.toLowerCase(), rawQuery);
}

function canonicalizeQuery(text) {
  return text.toLowerCase()
    .replace(/\bload\b/g, 'loan')
    .replace(/\bloam\b/g, 'loan')
    .replace(/\blaon\b/g, 'loan')
    .replace(/\bintrest\b/g, 'interest')
    .replace(/\bbyaj\b/g, 'interest')
    .replace(/\bbyaaj\b/g, 'interest');
}

function generateClientResponse(qLower, rawQuery) {
  const qClean = canonicalizeQuery(qLower).trim();

  // 0. Greetings
  if (["hi", "hii", "hiii", "hello", "helo", "hey", "namaste", "namaskar", "good morning", "good afternoon", "good evening", "kaise ho", "kya haal hai"].includes(qClean)) {
    return `
      <strong>Namaste! Welcome to BankSathi 🇮🇳</strong>
      <p>I am your one-stop Indian Banking Decision & Problem Assistant. How can I help you today?</p>
      <div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:8px;">
        <span class="chip" style="font-size:0.8rem; cursor:pointer;" data-chip-query="Best bank for students">🎓 Best bank for students</span>
        <span class="chip" style="font-size:0.8rem; cursor:pointer;" data-chip-query="Which bank offers highest FD rate?">📈 Highest FD rates</span>
        <span class="chip" style="font-size:0.8rem; cursor:pointer;" data-chip-query="Zero interest loan for 1 month">💳 0% 1-Month Credit</span>
        <span class="chip" style="font-size:0.8rem; cursor:pointer;" data-chip-query="Compare SBI vs HDFC">⇋ Compare SBI vs HDFC</span>
      </div>
    `;
  }

  // 1. Total Banks in Portal / Supported Banks Roster
  if (['total bank', 'how many bank', 'supported bank', 'all banks', 'list of bank', 'kitne bank', 'which banks are available'].some(t => qClean.includes(t))) {
    const banks = state.banks;
    const psus = banks.filter(b => b.type === 'Public Sector').map(b => `${b.name} (${b.shortName})`);
    const pvt = banks.filter(b => b.type === 'Private Sector').map(b => `${b.name} (${b.shortName})`);
    const sfb = banks.filter(b => b.type === 'Small Finance Bank').map(b => `${b.name} (${b.shortName})`);
    const intl = banks.filter(b => b.type.includes('Foreign') || b.type.includes('International')).map(b => `${b.name} (${b.shortName})`);
    const pay = banks.filter(b => b.type === 'Payments Bank').map(b => `${b.name} (${b.shortName})`);
    return `
      <strong>🏛️ Supported Banks in BankSathi (${banks.length} Major Indian Banks)</strong>
      <p>BankSathi tracks live verified benchmark data, interest rates, minimum balances, and emergency contacts across ${banks.length} leading banks in India:</p>
      <div style="display:flex; flex-direction:column; gap:6px; margin-top:8px;">
        <div style="background:#f1f5f9; padding:8px 12px; border-radius:6px;"><b>Public Sector PSUs:</b> ${psus.join(', ')}</div>
        <div style="background:#f8fafc; padding:8px 12px; border-radius:6px; border:1px solid #e2e8f0;"><b>Private Sector Banks:</b> ${pvt.join(', ')}</div>
        <div style="background:#faf5ff; padding:8px 12px; border-radius:6px; border:1px solid #e9d5ff;"><b>Small Finance Banks (High Returns):</b> ${sfb.join(', ')}</div>
        <div style="background:#f0fdf4; padding:8px 12px; border-radius:6px; border:1px solid #bbf7d0;"><b>Foreign / International:</b> ${intl.join(', ')}</div>
        <div style="background:#fff7ed; padding:8px 12px; border-radius:6px; border:1px solid #fed7aa;"><b>Payments Banks (Doorstep):</b> ${pay.join(', ')}</div>
      </div>
      <p style="font-size:0.8rem; color:#475569; margin-top:6px;">Features tracked: Savings MAB, 1/3/5-Yr FDs, Home/Personal/Education Loans, ATM Limits, and 24x7 Emergency Desks.</p>
    `;
  }

  // 2. Bank Account Opening Age Guidelines (RBI Rules)
  if (['age to open', 'minimum age', 'minor account', 'age limit', 'age for bank', 'how old to open', 'bachho ka account', 'minor khata'].some(t => qClean.includes(t))) {
    return `
      <strong>📅 Bank Account Opening Age Guidelines in India (RBI Rules)</strong>
      <p>Anyone from newborn infants to senior citizens can hold a bank account in India under distinct regulatory brackets:</p>
      <div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:8px 10px;">
          <b style="color:#0369a1;">👶 Minors Under 10 Years</b>
          <p style="font-size:0.84rem; margin:2px 0;">Joint Savings Account operated jointly by the natural parent or legal guardian (e.g., Sukanya Samriddhi for girl children).</p>
        </div>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:8px 10px;">
          <b style="color:#0369a1;">🧒 Minors Aged 10 to 18 Years</b>
          <p style="font-size:0.84rem; margin:2px 0;">Can independently open and operate Savings Accounts (e.g., SBI Pehla Kadam / Pehli Udaan) with debit card, mobile banking, and internet banking limits.</p>
        </div>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:8px 10px;">
          <b style="color:#0369a1;">🧑 Adults Aged 18 to 59 Years</b>
          <p style="font-size:0.84rem; margin:2px 0;">Full independent banking including individual savings/current accounts, credit cards, personal/home loans, and demat investment accounts.</p>
        </div>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:8px 10px;">
          <b style="color:#0369a1;">👴 Senior Citizens Aged 60+ Years</b>
          <p style="font-size:0.84rem; margin:2px 0;">Eligible for Senior Citizen accounts with preferential FD rates (+0.50% to +0.75%), doorstep banking, and dedicated branch priority queues.</p>
        </div>
      </div>
      <p style="margin-top:6px;"><a href="https://rbi.org.in/" target="_blank" rel="noopener">RBI Official Portal ↗</a></p>
    `;
  }

  // 3. Monthly Investment & Savings (₹500 / ₹1000 per month / RD / PPF / SIP)
  if (['per month', 'per moth', 'monthly invest', 'invest 1000', 'invest 500', 'har mahine', 'recurring deposit', 'rd scheme', 'small invest'].some(t => qClean.includes(t))) {
    return `
      <strong>💰 Best Monthly Investment Schemes in India (₹500 – ₹1,000 / month)</strong>
      <p>If you want to save a fixed amount every month, here are the top risk-free and high-return options across banks and government programs:</p>
      <div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:8px 10px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <b style="color:#166534;">Bank Recurring Deposit (RD)</b>
            <span class="tag-badge badge-success" style="font-size:0.75rem;">6.50% – 7.75% p.a.</span>
          </div>
          <p style="font-size:0.82rem; margin:4px 0 0 0; color:#374151;">Deposit ₹500 to ₹10,000 every month for 6 months to 10 years across SBI, HDFC, ICICI, PNB with zero capital risk.</p>
        </div>
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:8px 10px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <b style="color:#166534;">Public Provident Fund (PPF)</b>
            <span class="tag-badge badge-success" style="font-size:0.75rem;">7.10% p.a. Tax-Free</span>
          </div>
          <p style="font-size:0.82rem; margin:4px 0 0 0; color:#374151;">Minimum ₹500/year (or monthly deposits). 15-year tenure with full Section 80C tax exemption on deposits and interest.</p>
        </div>
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:8px 10px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <b style="color:#166534;">Sukanya Samriddhi Yojana (SSY)</b>
            <span class="tag-badge badge-success" style="font-size:0.75rem;">8.20% p.a. Tax-Free</span>
          </div>
          <p style="font-size:0.82rem; margin:4px 0 0 0; color:#374151;">For girl children below 10 years. Minimum ₹250/year. Highest government-backed guaranteed interest rate.</p>
        </div>
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:8px 10px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <b style="color:#166534;">Atal Pension Yojana (APY)</b>
            <span class="tag-badge badge-success" style="font-size:0.75rem;">Guaranteed Pension</span>
          </div>
          <p style="font-size:0.82rem; margin:4px 0 0 0; color:#374151;">For age 18–40. Contribute a small monthly amount (starting ₹42–₹210/mo) to receive ₹1,000 to ₹5,000 monthly pension after age 60.</p>
        </div>
      </div>
    `;
  }

  // 4. Savings Account Comparison (Which bank savings account is best)
  if (['saving account', 'saving accound', 'best saving', 'savings account', 'bachat khata', 'savings rate', 'best bank for savings'].some(t => qClean.includes(t))) {
    return `
      <strong>🏦 Best Savings Accounts & Minimum Balance Comparison</strong>
      <p>Comparison of savings accounts by minimum average balance (MAB) requirements and interest rates:</p>
      <div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:8px 10px;">
          <b style="color:#1d4ed8;">Kotak Mahindra Bank (Kotak 811)</b>
          <p style="font-size:0.84rem; margin:2px 0 0 0;">₹0 Minimum Balance + up to 4.00% p.a. savings interest + free virtual debit card.</p>
        </div>
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:8px 10px;">
          <b style="color:#1d4ed8;">Equitas & AU Small Finance Bank</b>
          <p style="font-size:0.84rem; margin:2px 0 0 0;">High savings interest rates up to 7.00% - 7.25% p.a. on savings balances.</p>
        </div>
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:8px 10px;">
          <b style="color:#1d4ed8;">State Bank of India (SBI)</b>
          <p style="font-size:0.84rem; margin:2px 0 0 0;">₹0 Minimum Balance maintenance penalty nationwide across all metro and rural branches + 2.70% p.a.</p>
        </div>
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:8px 10px;">
          <b style="color:#1d4ed8;">HDFC Bank & ICICI Bank</b>
          <p style="font-size:0.84rem; margin:2px 0 0 0;">₹10,000 Metro AMB + premium digital banking, high transaction limits, and cashback rewards.</p>
        </div>
      </div>
    `;
  }

  // 5. Senior Citizens & 50+ Retirement Queries
  if (['senior citizen', 'buzurg', '50+', '50 plus', '60+', '60 plus', 'retired', 'retirement'].some(t => qClean.includes(t))) {
    return `
      <strong>👴 Best Banks & Highest FD Rates for Senior Citizens & 50+</strong>
      <p>For senior citizens (and pre-retirees aged 50+ preparing for retirement), banks offer preferential interest rates (+0.50% to +0.75% extra) and high-yield fixed deposits:</p>
      <div class="bank-specs-grid" style="margin-top:8px;">
        <div class="spec-item" style="border-left:3px solid #f59e0b; padding-left:8px;">
          <b>Equitas SFB (Small Finance)</b>
          <span>Peak Rate: <b style="color:#2563eb;">8.75%</b></span>
          <span>Scheme: Equitas 444 Days Special</span>
        </div>
        <div class="spec-item" style="border-left:3px solid #f59e0b; padding-left:8px;">
          <b>AU SFB (Small Finance)</b>
          <span>Peak Rate: <b style="color:#2563eb;">8.50%</b></span>
          <span>Scheme: AU Royale 18 Months</span>
        </div>
        <div class="spec-item" style="border-left:3px solid #f59e0b; padding-left:8px;">
          <b>Kotak Bank (Private)</b>
          <span>Peak Rate: <b style="color:#2563eb;">7.90%</b></span>
          <span>Scheme: Kotak 390 Days FD</span>
        </div>
        <div class="spec-item" style="border-left:3px solid #f59e0b; padding-left:8px;">
          <b>PNB & Canara (Public Sector)</b>
          <span>Peak Rate: <b style="color:#2563eb;">7.75%</b></span>
          <span>Scheme: PNB Uttam / Canara 444</span>
        </div>
      </div>
    `;
  }

  // 6. Student Banking & Education Queries
  if (['student', 'college', 'padhai', 'study', 'university', 'youth'].some(t => qClean.includes(t))) {
    return `
      <strong>🎓 Best Bank Accounts & Education Options for Students</strong>
      <p>For students, the primary requirements are zero minimum balance maintenance, free digital banking, and accessible education loans:</p>
      <div style="display:flex; flex-direction:column; gap:10px; margin-top:8px;">
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px 12px;">
          <b style="color:#2563eb;">State Bank of India (SBI)</b> <span class="tag-badge" style="margin-left:6px; font-size:0.68rem;">Best Overall & Zero Balance</span>
          <p style="font-size:0.84rem; margin:4px 0;">₹0 minimum balance maintenance penalty across all branches, largest campus ATM network, free YONO digital app.</p>
          <p style="font-size:0.8rem; color:#475569;"><b>Education Loan:</b> SBI Student Loan starting from 8.15% p.a. (0.50% concession for female students).</p>
        </div>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px 12px;">
          <b style="color:#2563eb;">Kotak Mahindra Bank (Kotak 811)</b> <span class="tag-badge" style="margin-left:6px; font-size:0.68rem;">Best 100% Digital Account</span>
          <p style="font-size:0.84rem; margin:4px 0;">Lifetime ₹0 minimum balance digital account, instant online KYC, free virtual debit card on app, up to 4.00% savings interest.</p>
          <p style="font-size:0.8rem; color:#475569;"><b>Education Loan:</b> Kotak Education Loan for domestic and partner global universities.</p>
        </div>
      </div>
      <p style="margin-top:8px;"><a href="https://www.vidyalakshmi.co.in/" target="_blank" rel="noopener">Check Vidya Lakshmi Portal ↗</a></p>
    `;
  }

  // 7. Check for Bank Comparison Queries
  const mentionedBanks = state.banks.filter(b => {
    const id = b.id.toLowerCase();
    const short = b.shortName.toLowerCase();
    return qClean.includes(id) || qClean.includes(short) || qClean.includes(b.name.toLowerCase());
  });

  if (mentionedBanks.length >= 2 || (qClean.includes('compare') && mentionedBanks.length > 0)) {
    const compareList = mentionedBanks.length >= 2 ? mentionedBanks : state.banks.slice(0, 3);
    let html = `<strong>Bank Comparison: ${compareList.map(b => b.shortName).join(' vs ')}</strong>`;
    html += `<div class="bank-specs-grid" style="margin-top: 10px;">`;
    compareList.forEach(b => {
      html += `
        <div class="spec-item" style="border-left: 3px solid ${b.logoColor}; padding-left: 8px;">
          <b>${b.shortName} (${b.type})</b>
          <span>1-Yr FD: ${b.fixedDeposit.rate1Year.general}%</span>
          <span>Home Loan: ${b.loans.homeLoan.startingRate}%</span>
          <span>Min Balance: ₹${b.savings.minBalance.metro.toLocaleString('en-IN')}</span>
        </div>
      `;
    });
    html += `</div><p style="margin-top: 8px;">Switch to the <b>Bank Plan Selector</b> tab for full comparison.</p>`;
    return html;
  }

  // 7.5. IFSC & Branch Lookups (Offline Zero-Latency Resolution)
  if (['ifsc', 'ifsc code', 'branch code', 'micr', 'branch address', 'branch location', 'where is branch', 'branch ifsc'].some(t => qClean.includes(t))) {
    const knownBranches = {
      'friends colony': {
        name: 'State Bank of India (SBI)',
        branch: 'Friends Colony, Nagpur',
        ifsc: 'SBIN0014282',
        micr: '440002047',
        address: 'Friends Colony, Katol Road, Nagpur, Maharashtra - 440013',
      },
      'hudkeshwar': {
        name: 'Bank of India (BOI)',
        branch: 'Hudkeshwar Road, Nagpur',
        ifsc: 'BKID0008745',
        micr: '440013023',
        address: 'Plot No. 1, Kadu Nagar, Hudkeshwar Road, Nagpur, Maharashtra - 440034',
      },
      'civil lines': {
        name: 'State Bank of India (SBI)',
        branch: 'Civil Lines, Nagpur',
        ifsc: 'SBIN0000432',
        micr: '440002002',
        address: 'Kingsway, Station Road, Nagpur - 440001',
      },
      'ramdaspeth': {
        name: 'HDFC Bank',
        branch: 'Ramdaspeth, Nagpur',
        ifsc: 'HDFC0000059',
        micr: '440240002',
        address: 'Central Bazaar Road, Ramdaspeth, Nagpur - 440010',
      },
      'itwari': {
        name: 'Canara Bank',
        branch: 'Itwari, Nagpur',
        ifsc: 'CNRB0000246',
        micr: '440015003',
        address: 'Maskasath, Itwari, Nagpur - 440002',
      }
    };

    let match = null;
    for (const [key, info] of Object.entries(knownBranches)) {
      if (qClean.includes(key)) {
        match = info;
        break;
      }
    }

    if (match) {
      return `
        <strong>🏛️ ${match.name} — ${match.branch}</strong>
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:10px 14px; margin:8px 0;">
          <div style="font-size:0.85rem; color:#166534;">Verified 11-Character IFSC Code:</div>
          <div style="font-size:1.3rem; font-weight:700; color:#15803d; letter-spacing:1px; margin:4px 0;">${match.ifsc}</div>
          <div style="font-size:0.82rem; color:#475569;"><b>MICR Code:</b> ${match.micr} · <b>Address:</b> ${match.address}</div>
        </div>
        <p style="font-size:0.82rem; color:#64748b;">Format: First 4 letters bank code, 5th character '0', last 6 characters branch code.</p>
        <p><a href="https://rbi.org.in/scripts/IFSC_MICR.aspx" target="_blank" rel="noopener">Search on Official RBI IFSC Portal ↗</a></p>
      `;
    }

    const targetBank = mentionedBanks[0] || state.banks[0];
    const bankName = targetBank ? targetBank.name : 'Your Bank';
    return `
      <strong>🔍 How to Find IFSC Code for ${bankName} Branch</strong>
      <p>IFSC is an 11-character code used for NEFT, RTGS, and IMPS funds transfer.</p>
      <ul>
        <li><b>Cheque Leaf:</b> Look at the top left of any cheque leaf from your cheque book.</li>
        <li><b>Bank Passbook:</b> Printed clearly on the first page of your official account passbook.</li>
        <li><b>Official RBI Directory:</b> Search any Indian bank branch on the Reserve Bank of India directory.</li>
      </ul>
      <p><a href="https://rbi.org.in/scripts/IFSC_MICR.aspx" target="_blank" rel="noopener">Visit RBI Official IFSC Directory ↗</a></p>
    `;
  }

  // 8. Single Bank Detail (only if explicitly asking for bank overview / rates)
  if (mentionedBanks.length === 1 && !qClean.includes('zero int') && ['about', 'overview', 'rate', 'interest', 'detail', 'features', 'minimum balance', 'mab', 'info', 'kaisa hai'].some(w => qClean.includes(w))) {
    const b = mentionedBanks[0];
    return `
      <strong>${b.name} (${b.shortName}) Overview</strong>
      <p>${b.tagline}</p>
      <ul>
        <li><b>Savings Account:</b> Metro AMB: ₹${b.savings.minBalance.metro.toLocaleString('en-IN')}, Interest: ${b.savings.interestRate.upTo10Lakh}% p.a.</li>
        <li><b>Fixed Deposit (1-Yr):</b> ${b.fixedDeposit.rate1Year.general}% (Senior Citizen: ${b.fixedDeposit.rate1Year.seniorCitizen}%)</li>
        <li><b>Special Deposit:</b> ${b.fixedDeposit.specialScheme.name} @ ${b.fixedDeposit.specialScheme.generalRate}%</li>
        <li><b>Home Loan Starting Rate:</b> ${b.loans.homeLoan.startingRate}% (${b.loans.homeLoan.benchmarkType})</li>
        <li><b>Helpline:</b> ${b.customerSupport.tollFree.join(', ')}</li>
      </ul>
      <p><a href="${b.customerSupport.officialWebsite}" target="_blank" rel="noopener">Visit ${b.shortName} Official Website ↗</a></p>
    `;
  }

  // 9. Emergency Fraud / ATM / UPI Problem
  if (qClean.includes('otp') || qClean.includes('fraud') || qClean.includes('scam') || qClean.includes('kat gaya') || qClean.includes('nahi nikla')) {
    return `
      <div class="tag-badge badge-danger">Urgent Action Required</div>
      <strong>Safety & Fraud Protocol:</strong>
      <p>1. <b>Never share OTP, PIN, CVV, or passwords</b> with anyone claiming to be bank staff.</p>
      <p>2. If unauthorized transaction occurred, call the <b>National Cybercrime Helpline: 1930</b> immediately or visit <a href="https://cybercrime.gov.in" target="_blank">cybercrime.gov.in</a>.</p>
      <p>3. If cash was not dispensed at an ATM but deducted from your account, banks usually auto-reverse within 24-48 hours. If unresolved, file a formal complaint with your bank branch.</p>
      <p>Check the <b>Emergency & Fraud Help</b> tab for instant bank card-block numbers.</p>
    `;
  }

  // 10. Zero Interest Loan / 1-Month Credit Option
  if (
    (qClean.includes('zero') && (qClean.includes('loan') || qClean.includes('interest'))) ||
    qClean.includes('0%') ||
    qClean.includes('interest free') ||
    (qClean.includes('loan') && (qClean.includes('1 month') || qClean.includes('one month') || qClean.includes('30 days')))
  ) {
    return `
      <strong>Zero-Interest & 1-Month Short-Term Credit in India:</strong>
      <p>Standard bank personal loans (SBI, HDFC, ICICI, etc.) always carry interest (typically 10.5% – 14.5% p.a.). However, legitimate 0% interest / 1-month credit options in India include:</p>
      <ul>
        <li><b>Credit Card 45–50 Days Interest-Free Grace Period:</b> Banks offer 45 to 50 days of 0% interest credit if the bill is settled on time.</li>
        <li><b>No-Cost EMI / Buy Now Pay Later (BNPL):</b> 30-day interest-free purchase window on major portals where merchants cover the financing cost.</li>
        <li><b>Bank Overdraft against Salary or FD:</b> Instant emergency credit with interest charged only for the exact number of days borrowed.</li>
        <li><b>PM SVANidhi / Kisan Credit Card (KCC):</b> Highly subsidized government schemes with interest subvention (effective 4% - 7%).</li>
      </ul>
      <div class="tag-badge badge-danger" style="margin-top: 8px;">⚠️ Warning on Fake 7-Day Loan Apps</div>
      <p style="font-size: 0.82rem; color: #7f1d1d;">Never download unverified 7-day/30-day "0% loan" APK apps from social media. Only borrow through RBI-regulated banks or registered NBFCs.</p>
    `;
  }

  // 11. Zero Balance Account
  if (qClean.includes('zero balance') || qClean.includes('bina balance') || qClean.includes('no minimum balance')) {
    return `
      <strong>Zero-Balance Account Recommendations:</strong>
      <ul>
        <li><b>Pradhan Mantri Jan-Dhan Yojana (PMJDY):</b> Government financial inclusion zero-balance account with RuPay debit card and DBT support.</li>
        <li><b>State Bank of India (SBI):</b> ₹0 minimum balance maintenance penalty on all regular savings accounts.</li>
        <li><b>Kotak 811:</b> 100% digital zero-balance savings account with zero non-maintenance charges.</li>
      </ul>
    `;
  }

  // 12. Match Knowledge Base Schemes with Filtered Informational Keywords
  const stopWords = new Set(['bank', 'account', 'scheme', 'yojana', 'open', 'best', 'which', 'what', 'give', 'want', 'need', 'tell', 'about', 'rate', 'india', 'portal']);
  const queryKeywords = qClean.split(/\s+/).filter(w => w.length > 2 && !stopWords.has(w));

  if (queryKeywords.length > 0) {
    const scoredSchemes = state.knowledge.map(k => {
      const hay = `${k.name} ${k.category} ${k.tags.join(' ')} ${k.summary} ${k.eligibility}`.toLowerCase();
      let score = 0;
      queryKeywords.forEach(tok => {
        if (hay.includes(tok)) score += 1;
      });
      return { scheme: k, score };
    }).filter(x => x.score > 0).sort((a, b) => b.score - a.score);

    if (scoredSchemes.length > 0) {
      const top = scoredSchemes[0].scheme;
      return `
        <strong>${top.name} (${top.category})</strong>
        <p>${top.summary}</p>
        <p><b>Who is eligible:</b> ${top.eligibility}</p>
        <p><b>Key Benefit:</b> ${top.benefits.join('; ')}</p>
        <p><a href="${top.source}" target="_blank" rel="noopener">Verify at official ${top.authority} portal ↗</a></p>
      `;
    }
  }

  return `
    <div class="tag-badge" style="background:#fee2e2; color:#991b1b; margin-bottom:6px;">⚠️ No Direct Banking Match Found</div>
    <strong>I couldn't find a direct banking record for: "${escapeHTML(rawQuery)}"</strong>
    <p style="font-size:0.86rem; color:#475569; margin:4px 0 8px 0;">Did you mean one of these popular banking topics?</p>
    <div style="display:flex; flex-wrap:wrap; gap:6px;">
      <span class="chip" style="font-size:0.8rem; cursor:pointer;" onclick="document.getElementById('question').value='Compare SBI vs HDFC FD rates'; document.getElementById('chatForm').dispatchEvent(new Event('submit'));">⇋ Compare SBI vs HDFC</span>
      <span class="chip" style="font-size:0.8rem; cursor:pointer;" onclick="document.getElementById('question').value='Which bank offers the highest FD rate?'; document.getElementById('chatForm').dispatchEvent(new Event('submit'));">📈 Highest FD Rates</span>
      <span class="chip" style="font-size:0.8rem; cursor:pointer;" onclick="document.getElementById('question').value='Bank account opening age guidelines'; document.getElementById('chatForm').dispatchEvent(new Event('submit'));">📅 Age to Open Account</span>
      <span class="chip" style="font-size:0.8rem; cursor:pointer;" onclick="document.getElementById('question').value='Best savings account with zero balance'; document.getElementById('chatForm').dispatchEvent(new Event('submit'));">🏦 Zero Balance Accounts</span>
      <span class="chip" style="font-size:0.8rem; cursor:pointer;" onclick="document.getElementById('question').value='How to report ATM cash deduction issue'; document.getElementById('chatForm').dispatchEvent(new Event('submit'));">⚠️ ATM Dispute Help</span>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Multi-Bank Plan Selector & Comparison
// ---------------------------------------------------------------------------
function setupBankSelector() {
  const productFilter = document.getElementById('bankProductFilter');
  const typeFilter = document.getElementById('bankTypeFilter');
  const seniorToggle = document.getElementById('seniorCitizenToggle');

  function render() {
    const prod = productFilter.value;
    const type = typeFilter.value;
    const isSenior = seniorToggle.checked;
    state.seniorCitizenFD = isSenior;

    // Filter banks by Sector
    let filtered = state.banks;
    if (type !== 'all') {
      filtered = filtered.filter(b => b.type === type);
    }

    renderBestRateBanner(prod, isSenior);
    renderBankCards(filtered, prod, isSenior);
  }

  productFilter.addEventListener('change', render);
  typeFilter.addEventListener('change', render);
  seniorToggle.addEventListener('change', render);

  // Initial render
  render();
}

function renderBestRateBanner(product, isSenior) {
  const banner = document.getElementById('bestRateBanner');
  if (!state.banks.length) return;

  if (product === 'fd' || product === 'all') {
    // Find highest FD rate
    let topBank = state.banks[0];
    let maxRate = 0;
    state.banks.forEach(b => {
      const r = isSenior ? b.fixedDeposit.specialScheme.seniorRate : b.fixedDeposit.specialScheme.generalRate;
      if (r > maxRate) {
        maxRate = r;
        topBank = b;
      }
    });

    banner.innerHTML = `
      <div>
        <h3>⭐ Highest Fixed Deposit Return: ${topBank.shortName}</h3>
        <p>Offers up to <strong>${maxRate.toFixed(2)}% p.a.</strong> on ${topBank.fixedDeposit.specialScheme.name} (${isSenior ? 'Senior Citizen' : 'General Public'}).</p>
      </div>
      <div class="best-rate-badge">${maxRate.toFixed(2)}%</div>
    `;
  } else if (product === 'loans') {
    // Find lowest Home Loan starting rate
    let topBank = state.banks[0];
    let minRate = 99;
    state.banks.forEach(b => {
      const r = b.loans.homeLoan.startingRate;
      if (r < minRate) {
        minRate = r;
        topBank = b;
      }
    });

    banner.innerHTML = `
      <div>
        <h3>⭐ Lowest Home Loan Starting Benchmark: ${topBank.shortName}</h3>
        <p>Starting at <strong>${minRate.toFixed(2)}% p.a.</strong> linked to ${topBank.loans.homeLoan.benchmarkType}.</p>
      </div>
      <div class="best-rate-badge">${minRate.toFixed(2)}%</div>
    `;
  } else if (product === 'savings') {
    banner.innerHTML = `
      <div>
        <h3>⭐ Zero Minimum Balance Maintenance: SBI & Kotak 811</h3>
        <p>SBI waives monthly balance penalties across all branches; Kotak 811 offers a digital ₹0 MAB account with up to 4.00% interest.</p>
      </div>
      <div class="best-rate-badge">₹0 MAB</div>
    `;
  } else {
    banner.innerHTML = `
      <div>
        <h3>⭐ Compare 8 Major Public & Private Sector Banks</h3>
        <p>Verified interest rates, minimum balances, loan benchmarks, and emergency numbers.</p>
      </div>
      <div class="best-rate-badge">8 Banks</div>
    `;
  }
}

function renderBankCards(banks, product, isSenior) {
  const container = document.getElementById('banksGrid');
  container.innerHTML = '';

  banks.forEach(b => {
    const card = document.createElement('div');
    card.className = 'bank-card';

    const typeClass = b.type === 'Public Sector' ? 'public' : 'private';
    const fd1Yr = isSenior ? b.fixedDeposit.rate1Year.seniorCitizen : b.fixedDeposit.rate1Year.general;
    const fdPeak = isSenior ? b.fixedDeposit.specialScheme.seniorRate : b.fixedDeposit.specialScheme.generalRate;

    card.innerHTML = `
      <div class="bank-card-header">
        <div class="bank-name-wrap">
          <h3 style="color: ${b.logoColor}">${b.name}</h3>
          <span class="bank-tagline">${b.tagline}</span>
        </div>
        <span class="bank-type-pill ${typeClass}">${b.type}</span>
      </div>

      <div class="bank-specs-grid">
        <div class="spec-item">
          <span>Savings Interest</span>
          <b class="highlight">${b.savings.interestRate.upTo10Lakh}% – ${b.savings.interestRate.above10Lakh}%</b>
        </div>
        <div class="spec-item">
          <span>Min Balance (Metro)</span>
          <b>₹${b.savings.minBalance.metro.toLocaleString('en-IN')}</b>
        </div>
        <div class="spec-item">
          <span>1-Yr FD Rate</span>
          <b class="highlight">${fd1Yr.toFixed(2)}%</b>
        </div>
        <div class="spec-item">
          <span>Special Peak FD</span>
          <b>${fdPeak.toFixed(2)}%</b>
        </div>
        <div class="spec-item">
          <span>Home Loan (from)</span>
          <b class="highlight">${b.loans.homeLoan.startingRate.toFixed(2)}%</b>
        </div>
        <div class="spec-item">
          <span>ATM Daily Limit</span>
          <b>₹${b.cardsAndAtm.dailyAtmWithdrawalLimit.toLocaleString('en-IN')}</b>
        </div>
      </div>

      <ul class="bank-features-list">
        <li>${b.savings.features[0]}</li>
        <li><b>Special Deposit:</b> ${b.fixedDeposit.specialScheme.name}</li>
        <li><b>Emergency Toll-Free:</b> ${b.customerSupport.tollFree[0]}</li>
      </ul>

      <div class="bank-actions">
        <a href="${b.customerSupport.officialWebsite}" target="_blank" rel="noopener" class="btn-card-action primary">Visit Official Portal ↗</a>
        <a href="${b.customerSupport.netBankingUrl}" target="_blank" rel="noopener" class="btn-card-action">NetBanking ↗</a>
      </div>
    `;

    container.appendChild(card);
  });
}

// ---------------------------------------------------------------------------
// Government Scheme Finder
// ---------------------------------------------------------------------------
function setupSchemeFinder() {
  const form = document.getElementById('finderForm');
  const results = document.getElementById('schemeResults');

  const schemeNeedMap = {
    saving: ['pmjdy', 'fd', 'rd', 'ppf', 'sukanya'],
    business: ['mudra', 'standup'],
    insurance: ['pmsby', 'pmjjby'],
    pension: ['apy', 'nps', 'ppf'],
    education: ['education'],
    farmer: ['kcc'],
  };

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const need = formData.get('need');
    const age = Number(formData.get('age')) || null;
    const profile = formData.get('profile');

    const matchedIds = schemeNeedMap[need] || [];
    let picks = matchedIds.map(id => state.knowledge.find(k => k.id === id)).filter(Boolean);

    // Profile specific boosts
    if (profile === 'woman' && need === 'business') {
      const standup = state.knowledge.find(k => k.id === 'standup');
      if (standup && !picks.includes(standup)) picks.unshift(standup);
    }
    if (profile === 'unbanked') {
      const pmjdy = state.knowledge.find(k => k.id === 'pmjdy');
      if (pmjdy && !picks.includes(pmjdy)) picks.unshift(pmjdy);
    }
    if (age && need === 'pension' && age > 40) {
      picks = picks.filter(p => p.id !== 'apy'); // APY joining age max 40
    }

    results.innerHTML = '';
    if (picks.length === 0) {
      results.innerHTML = '<p>No specific schemes matched your exact criteria. Please try adjusting your parameters.</p>';
      return;
    }

    picks.forEach(s => {
      const card = document.createElement('div');
      card.className = 'scheme-card';
      card.innerHTML = `
        <span class="badge">${s.category}</span>
        <h3>${s.name}</h3>
        <p>${s.summary}</p>
        <p><b>Who can apply:</b> ${s.eligibility}</p>
        <p><b>Core Benefits:</b> ${s.benefits.join('; ')}</p>
        <a href="${s.source}" target="_blank" rel="noopener">Official ${s.authority} Portal ↗</a>
      `;
      results.appendChild(card);
    });
  });
}

// ---------------------------------------------------------------------------
// Loan EMI Calculator
// ---------------------------------------------------------------------------
function setupEMICalculator() {
  const form = document.getElementById('emiForm');
  const amountInput = document.getElementById('loanAmount');
  const rateInput = document.getElementById('loanRate');
  const tenureInput = document.getElementById('loanTenure');

  const emiValue = document.getElementById('emiValue');
  const principalValue = document.getElementById('principalValue');
  const interestValue = document.getElementById('interestValue');
  const totalPaymentValue = document.getElementById('totalPaymentValue');

  function calculate() {
    const P = Number(amountInput.value) || 0;
    const annualRate = Number(rateInput.value) || 0;
    const years = Number(tenureInput.value) || 0;

    const r = annualRate / (12 * 100);
    const n = years * 12;

    let emi = 0;
    if (P > 0 && n > 0) {
      if (r === 0) {
        emi = P / n;
      } else {
        emi = (P * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
      }
    }

    const totalPayment = emi * n;
    const totalInterest = totalPayment - P;

    emiValue.textContent = formatINR(emi);
    principalValue.textContent = formatINR(P);
    interestValue.textContent = formatINR(totalInterest);
    totalPaymentValue.textContent = formatINR(totalPayment);
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    calculate();
  });

  [amountInput, rateInput, tenureInput].forEach(inp => {
    inp.addEventListener('input', calculate);
  });

  // Quick Amount Chips
  document.querySelectorAll('.btn-chip-amt').forEach(btn => {
    btn.addEventListener('click', () => {
      amountInput.value = btn.dataset.amt;
      calculate();
    });
  });

  calculate();
}

// ---------------------------------------------------------------------------
// Emergency Help Desk
// ---------------------------------------------------------------------------
function setupEmergencyDesk() {
  const container = document.getElementById('emergencyGrid');
  if (!container || !state.banks.length) return;

  container.innerHTML = '';
  state.banks.forEach(b => {
    const card = document.createElement('div');
    card.className = 'emergency-card';
    card.innerHTML = `
      <h3 style="color: ${b.logoColor}">${b.name} (${b.shortName})</h3>
      <div class="emergency-phone">
        <span>📞</span> ${b.customerSupport.tollFree.join(' / ')}
      </div>
      <div class="sms-block-box">
        <span><b>Instant SMS Card Block:</b></span>
        <code>${b.customerSupport.cardBlockSms}</code>
      </div>
      <p style="font-size: 0.78rem; color: #64748b;">
        Nodal Officer Email: <a href="mailto:${b.customerSupport.nodalOfficerEmail}">${b.customerSupport.nodalOfficerEmail}</a>
      </p>
    `;
    container.appendChild(card);
  });
}

function escapeHTML(str) {
  return str.replace(/[&<>'"]/g, tag => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[tag] || tag));
}

// Start application
document.addEventListener('DOMContentLoaded', initApp);
