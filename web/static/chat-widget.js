/* Chat prozor virtualnog asistenta Banke Demo.
 *
 * Dva načina rada:
 *  - plutajući gumb u donjem desnom kutu (zadano, na svim stranicama banke)
 *  - cijela stranica: ako na stranici postoji <div id="bankbot-page"></div>
 *
 * Razgovor se pamti u sessionStorage, pa ostaje kad klijent prelazi između stranica.
 */
(function () {
  "use strict";

  const STORE_KEY = "bankbot-v1";
  // Nakon ovoliko neaktivnosti razgovor se briše i u pregledniku (server ima isti rok).
  const IDLE_MS = 30 * 60 * 1000;
  // Jezik sučelja prati jezik stranice; bot sam prepoznaje jezik svake poruke.
  const lang = (document.documentElement.lang || navigator.language || "hr").toLowerCase().startsWith("hr") ? "hr" : "en";

  const UI = {
    hr: {
      title: "Virtualni asistent",
      status: "Online · odgovara odmah",
      placeholder: "Upišite poruku…",
      send: "Pošalji",
      open: "Otvori chat",
      close: "Zatvori chat",
      reset: "Novi razgovor",
      demo: "demo način",
      note: "Odgovori su informativni. Ne upisujte osobne podatke, lozinke ni brojeve kartica.",
      error: "Došlo je do greške. Pokušajte ponovno.",
      offline: "Server nije dostupan. Provjerite je li pokrenut.",
      expired: "Razgovor je istekao pa sam započeo novi.",
      idle: "Prethodni razgovor je završen nakon 30 minuta neaktivnosti.",
      bubble: "Trebate pomoć?",
      suggestions: ["Izračunaj ratu kredita", "Tečajna lista", "Radno vrijeme poslovnica", "Kako blokirati karticu?"],
    },
    en: {
      title: "Virtual assistant",
      status: "Online · replies instantly",
      placeholder: "Type a message…",
      send: "Send",
      open: "Open chat",
      close: "Close chat",
      reset: "New conversation",
      demo: "demo mode",
      note: "Answers are for information only. Don't enter personal data, passwords or card numbers.",
      error: "Something went wrong. Please try again.",
      offline: "The server isn't reachable. Check that it's running.",
      expired: "The conversation expired, so I started a new one.",
      idle: "The previous conversation ended after 30 minutes of inactivity.",
      bubble: "Need help?",
      suggestions: ["Calculate a loan payment", "Exchange rates", "Branch opening hours", "How do I block my card?"],
    },
  }[lang];

  const ICON_CHAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12z"/></svg>';
  const ICON_CLOSE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>';
  const ICON_SEND = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3.4 20.4 21 12 3.4 3.6 3.4 10l12.6 2-12.6 2z"/></svg>';
  const ICON_RESET = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/></svg>';
  const AVATAR = '<svg viewBox="0 0 40 40" aria-hidden="true"><rect width="40" height="40" rx="10" fill="#0b2e4f"/><path d="M8 17 20 9l12 8v2H8z" fill="#f2b134"/><rect x="11" y="21" width="3" height="9" fill="#fff"/><rect x="18.5" y="21" width="3" height="9" fill="#fff"/><rect x="26" y="21" width="3" height="9" fill="#fff"/><rect x="8" y="31" width="24" height="2.5" fill="#fff"/></svg>';

  // ---------------------------------------------------------------------------
  // Stanje (sessionStorage je opcionalan: u privatnom načinu može baciti grešku)
  // ---------------------------------------------------------------------------

  function load() {
    try {
      return JSON.parse(sessionStorage.getItem(STORE_KEY)) || {};
    } catch (e) {
      return {};
    }
  }

  function save() {
    try {
      sessionStorage.setItem(STORE_KEY, JSON.stringify(state));
    } catch (e) {
      /* nije bitno */
    }
  }

  let state = Object.assign({ sessionId: null, messages: [], open: false, mode: null, lastActivity: null }, load());

  // ---------------------------------------------------------------------------
  // Mini markdown: **bold**, [link](url), liste, tablice, novi redovi. Sve se prvo escapea.
  // ---------------------------------------------------------------------------

  function esc(s) {
    return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function inline(s) {
    return esc(s)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\[([^\]]+)\]\(((?:\/|https?:\/\/)[^)\s]+)\)/g, (m, text, url) => {
        const external = /^https?:/.test(url);
        return `<a href="${url}"${external ? ' target="_blank" rel="noopener"' : ""}${url.endsWith(".csv") ? " download" : ""}>${text}</a>`;
      });
  }

  function renderMarkdown(text) {
    const out = [];
    const lines = text.replace(/\r/g, "").split("\n");
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      if (/^\s*\|.*\|\s*$/.test(line)) {
        const rows = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) rows.push(lines[i++]);
        const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
        const body = rows.filter((r) => !/^\s*\|(\s*:?-{2,}:?\s*\|)+\s*$/.test(r));
        const [head, ...rest] = body;
        let html = '<div class="bb-table"><table><thead><tr>' + cells(head).map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead><tbody>";
        html += rest.map((r) => "<tr>" + cells(r).map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>").join("");
        out.push(html + "</tbody></table></div>");
        continue;
      }
      if (/^\s*[-•]\s+/.test(line)) {
        const items = [];
        while (i < lines.length && (/^\s*[-•]\s+/.test(lines[i]) || (lines[i].trim() === "" && /^\s*[-•]\s+/.test(lines[i + 1] || "")))) {
          if (lines[i].trim()) items.push(lines[i].replace(/^\s*[-•]\s+/, ""));
          i++;
        }
        out.push("<ul>" + items.map((it) => `<li>${inline(it)}</li>`).join("") + "</ul>");
        continue;
      }
      if (line.trim() === "") {
        i++;
        continue;
      }
      const para = [];
      while (i < lines.length && lines[i].trim() !== "" && !/^\s*[-•]\s+/.test(lines[i]) && !/^\s*\|.*\|\s*$/.test(lines[i])) para.push(lines[i++]);
      out.push("<p>" + para.map(inline).join("<br>") + "</p>");
    }
    return out.join("");
  }

  // ---------------------------------------------------------------------------
  // DOM
  // ---------------------------------------------------------------------------

  const pageHost = document.getElementById("bankbot-page");
  const root = document.createElement("div");
  root.className = "bb-root" + (pageHost ? " bb-page" : "");
  root.innerHTML = `
    ${pageHost ? "" : `<button class="bb-launcher" type="button" aria-label="${UI.open}">
      <span class="bb-launcher-icon">${ICON_CHAT}</span><span class="bb-launcher-text">${UI.bubble}</span></button>`}
    <section class="bb-panel" role="dialog" aria-label="${UI.title}">
      <header class="bb-header">
        <div class="bb-avatar">${AVATAR}</div>
        <div class="bb-heading">
          <div class="bb-title">${UI.title} <span class="bb-mode" hidden>${UI.demo}</span></div>
          <div class="bb-status"><span class="bb-dot"></span>${UI.status}</div>
        </div>
        <button class="bb-icon-btn bb-reset" type="button" title="${UI.reset}" aria-label="${UI.reset}">${ICON_RESET}</button>
        ${pageHost ? "" : `<button class="bb-icon-btn bb-close" type="button" title="${UI.close}" aria-label="${UI.close}">${ICON_CLOSE}</button>`}
      </header>
      <div class="bb-messages" aria-live="polite"></div>
      <div class="bb-suggestions"></div>
      <form class="bb-form">
        <textarea class="bb-input" rows="1" maxlength="1000" placeholder="${UI.placeholder}" aria-label="${UI.placeholder}"></textarea>
        <button class="bb-send" type="submit" aria-label="${UI.send}">${ICON_SEND}</button>
      </form>
      <div class="bb-note">${UI.note}</div>
    </section>`;
  (pageHost || document.body).appendChild(root);

  const $ = (sel) => root.querySelector(sel);
  const messagesEl = $(".bb-messages");
  const suggestionsEl = $(".bb-suggestions");
  const input = $(".bb-input");
  const form = $(".bb-form");
  let busy = false;
  let sessionPromise = null; // pozdrav/sesija koja se upravo stvara

  function addMessage(role, text, persist = true, quick = []) {
    const el = document.createElement("div");
    el.className = `bb-msg bb-${role}`;
    el.innerHTML = role === "user" ? `<p>${esc(text).replace(/\n/g, "<br>")}</p>` : renderMarkdown(text);
    messagesEl.appendChild(el);
    if (role === "bot" && quick && quick.length) showQuickReplies(quick);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    if (persist) {
      state.messages.push({ role, text, quick: quick || [] });
      state.lastActivity = Date.now();
      save();
    }
  }

  // Gumbi za brzi odgovor ispod zadnje poruke bota (Da/Ne, Gotovinski/Stambeni, "Jeste li mislili na...").
  function showQuickReplies(options) {
    clearQuickReplies();
    const box = document.createElement("div");
    box.className = "bb-quick";
    options.forEach((label) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "bb-chip";
      b.textContent = label;
      b.addEventListener("click", () => send(label));
      box.appendChild(b);
    });
    messagesEl.appendChild(box);
  }

  function clearQuickReplies() {
    root.querySelectorAll(".bb-quick").forEach((el) => el.remove());
  }

  function addNote(text) {
    const el = document.createElement("div");
    el.className = "bb-sysnote";
    el.textContent = text;
    messagesEl.appendChild(el);
  }

  // ---------------------------------------------------------------------------
  // Neaktivnost: razgovor stariji od IDLE_MS briše se i klijent dobiva novi.
  // Provjerava se kod učitavanja stranice, otvaranja chata, povratka na karticu i slanja poruke.
  // ---------------------------------------------------------------------------

  let idleNote = false; // prikaži napomenu u sljedećem novom razgovoru

  function clearIfIdle() {
    const idle = state.messages.length && state.lastActivity && Date.now() - state.lastActivity > IDLE_MS;
    if (!idle) return false;
    state = { sessionId: null, messages: [], open: state.open, mode: state.mode, lastActivity: null };
    messagesEl.innerHTML = "";
    save();
    idleNote = true;
    return true;
  }

  function showTyping(on) {
    let el = $(".bb-typing");
    if (on && !el) {
      el = document.createElement("div");
      el.className = "bb-msg bb-bot bb-typing";
      el.innerHTML = "<span></span><span></span><span></span>";
      messagesEl.appendChild(el);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    } else if (!on && el) {
      el.remove();
    }
  }

  function renderSuggestions() {
    const show = state.messages.filter((m) => m.role === "user").length === 0;
    suggestionsEl.innerHTML = "";
    suggestionsEl.hidden = !show;
    if (!show) return;
    UI.suggestions.forEach((s) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "bb-chip";
      b.textContent = s;
      b.addEventListener("click", () => send(s));
      suggestionsEl.appendChild(b);
    });
  }

  function showMode() {
    $(".bb-mode").hidden = state.mode !== "simulated";
  }

  // ---------------------------------------------------------------------------
  // API
  // ---------------------------------------------------------------------------

  async function api(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    return { status: res.status, data };
  }

  // ---------------------------------------------------------------------------
  // "Tipkanje": odgovor stiže odmah, ali ga prikazujemo nakon kratke pauze s točkicama,
  // da razgovor djeluje prirodnije. Dulji odgovor = malo dulje tipkanje, uz gornju granicu.
  // ---------------------------------------------------------------------------

  const TYPING = { beforeDots: 350, base: 700, perChar: 8, max: 2600 };
  const sleep = (ms) => new Promise((r) => setTimeout(r, Math.max(0, ms)));
  const typingTime = (text) => Math.min(TYPING.max, TYPING.base + text.length * TYPING.perChar);

  async function botSays(text, persist = true, startedAt = performance.now(), quick = []) {
    showTyping(true);
    await sleep(typingTime(text) - (performance.now() - startedAt));
    showTyping(false);
    addMessage("bot", text, persist, quick);
  }

  async function startSession(showGreeting = true) {
    const { status, data } = await api("/api/session", { lang });
    if (status !== 200) throw new Error("session");
    state.sessionId = data.session_id;
    state.mode = data.mode;
    save();
    showMode();
    if (showGreeting) {
      showTyping(true);
      await sleep(900);
      showTyping(false);
      addMessage("bot", data.greeting);
    }
  }

  async function send(text) {
    text = text.trim();
    if (!text || busy) return;
    if (clearIfIdle()) await reset();
    busy = true;
    input.value = "";
    autosize();
    clearQuickReplies();
    addMessage("user", text);
    renderSuggestions();
    try {
      if (sessionPromise) await sessionPromise.catch(() => {});
      // Kratko "pročitano" prije nego što bot počne tipkati; zahtjev ide odmah, paralelno s pauzom.
      const startedAt = performance.now();
      const request = (async () => {
        if (!state.sessionId) await startSession(false);
        return api("/api/chat", { session_id: state.sessionId, message: text });
      })();
      await sleep(TYPING.beforeDots);
      showTyping(true); // točkice odmah, i ako pravi model odgovara nekoliko sekundi
      let { status, data } = await request;
      if (status === 410) {
        // Server je restartan ili je razgovor istekao.
        await startSession(false);
        addMessage("bot", UI.expired);
        ({ status, data } = await api("/api/chat", { session_id: state.sessionId, message: text }));
      }
      await botSays(
        status === 200 ? data.reply : data.error || UI.error,
        status === 200,
        startedAt + TYPING.beforeDots,
        status === 200 ? data.quick_replies || [] : []
      );
    } catch (e) {
      showTyping(false);
      addMessage("bot", UI.offline, false);
    } finally {
      busy = false;
      input.focus();
    }
  }

  async function reset() {
    state = { sessionId: null, messages: [], open: state.open, mode: state.mode, lastActivity: null };
    messagesEl.innerHTML = "";
    save();
    renderSuggestions();
    if (idleNote) {
      addNote(UI.idle);
      idleNote = false;
    }
    sessionPromise = startSession(true);
    try {
      await sessionPromise;
    } catch (e) {
      addMessage("bot", UI.offline, false);
    } finally {
      sessionPromise = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Događaji
  // ---------------------------------------------------------------------------

  function autosize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  }

  function setOpen(open) {
    state.open = open;
    save();
    root.classList.toggle("bb-open", open);
    if (open) {
      setTimeout(() => input.focus(), 50);
      clearIfIdle();
      if (!state.messages.length) reset();
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    send(input.value);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input.value);
    }
  });
  input.addEventListener("input", autosize);
  $(".bb-reset").addEventListener("click", reset);

  if (!pageHost) {
    $(".bb-launcher").addEventListener("click", () => setOpen(!root.classList.contains("bb-open")));
    $(".bb-close").addEventListener("click", () => setOpen(false));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && root.classList.contains("bb-open")) setOpen(false);
    });
  }

  // Linkovi na stranici s data-bankbot="tekst" otvaraju chat i šalju taj tekst.
  document.addEventListener("click", async (e) => {
    const a = e.target.closest("[data-bankbot]");
    if (!a) return;
    e.preventDefault();
    if (!pageHost) setOpen(true);
    if (sessionPromise) await sessionPromise.catch(() => {});
    const msg = a.getAttribute("data-bankbot");
    if (msg) send(msg);
  });

  // Klijent se vratio na karticu nakon dulje pauze.
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible" || !clearIfIdle()) return;
    renderSuggestions();
    if (root.classList.contains("bb-open")) reset();
  });

  // Obnovi razgovor iz sessionStoragea (osim ako je predugo bio neaktivan).
  clearIfIdle();
  // Gumbi se prikazuju samo ispod zadnje poruke, i samo ako je ona od bota.
  const last = state.messages.length - 1;
  state.messages.forEach((m, i) => addMessage(m.role, m.text, false, i === last ? m.quick : []));
  showMode();
  renderSuggestions();
  if (pageHost) {
    root.classList.add("bb-open");
    if (!state.messages.length) reset();
  } else if (state.open) {
    setOpen(true);
  }
})();
