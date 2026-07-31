/* 等离子体文献工作台 — 前端工作台
 * 所有业务数据来自 /api/v1 真实接口；「待下载清单」「项目分组」「阅读偏好」「术语表」是本地工作台状态，
 * 存 localStorage。
 */
'use strict';

const API = '/api/v1';
const LS_KEY = 'plasma-workbench';

/* ── 术语表（中英对照，用于阅读页高亮） ── */
const DEFAULT_GLOSSARY = [
  { id: 'default-1', en: 'capacitively coupled', zh: '容性耦合' },
  { id: 'default-2', en: 'electron energy distribution function', zh: '电子能量分布函数' },
  { id: 'default-3', en: 'EEDF', zh: '电子能量分布函数' },
  { id: 'default-4', en: 'particle-in-cell', zh: '粒子网格法' },
  { id: 'default-5', en: 'Monte Carlo collisions', zh: '蒙特卡罗碰撞' },
  { id: 'default-6', en: 'secondary electron emission', zh: '二次电子发射' },
  { id: 'default-7', en: 'ohmic heating', zh: '欧姆加热' },
  { id: 'default-8', en: 'cross section', zh: '截面' },
  { id: 'default-9', en: 'dissociation', zh: '解离' },
  { id: 'default-10', en: 'ionization', zh: '电离' },
  { id: 'default-11', en: 'attachment', zh: '吸附' },
  { id: 'default-12', en: 'radical', zh: '自由基' },
  { id: 'default-13', en: 'ion flux', zh: '离子通量' },
  { id: 'default-14', en: 'sheath', zh: '鞘层' },
  { id: 'default-15', en: 'self-bias', zh: '自偏压' },
  { id: 'default-16', en: 'rate coefficient', zh: '速率系数' },
];
const MAX_GLOSSARY_TERM_LENGTH = 120;

const NAV = [
  { key: 'search', label: '文献检索', sub: 'SEARCH', group: 'use' },
  { key: 'library', label: '文献库', sub: 'LIBRARY', group: 'use' },
  { key: 'reader', label: '双语阅读', sub: 'READER', group: 'use' },
  { key: 'chat', label: 'AI 问答', sub: 'Q&A', group: 'use' },
  { key: 'chemistry', label: '化学库复核', sub: 'CHEMISTRY', group: 'use' },
  { key: 'journals', label: '期刊管理', sub: 'JOURNALS', group: 'manage' },
  { key: 'tags', label: '标签管理', sub: 'TAGS', group: 'manage' },
  { key: 'glossary', label: '术语表管理', sub: 'GLOSSARY', group: 'manage' },
];
const NAV_GROUPS = [
  { key: 'use', label: '功能' },
  { key: 'manage', label: '管理' },
];

const REACTION_TYPES = ['elastic', 'excitation', 'ionization', 'attachment', 'recombination'];
const RATE_TYPES = ['cross_section', 'arrhenius', 'constant'];
const EXPORT_LABELS = { json: 'JSON', txt: 'TXT', bolsig: 'BOLSIG+' };
const SELF_REVIEWER = 'self';

const YEAR_MIN = 1990;
const YEAR_MAX = new Date().getFullYear();
const YEAR_PRESETS = [
  { l: '全部', f: YEAR_MIN, t: YEAR_MAX },
  { l: '近 3 年', f: YEAR_MAX - 2, t: YEAR_MAX },
  { l: '近 5 年', f: YEAR_MAX - 4, t: YEAR_MAX },
  { l: '近 10 年', f: YEAR_MAX - 9, t: YEAR_MAX },
];

/* ── 本地视图状态 ── */
const persisted = Object.assign(
  {
    marked: [], projects: [], fontSize: 15, glossary: true,
    glossaryTerms: null, uploadProject: 'none', targetLang: 'zh',
  },
  readStore()
);
persisted.glossaryTerms = normalizeGlossaryTerms(persisted.glossaryTerms);
const legacyPromptPresets = Array.isArray(persisted.customPresets)
  ? persisted.customPresets.filter((item) => item && typeof item === 'object')
    .map((item) => ({
      command: normalizePresetCommand(String(item.cmd || '').slice(0, 24)),
      description: String(item.desc || '').trim().slice(0, 80) || null,
      prompt: String(item.q || '').trim().slice(0, 1000),
    }))
    .filter((item) => /^\/[^\s/]{1,23}$/.test(item.command) && item.prompt)
  : [];

function readStore() {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || '{}'); } catch (e) { return {}; }
}
function saveStore() {
  try { localStorage.setItem(LS_KEY, JSON.stringify(persisted)); } catch (e) { /* 隐私模式下忽略 */ }
}
function allPresets() {
  return state.presets;
}
function presetById(id) {
  return allPresets().find((preset) => String(preset.id) === String(id));
}
function normalizePresetCommand(value) {
  const raw = String(value || '').trim();
  return raw.startsWith('/') ? raw : `/${raw}`;
}
function normalizeGlossaryTerms(value) {
  const source = Array.isArray(value) ? value : DEFAULT_GLOSSARY;
  const seenIds = new Set();
  return source.filter((item) => item && typeof item === 'object').map((item, index) => {
    const fallbackId = `term-${index + 1}`;
    let id = String(item.id || fallbackId).trim() || fallbackId;
    while (seenIds.has(id)) id = `${fallbackId}-${seenIds.size + 1}`;
    seenIds.add(id);
    return {
      id,
      en: String(item.en || '').trim().replace(/\s+/g, ' ').slice(0, MAX_GLOSSARY_TERM_LENGTH),
      zh: String(item.zh || '').trim().replace(/\s+/g, ' ').slice(0, MAX_GLOSSARY_TERM_LENGTH),
    };
  }).filter((item) => item.en || item.zh);
}
function glossaryTerms() {
  return persisted.glossaryTerms;
}

/* ── 运行时状态 ── */
const state = {
  page: 'search',
  status: null,
  journals: [],
  categories: [],
  presets: [],
  activeJournal: null,
  activeCategory: null,
  tagEditor: null,
  categoryEditingId: null,
  oaOnly: false,
  downloadOnly: false,
  query: '',
  queryMode: 'or',
  resultLimit: 50,
  yearFrom: YEAR_MIN,
  yearTo: YEAR_MAX,
  sort: 'relevance',
  searchPage: 1,
  searchTotal: 0,
  results: [],
  searched: false,
  searchMode: 'local',
  activeSearchId: null,
  searchBatchDecision: null,
  onlineSyncing: false,
  syncSummary: null,
  journalSubmitting: false,
  journalEditingId: null,
  expanded: {},
  absZh: {},
  documents: [],
  docMeta: {},
  paperCache: {},
  libLoaded: false,
  readerDocId: null,
  readerProject: 'all',
  readerCategory: '',
  readerMode: 'both',
  readerQaLang: 'zh',
  readerParas: [],
  readerLoading: false,
  readerRetranslating: false,
  readerTargetLang: 'zh',
  translationStatus: null,
  activePara: null,
  readerSearch: '',
  readerDropOpen: false,
  readerQaThreads: {},
  readerQaTyping: false,
  chatScope: 'single',
  chatCategory: '',
  chatDocs: [],
  selProject: null,
  docSearch: '',
  messages: [],
  typing: false,
  chatInput: '',
  slashOpen: false,
  presetEditor: null,
  selection: null,
  glossaryEditingId: null,
  glossaryQuery: '',
  drawerOpen: false,
  batchDownloading: false,
  markedDownloadState: {},
  chemDocId: null,
  chemSets: [],
  chemSetId: null,
  chemSet: null,
  chemLoading: false,
  chemAudit: {},
};

/* ── 工具 ── */
const $ = (sel, root) => (root || document).querySelector(sel);
const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
const esc = (v) => String(v == null ? '' : v)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

function el(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

let toastTimer = null;
function toast(message, bad) {
  const node = $('#toast');
  node.textContent = message;
  node.classList.toggle('bad', !!bad);
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.hidden = true; }, 2600);
}

async function api(path, options) {
  const opts = Object.assign({ headers: {} }, options || {});
  if (opts.body && !(opts.body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  const response = await fetch(API + path, opts);
  const text = await response.text();
  let payload = null;
  try { payload = text ? JSON.parse(text) : null; } catch (e) { payload = null; }
  if (!response.ok) {
    const detail = payload && payload.error ? payload.error : null;
    const err = new Error(detail ? detail.message : `HTTP ${response.status}`);
    err.status = response.status;
    err.code = detail ? detail.code : String(response.status);
    err.payload = payload;
    throw err;
  }
  return payload;
}

async function apiOrNull(path) {
  try { return await api(path); } catch (e) { return null; }
}

function untranslatedAuthorName(value) {
  const name = String(value || '').trim();
  const hasLatin = /[A-Za-z]/.test(name);
  const hasHan = /[\u3400-\u4DBF\u4E00-\u9FFF]/.test(name);
  if (!hasLatin || !hasHan) return name;
  return name
    .replace(/[\u3400-\u4DBF\u4E00-\u9FFF]+/g, '')
    .replace(/([[(（【])\s*([\])）】])/g, '')
    .replace(/\s+([,;，；])/g, '$1')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

function authorsText(authors) {
  if (!Array.isArray(authors) || !authors.length) return '作者信息缺失';
  const names = authors
    .map((a) => untranslatedAuthorName(
      typeof a === 'string' ? a : (a && (a.name || a.display_name || a.full_name)) || ''
    ))
    .filter(Boolean);
  if (!names.length) return '作者信息缺失';
  return names.length > 6 ? `${names.slice(0, 6).join(', ')} 等 ${names.length} 人` : names.join(', ');
}

function zoneClass(zone) {
  const text = String(zone || '');
  if (text.includes('2')) return 'z2';
  if (text.includes('3')) return 'z3';
  return 'zx';
}

function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => toast('已复制 ✓'), () => toast('复制失败', true));
    return;
  }
  const ta = document.createElement('textarea');
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); toast('已复制 ✓'); } catch (e) { toast('复制失败', true); }
  ta.remove();
}

function download(name, content, type) {
  const a = document.createElement('a');
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/* ── 导航与系统状态 ── */
function renderNav() {
  $('#nav').innerHTML = NAV_GROUPS.map((group) => `
    <div class="nav-group" aria-label="${group.label}">
      <div class="nav-group-title">${group.label}</div>
      ${NAV.filter((item) => item.group === group.key).map((item) => `
        <button data-nav="${item.key}" class="${state.page === item.key ? 'on' : ''}">
          <span class="lbl">${item.label}</span>
          <span class="sub">${item.sub}</span>
        </button>`).join('')}
    </div>`).join('');
}

function renderSysbox() {
  const s = state.status;
  if (!s) return;
  const cap = s.external_capabilities || {};
  const counts = s.counts || {};
  const engineOnline = cap.translation_adapter === 'openai-compatible';
  const academicOnline = !!cap.openalex_api_key;
  $('#sysbox').innerHTML = `
    <div class="sysbox-title">系统状态</div>
    <div class="sysrow"><span>翻译引擎</span><span class="${engineOnline ? 'ok' : 'off'}">${engineOnline ? '在线' : '本地回显'}</span></div>
    <div class="sysrow"><span>RAG 索引</span><span class="dim">${counts.documents || 0} 篇 · ${counts.chunks || 0} 段</span></div>
    <div class="sysrow"><span>学术 API</span><span class="${academicOnline ? 'ok' : 'off'}">${academicOnline ? 'API Key 已配置' : '缺少 API Key'}</span></div>`;
}

function setPage(page) {
  state.page = page;
  state.selection = null;
  $('#selection-popover').hidden = true;
  $$('.screen').forEach((node) => { node.hidden = node.dataset.screen !== page; });
  renderNav();
  if (page === 'journals') renderJournalManager();
  if (page === 'library') loadLibrary();
  if (page === 'tags') loadCategories();
  if (page === 'glossary') renderGlossaryManager();
  if (page === 'reader') { ensureLibrary().then(renderReaderBar); }
  if (page === 'chat') { ensureLibrary().then(renderChatSide); }
  if (page === 'chemistry') { ensureLibrary().then(openChemistry); }
}

/* ── 文献检索 ── */
async function loadJournals() {
  const data = await apiOrNull('/journals?active=1&page_size=100');
  state.journals = (data && data.items) || [];
  renderJournalChips();
  renderUploadPaperOptions();
  renderJournalManager();
  renderNav();
}

function renderJournalChips() {
  $('#journal-chips').innerHTML = state.journals.map((j) => {
    const zone = j.sci_zone ? `<span class="zone ${zoneClass(j.sci_zone)}">${esc(j.sci_zone)}</span>` : '';
    const imp = j.impact_factor != null ? `<span class="imp">IF ${esc(j.impact_factor)}</span>` : '';
    return `<button class="chip ${state.activeJournal === j.id ? 'on' : ''}" data-journal="${j.id}">
      ${esc(j.name)}${zone}${imp}</button>`;
  }).join('');
}

/* ── 期刊管理 ── */
function renderJournalManager() {
  const count = $('#journal-manager-count');
  const list = $('#journal-manager-list');
  if (!count || !list) return;
  count.textContent = state.journals.length;
  if (!state.journals.length) {
    list.innerHTML = '<div class="journal-roster-empty">还没有启用的白名单期刊</div>';
    return;
  }
  list.innerHTML = state.journals.map((journal) => {
    const issn = journal.issn_electronic || journal.issn_print || 'ISSN 未填写';
    const yearRange = `${journal.year_from || YEAR_MIN}–${journal.year_to || '至今'}`;
    return `<div class="journal-roster-row" data-journal-row="${journal.id}">
      <div class="journal-roster-main">
        <div class="journal-roster-name" title="${esc(journal.name)}">${esc(journal.name)}</div>
        <div class="journal-roster-meta">
          <span>${esc(issn)}</span>
          <span>${esc(yearRange)}</span>
          <span>搜索词在检索页设置</span>
        </div>
      </div>
      <div class="journal-roster-actions">
        <button class="journal-row-action" type="button" data-journal-edit="${journal.id}"
          aria-label="编辑 ${esc(journal.name)}">编辑</button>
        <button class="journal-row-action danger" type="button" data-journal-delete="${journal.id}"
          aria-label="删除 ${esc(journal.name)}">删除</button>
      </div>
    </div>`;
  }).join('');
}

function journalFormPayload() {
  const yearTo = $('#journal-year-to').value.trim();
  const impactFactor = $('#journal-impact-factor').value.trim();
  return {
    name: $('#journal-name').value.trim(),
    publisher: $('#journal-publisher').value.trim() || null,
    platform: $('#journal-platform').value.trim() || null,
    url: $('#journal-url').value.trim() || null,
    issn_print: $('#journal-issn-print').value.trim().toUpperCase() || null,
    issn_electronic: $('#journal-issn-electronic').value.trim().toUpperCase() || null,
    keywords: [],
    year_from: Number($('#journal-year-from').value),
    year_to: yearTo ? Number(yearTo) : null,
    sci_zone: $('#journal-sci-zone').value || null,
    impact_factor: impactFactor ? Number(impactFactor) : null,
    active: true,
  };
}

function journalValidationMessage(payload, excludedJournalId) {
  if (!payload.name) return '请填写期刊名称。';
  if (!payload.issn_print && !payload.issn_electronic) return '请至少填写一个 Print ISSN 或 Electronic ISSN。';
  const issnPattern = /^\d{4}-\d{3}[\dX]$/;
  if (payload.issn_print && !issnPattern.test(payload.issn_print)) return 'Print ISSN 格式应为 ####-####，校验位可为 X。';
  if (payload.issn_electronic && !issnPattern.test(payload.issn_electronic)) return 'Electronic ISSN 格式应为 ####-####，校验位可为 X。';
  if (!Number.isInteger(payload.year_from) || payload.year_from < 1900 || payload.year_from > 2100) {
    return '起始年份应在 1900–2100 之间。';
  }
  if (payload.year_to != null && (
    !Number.isInteger(payload.year_to) || payload.year_to < payload.year_from || payload.year_to > 2100
  )) return '截止年份应不早于起始年份，且不晚于 2100。';
  if (payload.impact_factor != null && (!Number.isFinite(payload.impact_factor) || payload.impact_factor < 0)) {
    return '影响因子应为不小于 0 的数字。';
  }
  const normalizedName = payload.name.toLowerCase();
  const duplicate = state.journals.find((journal) =>
    journal.id !== excludedJournalId && (
      String(journal.name || '').toLowerCase() === normalizedName
      || (payload.issn_print && [journal.issn_print, journal.issn_electronic].includes(payload.issn_print))
      || (payload.issn_electronic && [journal.issn_print, journal.issn_electronic].includes(payload.issn_electronic))
    ));
  return duplicate ? `白名单中已存在「${duplicate.name}」，请核对期刊名称和 ISSN。` : '';
}

function setJournalFormMessage(message, bad) {
  const node = $('#journal-form-message');
  node.textContent = message || '';
  node.classList.toggle('bad', !!bad);
  node.hidden = !message;
}

function resetJournalForm() {
  state.journalEditingId = null;
  $('#journal-create-form').reset();
  $('#journal-year-from').value = String(YEAR_MIN);
  $('#journal-form-title').textContent = '新增白名单期刊';
  $('#journal-form-description').textContent = '期刊名称和至少一个 ISSN 为必填项；搜索关键词统一在文献检索页填写。';
  $('#journal-form-reset').textContent = '清空';
  $('#journal-create-submit').textContent = '新增并启用';
  setJournalFormMessage('', false);
}

function editJournalFromWorkbench(journalId) {
  const journal = state.journals.find((item) => item.id === journalId);
  if (!journal) {
    toast('找不到要编辑的期刊，请刷新后重试', true);
    return;
  }
  state.journalEditingId = journal.id;
  $('#journal-name').value = journal.name || '';
  $('#journal-issn-print').value = journal.issn_print || '';
  $('#journal-issn-electronic').value = journal.issn_electronic || '';
  $('#journal-year-from').value = String(journal.year_from || YEAR_MIN);
  $('#journal-year-to').value = journal.year_to == null ? '' : String(journal.year_to);
  $('#journal-publisher').value = journal.publisher || '';
  $('#journal-platform').value = journal.platform || '';
  $('#journal-url').value = journal.url || '';
  $('#journal-sci-zone').value = journal.sci_zone || '';
  $('#journal-impact-factor').value = journal.impact_factor == null ? '' : String(journal.impact_factor);
  $('#journal-form-title').textContent = '编辑白名单期刊';
  $('#journal-form-description').textContent = `正在编辑「${journal.name}」；保存后新的范围会用于后续联网搜索。`;
  $('#journal-form-reset').textContent = '取消编辑';
  $('#journal-create-submit').textContent = '保存修改';
  setJournalFormMessage('', false);
  $('#journal-name').focus();
}

async function deleteJournalFromWorkbench(journalId) {
  const journal = state.journals.find((item) => item.id === journalId);
  if (!journal) {
    toast('找不到要删除的期刊，请刷新后重试', true);
    return;
  }
  const confirmed = window.confirm(
    `确认删除白名单「${journal.name}」？\n\n该期刊将停止参与后续联网搜索；已抓取的论文和历史任务不会删除。`
  );
  if (!confirmed) return;
  try {
    await api(`/journals/${journal.id}`, { method: 'DELETE' });
    if (state.journalEditingId === journal.id) resetJournalForm();
    if (state.activeJournal === journal.id) state.activeJournal = null;
    await loadJournals();
    toast(`已删除白名单「${journal.name}」`);
  } catch (error) {
    toast(`删除失败：${error.message}`, true);
  }
}

async function saveJournalFromWorkbench() {
  if (state.journalSubmitting) return;
  const payload = journalFormPayload();
  const editingId = state.journalEditingId;
  const validationMessage = journalValidationMessage(payload, editingId);
  if (validationMessage) {
    setJournalFormMessage(validationMessage, true);
    return;
  }
  const submit = $('#journal-create-submit');
  state.journalSubmitting = true;
  submit.disabled = true;
  submit.textContent = editingId == null ? '正在新增…' : '正在保存…';
  setJournalFormMessage(editingId == null ? '正在写入白名单并刷新工作台…' : '正在保存修改并刷新工作台…', false);
  try {
    const journal = editingId == null
      ? await api('/journals', { method: 'POST', body: payload })
      : await api(`/journals/${editingId}`, { method: 'PUT', body: payload });
    resetJournalForm();
    await loadJournals();
    const action = editingId == null ? '新增并启用' : '更新';
    setJournalFormMessage(`已${action}「${journal.name}」。新的范围将用于后续联网搜索。`, false);
    toast(`已${action}白名单「${journal.name}」`);
  } catch (error) {
    setJournalFormMessage(`${editingId == null ? '新增' : '保存'}失败：${error.message}`, true);
  } finally {
    state.journalSubmitting = false;
    submit.disabled = false;
    submit.textContent = state.journalEditingId == null ? '新增并启用' : '保存修改';
  }
}

/* ── 标签（复用 categories / paper_categories） ── */
async function loadCategories() {
  const data = await apiOrNull('/categories?page_size=100');
  state.categories = (data && data.items) || [];
  renderCategoryChips();
  renderTagManager();
}

async function loadPresets() {
  const data = await api('/prompt-presets?page_size=100');
  state.presets = (data.items || []).map((preset) => ({
    id: preset.id,
    cmd: preset.command,
    desc: preset.description || '',
    q: preset.prompt,
  }));
}

async function migrateLegacyPromptPresets() {
  if (!legacyPromptPresets.length) {
    delete persisted.customPresets;
    saveStore();
    return;
  }
  for (const preset of legacyPromptPresets) {
    try {
      await api('/prompt-presets', { method: 'POST', body: preset });
    } catch (error) {
      if (error.code !== 'prompt_preset_conflict') throw error;
    }
  }
  delete persisted.customPresets;
  saveStore();
}

function renderCategoryChips() {
  $('#category-chips').innerHTML = state.categories.length
    ? state.categories.map((c) => `<button class="chip ${state.activeCategory === c.slug ? 'on' : ''}"
        data-category="${esc(c.slug)}" title="${esc(c.description || '')}">${esc(c.name)}</button>`).join('')
    : '<span class="chips-label">（分类表为空）</span>';
}

function categoryOptions(selectedSlug, emptyLabel) {
  return [`<option value="">${esc(emptyLabel || '全部标签')}</option>`].concat(
    state.categories.map((category) =>
      `<option value="${esc(category.slug)}" ${selectedSlug === category.slug ? 'selected' : ''}>`
      + `${esc(category.name)}（${category.paper_count || 0}）</option>`)
  ).join('');
}

function categoryBySlug(slug) {
  return state.categories.find((category) => category.slug === slug);
}

function documentPaper(doc) {
  if (!doc || doc.paper_id == null) return null;
  return state.paperCache[doc.paper_id] || null;
}

function documentMatchesCategory(doc, slug) {
  if (!slug) return true;
  const paper = documentPaper(doc);
  return !!paper && (paper.category_details || []).some((category) => category.slug === slug);
}

function renderTagManager() {
  const list = $('#tag-manager-list');
  const summary = $('#tag-manager-summary');
  if (!list || !summary) return;
  const linked = state.categories.reduce((total, category) => total + (category.paper_count || 0), 0);
  summary.textContent = `${state.categories.length} 个标签 · ${linked} 条文献关联`;
  if (!state.categories.length) {
    list.innerHTML = '<div class="tag-manager-empty">还没有标签，可在上方创建第一个标签</div>';
    return;
  }
  list.innerHTML = state.categories.map((category) => {
    const childCount = (category.children || []).length;
    const usage = category.paper_count || 0;
    if (state.categoryEditingId === category.id) {
      return `<form class="tag-manager-row is-editing" data-category-edit-form="${category.id}">
        <div class="tag-manager-name tag-manager-edit-stack">
          <input class="input" data-category-edit-name value="${esc(category.name)}"
            aria-label="标签名称" maxlength="120" required>
          <input class="input tag-manager-edit-description" data-category-edit-description
            value="${esc(category.description || '')}" aria-label="标签说明"
            maxlength="240" placeholder="标签说明（可选）">
        </div>
        <div class="tag-manager-slug">
          <input class="input mono" data-category-edit-slug value="${esc(category.slug)}"
            aria-label="英文标识" maxlength="120" required>
        </div>
        <div class="tag-manager-usage">${usage} 篇文献${childCount ? ` · ${childCount} 个子标签` : ''}</div>
        <div class="tag-manager-actions">
          <button type="submit" class="btn-primary sm">保存</button>
          <button type="button" class="btn-ghost sm" data-category-edit-cancel="${category.id}">取消</button>
        </div>
      </form>`;
    }
    const deleteHint = childCount
      ? `包含 ${childCount} 个子标签，需先处理子标签`
      : usage
        ? `删除并解除 ${usage} 条文献关联`
        : '删除此标签';
    return `<div class="tag-manager-row" data-category-row="${category.id}">
      <div class="tag-manager-name">
        ${esc(category.name)}
        <div class="desc">${esc(category.description || '暂无说明')}</div>
      </div>
      <div class="tag-manager-slug">${esc(category.slug)}</div>
      <div class="tag-manager-usage">${usage} 篇文献${childCount ? ` · ${childCount} 个子标签` : ''}</div>
      <div class="tag-manager-actions">
        <button class="btn-ghost sm" data-category-edit="${category.id}">编辑</button>
        <button class="btn-ghost sm danger" data-category-delete="${category.id}"
          title="${esc(deleteHint)}" ${childCount ? 'disabled' : ''}>删除</button>
      </div>
    </div>`;
  }).join('');
}

function tagChips(paper) {
  return (paper.category_details || []).map((c) => {
    const manual = c.method === 'manual';
    const title = manual ? '人工标注' : `自动分类${c.confidence != null ? ` · 置信度 ${c.confidence}` : ''}`;
    return `<span class="tag-chip ${manual ? '' : 'auto'}" title="${esc(title)}">${esc(c.name)}</span>`;
  }).join('');
}

function tagEditorMarkup(paper) {
  const selected = new Set((paper.category_details || []).map((c) => c.id));
  const opts = state.categories.map((c) => `<button class="tag-opt ${selected.has(c.id) ? 'on' : ''}"
    data-tag="${c.id}"><span class="box">${selected.has(c.id) ? '✓' : ''}</span>${esc(c.name)}</button>`).join('');
  return `<div class="tag-editor">
    <div class="lbl">打标 · 人工标注会覆盖自动分类</div>
    <div class="tag-opts">${opts || '<span class="chips-label">分类表为空，先新建一个标签</span>'}</div>
    <div class="tag-editor-foot">
      <input class="input" data-new-tag placeholder="新建标签名称">
      <button class="btn-dashed" data-tag-act="create">＋ 新建标签</button>
      <div class="spacer"></div>
      <button class="btn-ghost sm" data-tag-act="auto">自动分类</button>
      <button class="btn-ghost sm" data-tag-act="cancel">取消</button>
      <button class="btn-primary sm" data-tag-act="save">保存标签</button>
    </div>
    <div class="tag-note">保存后写入 paper_categories（method=manual）；「自动分类」调用 LLM 分类接口，结果以 auto 记录，不覆盖人工标注。</div>
  </div>`;
}

async function saveTags(paperId, categoryIds) {
  try {
    await api(`/papers/${paperId}/categories`, {
      method: 'PUT',
      body: { category_ids: categoryIds, method: 'manual' },
    });
    toast(categoryIds.length ? `已保存 ${categoryIds.length} 个标签` : '已清空该文献的标签');
  } catch (e) {
    toast(`打标失败：${e.message}`, true);
    return;
  }
  state.tagEditor = null;
  await refreshTaggedPaper(paperId);
}

async function autoClassify(paperId) {
  toast('正在调用分类接口…');
  try {
    await api(`/papers/${paperId}/classify`, { method: 'POST' });
    toast('自动分类完成');
  } catch (e) {
    toast(`自动分类失败：${e.message}`, true);
    return;
  }
  await refreshTaggedPaper(paperId);
}

async function createCategory(name, description) {
  const label = (name || '').trim();
  if (!label) { toast('标签名称不能为空', true); return; }
  const slugBase = label.toLowerCase().replace(/\s+/g, '-')
    .replace(/[^a-z0-9_-]/g, '').replace(/^[-_]+|[-_]+$/g, '');
  const slug = slugBase || `tag-${Date.now()}`;
  try {
    await api('/categories', {
      method: 'POST',
      body: { name: label, slug, description: (description || '').trim() || null },
    });
    toast(`已新建标签「${label}」`);
  } catch (e) {
    toast(`新建标签失败：${e.message}`, true);
    return false;
  }
  await loadCategories();
  renderLibrary();
  if (state.page === 'reader') renderReaderBar();
  if (state.page === 'chat') renderChatSide();
  return true;
}

function removeCategoryFromPaper(paper, categoryId, slug) {
  if (!paper) return;
  paper.category_details = (paper.category_details || []).filter((category) => category.id !== categoryId);
  paper.categories = (paper.categories || []).filter((categorySlug) => categorySlug !== slug);
}

function updateCategoryOnPaper(paper, updated, previousSlug) {
  if (!paper) return;
  paper.category_details = (paper.category_details || []).map((category) =>
    category.id === updated.id
      ? Object.assign({}, category, { name: updated.name, slug: updated.slug })
      : category);
  paper.categories = (paper.categories || []).map((slug) =>
    slug === previousSlug ? updated.slug : slug);
}

async function updateCategory(categoryId, form) {
  const previous = state.categories.find((item) => item.id === categoryId);
  if (!previous) return;
  const name = $('[data-category-edit-name]', form).value.trim();
  const slug = $('[data-category-edit-slug]', form).value.trim();
  const description = $('[data-category-edit-description]', form).value.trim();
  if (!name || !slug) {
    toast('标签名称和英文标识不能为空', true);
    return;
  }
  const submit = $('button[type="submit"]', form);
  submit.disabled = true;
  submit.textContent = '保存中…';
  try {
    const updated = await api(`/categories/${categoryId}`, {
      method: 'PUT',
      body: { name, slug, description: description || null },
    });
    state.results.forEach((paper) => updateCategoryOnPaper(paper, updated, previous.slug));
    Object.values(state.paperCache).forEach((paper) =>
      updateCategoryOnPaper(paper, updated, previous.slug));
    if (state.activeCategory === previous.slug) state.activeCategory = updated.slug;
    if (state.readerCategory === previous.slug) state.readerCategory = updated.slug;
    if (state.chatCategory === previous.slug) state.chatCategory = updated.slug;
    state.categoryEditingId = null;
    await loadCategories();
    renderResults();
    renderLibrary();
    if (state.page === 'reader') renderReaderBar();
    if (state.page === 'chat') renderChatSide();
    toast(`已更新标签「${updated.name}」`);
  } catch (error) {
    submit.disabled = false;
    submit.textContent = '保存';
    toast(`保存标签失败：${error.message}`, true);
  }
}

async function deleteCategory(categoryId) {
  const category = state.categories.find((item) => item.id === categoryId);
  if (!category) return;
  const usage = category.paper_count || 0;
  const detail = usage
    ? `该操作会同时解除 ${usage} 条文献关联，文献本身不会被删除。`
    : '该标签当前没有关联文献。';
  if (!window.confirm(`确定删除标签「${category.name}」？\n${detail}`)) return;
  try {
    const result = await api(`/categories/${categoryId}`, { method: 'DELETE' });
    state.results.forEach((paper) => removeCategoryFromPaper(paper, categoryId, category.slug));
    Object.values(state.paperCache).forEach((paper) => removeCategoryFromPaper(paper, categoryId, category.slug));
    if (state.activeCategory === category.slug) state.activeCategory = null;
    if (state.readerCategory === category.slug) state.readerCategory = '';
    if (state.chatCategory === category.slug) state.chatCategory = '';
    await loadCategories();
    renderResults();
    renderLibrary();
    if (state.page === 'reader') renderReaderBar();
    if (state.page === 'chat') renderChatSide();
    toast(`已删除「${category.name}」，解除 ${result.removed_paper_links} 条文献关联`);
  } catch (e) {
    toast(`删除标签失败：${e.message}`, true);
  }
}

/* 打标后同步刷新：检索结果与文献库卡片都读同一份 paper 数据 */
async function refreshTaggedPaper(paperId) {
  const fresh = await apiOrNull(`/papers/${paperId}`);
  if (fresh) {
    const index = state.results.findIndex((p) => p.id === paperId);
    if (index >= 0) state.results[index] = Object.assign({}, state.results[index], fresh);
    state.paperCache[paperId] = fresh;
  }
  renderResults();
  renderLibrary();
}

function searchQuery() {
  const params = new URLSearchParams();
  if (state.query.trim()) {
    params.set('q', state.query.trim());
    params.set('q_mode', state.queryMode);
    params.set('result_limit', state.resultLimit);
  }
  if (state.searchMode === 'online' && state.activeSearchId != null) {
    params.set('search_id', state.activeSearchId);
  }
  if (state.activeJournal != null) params.set('journal_id', state.activeJournal);
  if (state.activeCategory) params.set('category', state.activeCategory);
  params.set('year_from', state.yearFrom);
  params.set('year_to', state.yearTo);
  if (state.oaOnly) params.set('oa_only', 'true');
  if (state.downloadOnly) params.set('downloadable_only', 'true');
  params.set('sort', state.query.trim() ? state.sort : 'date_desc');
  params.set('page', state.searchPage);
  params.set('page_size', '20');
  return params.toString();
}

function parseSearchTerms(value) {
  return String(value || '').split(/[\n,，;；]+/)
    .map((term) => term.trim().replace(/\s+/g, ' '))
    .filter((term, index, terms) =>
      term && terms.findIndex((candidate) => candidate.toLowerCase() === term.toLowerCase()) === index);
}

async function runSearch(resetPage, options) {
  options = options || {};
  if (resetPage !== false) state.searchPage = 1;
  if (!options.keepSyncSummary) {
    state.searchMode = 'local';
    state.activeSearchId = null;
    state.searchBatchDecision = null;
    state.syncSummary = null;
  }
  $('#search-meta').textContent = '正在检索本地文献库…';
  try {
    const data = await api(`/papers?${searchQuery()}`);
    state.results = data.items || [];
    state.searchTotal = data.total || 0;
    state.searched = true;
  } catch (e) {
    state.results = [];
    state.searchTotal = 0;
    $('#search-meta').textContent = `检索失败：${e.message}`;
    $('#search-results').innerHTML = '';
    return;
  }
  renderResults();
}

function renderResults() {
  const meta = $('#search-meta');
  let sync = '本地文献库 · ';
  if (state.searchMode === 'online' && state.syncSummary) {
    sync = state.syncSummary.cacheHit
      ? `本地缓存命中（${state.syncSummary.cacheTtlHours} 小时内） · `
      : `联网搜索完成：${state.syncSummary.succeeded}/${state.syncSummary.total} 个期刊成功`
        + ` · 新增 ${state.syncSummary.newPapers} 篇 · `;
  }
  meta.textContent = `${sync}共 ${state.searchTotal} 条结果 · 已标记 ${persisted.marked.length} 条待下载`
    + (state.activeJournal != null ? ' · 已按白名单期刊过滤' : '');
  const batchActions = $('#search-batch-actions');
  batchActions.hidden = !(
    state.searchMode === 'online'
    && state.activeSearchId != null
    && state.searchBatchDecision !== 'discarded'
  );
  $('#save-search-batch').hidden = state.searchBatchDecision === 'saved';
  $('#discard-search-batch').textContent = state.searchBatchDecision === 'saved'
    ? '撤销已保存批次'
    : '撤销本次结果';
  const wrap = $('#search-results');
  if (!state.results.length) {
    wrap.innerHTML = `<div class="empty-state">${state.searched
      ? '没有命中文献<br>可切换 OR、放宽年份区间、清除期刊筛选，或点击「联网搜索」更新元数据'
      : '输入关键词后检索本地库，或在白名单期刊中联网搜索'}</div>`;
    $('#search-pager').hidden = true;
    return;
  }
  wrap.innerHTML = state.results.map((p) => paperCard(p)).join('');
  const pages = Math.max(1, Math.ceil(state.searchTotal / 20));
  $('#search-pager').hidden = pages <= 1;
  $('[data-page-label]').textContent = `第 ${state.searchPage} / ${pages} 页`;
  $('[data-page-prev]').disabled = state.searchPage <= 1;
  $('[data-page-next]').disabled = state.searchPage >= pages;
}

function onlineDateRange() {
  const now = new Date();
  const currentYear = now.getFullYear();
  const today = [
    currentYear,
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
  ].join('-');
  return {
    date_from: `${state.yearFrom}-01-01`,
    date_to: state.yearTo >= currentYear ? today : `${state.yearTo}-12-31`,
  };
}

function setOnlineSearchBusy(busy, label) {
  state.onlineSyncing = busy;
  $('#do-search').disabled = busy;
  const button = $('#do-online-search');
  button.disabled = busy;
  button.textContent = label || (busy ? '联网搜索中…' : '联网搜索');
}

function waitForOnlineSearchPoll(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function waitForCrawlJobs(jobIds) {
  const deadline = Date.now() + 1800000;
  while (Date.now() < deadline) {
    const jobs = await Promise.all(jobIds.map((jobId) => api(`/crawl/jobs/${jobId}`)));
    const finished = jobs.filter((job) => ['success', 'failed'].includes(job.status));
    const newPapers = jobs.reduce((total, job) => total + Number(job.papers_new || 0), 0);
    $('#search-meta').textContent =
      `联网搜索中：${finished.length}/${jobs.length} 个期刊完成 · 已新增 ${newPapers} 篇`;
    setOnlineSearchBusy(true, `同步中 ${finished.length}/${jobs.length}`);
    if (finished.length === jobs.length) return jobs;
    await waitForOnlineSearchPoll(1000);
  }
  throw new Error('联网搜索等待超过 30 分钟；后台任务可能仍在运行，请稍后重试本地检索');
}

async function runOnlineSearch() {
  if (state.onlineSyncing) return;
  const query = state.query.trim();
  const searchTerms = parseSearchTerms(query);
  if (!searchTerms.length) {
    toast('请先输入在线检索关键词', true);
    $('#search-q').focus();
    return;
  }
  setOnlineSearchBusy(true);
  $('#search-meta').textContent = '正在检查本地缓存并创建 OpenAlex / Crossref 搜索任务…';
  const body = Object.assign({
    period: 'manual',
    search_terms: searchTerms,
    search_mode: state.queryMode,
    max_results: state.resultLimit,
  }, onlineDateRange());
  if (state.activeJournal != null) body.journal_ids = [state.activeJournal];
  try {
    const accepted = await api('/crawl/run', { method: 'POST', body });
    const jobIds = (accepted.jobs || []).map((job) => job.job_id);
    state.activeSearchId = accepted.search_id == null ? null : Number(accepted.search_id);
    state.searchBatchDecision = accepted.decision_status || 'preview';
    if (accepted.cache_hit) {
      state.searchMode = 'online';
      state.syncSummary = {
        cacheHit: true,
        cacheTtlHours: Number(accepted.cache_ttl_hours || 24),
      };
      await runSearch(true, { keepSyncSummary: true });
      toast(`已复用本地缓存，最多返回 ${state.resultLimit} 篇`);
      return;
    }
    if (!jobIds.length) throw new Error('联网搜索没有创建任何期刊任务');
    const jobs = await waitForCrawlJobs(jobIds);
    const succeeded = jobs.filter((job) => job.status === 'success');
    const failed = jobs.filter((job) => job.status === 'failed');
    state.searchMode = 'online';
    state.syncSummary = {
      total: jobs.length,
      succeeded: succeeded.length,
      failed: failed.length,
      newPapers: jobs.reduce((total, job) => total + Number(job.papers_new || 0), 0),
      cacheHit: false,
    };
    await runSearch(true, { keepSyncSummary: true });
    if (failed.length) toast(`${failed.length} 个期刊搜索失败，已展示其余结果`, true);
    else toast(`联网搜索完成，最多返回 ${state.resultLimit} 篇`);
  } catch (e) {
    $('#search-meta').textContent = `联网搜索失败：${e.message} · 本地结果未改变`;
    toast(`联网搜索失败：${e.message}`, true);
  } finally {
    setOnlineSearchBusy(false);
  }
}

async function saveOnlineSearchBatch() {
  if (state.activeSearchId == null) return;
  try {
    const result = await api(`/crawl/searches/${state.activeSearchId}/save`, { method: 'POST' });
    state.searchBatchDecision = result.decision_status;
    renderResults();
    toast(`已保存 ${result.saved_count} 篇新论文到本地库`);
  } catch (e) {
    toast(`保存搜索结果失败：${e.message}`, true);
  }
}

async function discardOnlineSearchBatch() {
  if (state.activeSearchId == null) return;
  if (!window.confirm('撤销本次联网搜索结果？\n\n仅本次新增且没有 PDF 或其他引用的预览论文会被删除。')) return;
  try {
    const result = await api(`/crawl/searches/${state.activeSearchId}`, { method: 'DELETE' });
    state.searchMode = 'local';
    state.activeSearchId = null;
    state.searchBatchDecision = result.decision_status;
    state.syncSummary = null;
    await runSearch(true);
    toast(`已撤销：删除 ${result.removed_count} 篇，安全保留 ${result.preserved_count} 篇`);
  } catch (e) {
    toast(`撤销搜索结果失败：${e.message}`, true);
  }
}

function paperCard(p) {
  const expanded = !!state.expanded[p.id];
  const marked = persisted.marked.some((m) => m.id === p.id);
  const downloadInfo = downloadAvailability(p);
  const journal = state.journals.find((j) => j.id === p.journal_id);
  const zone = journal && journal.sci_zone
    ? `<span class="zone ${zoneClass(journal.sci_zone)}">${esc(journal.sci_zone)}</span>` : '';
  const oa = p.oa_pdf_url
    ? `<a class="card-fact" style="color:var(--accent-1)" href="${esc(p.oa_pdf_url)}" target="_blank" rel="noopener">OA 全文 ↗</a>`
    : `<span class="card-fact">${p.oa_status ? `OA ${esc(p.oa_status)}` : '无 OA 链接'}</span>`;
  const cats = tagChips(p);
  const zh = state.absZh[p.id];
  const zhBlock = zh
    ? `<div class="abs-zh ${zh.muted ? 'muted' : ''}"><span class="tag">摘要翻译</span>${esc(zh.text)}</div>`
    : '';
  const markButton = downloadInfo.supported
    ? `<button class="btn-ghost sm mark-btn ${marked ? 'on' : ''}" data-act="mark">${marked ? '✓ 已在清单' : '加入待下载'}</button>`
    : `<button class="btn-ghost sm mark-btn" disabled title="${esc(downloadInfo.reason)}">暂不支持下载</button>`;
  return `<div class="card" data-paper="${p.id}">
    <div class="card-top">
      <div class="flex">
        <div class="card-title" data-act="expand">${esc(p.title)}</div>
        <div class="card-authors">${esc(authorsText(p.authors))}</div>
        <div class="card-facts">
          ${zone}
          <span class="card-journal">${esc(p.journal_name || '未知期刊')}</span>
          <span class="card-fact">${esc(p.published_date || p.published_year || '')}</span>
          ${oa}
          ${cats}
        </div>
      </div>
      ${markButton}
    </div>
    <div class="abs ${expanded ? '' : 'clamp'}" data-act="expand">${esc(p.abstract || '（该条元数据没有摘要）')}</div>
    ${zhBlock}
    <div class="card-foot">
      <span class="doi">DOI&nbsp;&nbsp;${esc(p.doi || '—')}</span>
      <div class="spacer"></div>
      <button class="btn-ghost sm" data-act="copy" ${p.doi ? '' : 'disabled'}>复制 DOI</button>
      <button class="btn-ghost sm" data-act="zh">${zh ? '隐藏翻译' : '摘要翻译'}</button>
      <button class="btn-ghost sm" data-act="expand">${expanded ? '收起摘要' : '展开摘要'}</button>
    </div>
  </div>`;
}

/* 摘要翻译：复用已导入全文的译文里的 abstract 段落，没有则如实说明 */
async function showAbstractTranslation(paperId) {
  if (state.absZh[paperId]) { delete state.absZh[paperId]; renderResults(); return; }
  state.absZh[paperId] = { text: '正在查找该文献的译文…', muted: true };
  renderResults();
  await ensureLibrary();
  const doc = state.documents.find((d) => d.paper_id === paperId);
  if (!doc) {
    state.absZh[paperId] = { text: '尚未导入该文献的 PDF 全文。请先在「文献库」上传 PDF 并执行解析与翻译。', muted: true };
    renderResults();
    return;
  }
  const translation = await apiOrNull(`/documents/${doc.id}/translation`);
  const sections = (translation && translation.sections) || [];
  const abstract = sections.find((s) => (s.section_type || '').toLowerCase() === 'abstract')
    || sections.find((s) => /abstract|摘要/i.test(s.title || ''));
  if (!abstract || !abstract.target.trim()) {
    state.absZh[paperId] = {
      text: `文档 #${doc.id} 尚无可用的摘要译文（当前翻译状态：${translation ? translation.status : '未翻译'}）。可在「文献库」中触发翻译。`,
      muted: true,
    };
  } else {
    state.absZh[paperId] = { text: abstract.target, muted: false };
  }
  renderResults();
}

/* ── 待下载清单 ── */
function downloadAvailability(paper) {
  const value = String((paper && paper.oa_pdf_url) || '').trim();
  if (!value) {
    const status = String((paper && paper.oa_status) || '').toLowerCase();
    if (status === 'closed') return { supported: false, reason: '未发现开放全文' };
    if (status === 'unknown') return { supported: false, reason: '开放权限未知' };
    if (['gold', 'green', 'hybrid', 'bronze'].includes(status)) {
      return { supported: false, reason: '暂无可用 PDF 直链' };
    }
    return { supported: false, reason: '未提供开放全文链接' };
  }
  try {
    const url = new URL(value);
    const hostname = url.hostname.toLowerCase();
    if (!['http:', 'https:'].includes(url.protocol)) {
      return { supported: false, reason: '全文链接协议不受支持' };
    }
    if (hostname === 'example.test' || hostname.endsWith('.example.test')) {
      return { supported: false, reason: '测试数据不支持下载' };
    }
    return { supported: true, reason: '', url: url.href };
  } catch (error) {
    return { supported: false, reason: '全文链接无效' };
  }
}

function currentMarkedPaper(marked) {
  const current = state.results.find((paper) => paper.id === marked.id)
    || state.paperCache[marked.id];
  return current ? Object.assign({}, marked, current) : marked;
}

function toggleMark(paper) {
  const downloadInfo = downloadAvailability(paper);
  if (!downloadInfo.supported) {
    toast(`暂不支持下载：${downloadInfo.reason}`, true);
    return;
  }
  const index = persisted.marked.findIndex((m) => m.id === paper.id);
  if (index >= 0) persisted.marked.splice(index, 1);
  else {
    persisted.marked.push({
      id: paper.id, doi: paper.doi || '', title: paper.title,
      journal: paper.journal_name || '', year: paper.published_year || '',
      oa_status: paper.oa_status || 'unknown', oa_pdf_url: downloadInfo.url,
    });
  }
  saveStore();
  renderMarked();
  renderResults();
}

function renderMarked() {
  $$('[data-marked-count]').forEach((node) => { node.textContent = persisted.marked.length; });
  const body = $('#drawer-body');
  const summary = $('#download-summary');
  const batchButton = $('#download-marked');
  const entries = persisted.marked.map(currentMarkedPaper);
  const availableCount = entries.filter((paper) => downloadAvailability(paper).supported).length;
  const unsupportedCount = entries.length - availableCount;
  summary.textContent = persisted.marked.length
    ? `可下载 ${availableCount} 篇 · 不支持 ${unsupportedCount} 篇`
    : '尚未加入待下载文章';
  batchButton.disabled = availableCount === 0 || state.batchDownloading;
  batchButton.textContent = state.batchDownloading
    ? '正在下载开放全文…'
    : availableCount
    ? `一键下载可用全文（${availableCount}）`
    : '一键下载可用全文';
  if (!persisted.marked.length) {
    body.innerHTML = '<div class="drawer-empty">清单为空<br>在检索结果中点击「加入待下载」收集 DOI</div>';
    return;
  }
  body.innerHTML = entries.map((m, i) => {
    const info = downloadAvailability(m);
    const downloadState = state.markedDownloadState[m.id];
    const status = {
      downloading: { label: '下载中', className: 'downloading' },
      downloaded: { label: '已下载', className: 'downloaded' },
      failed: { label: '失败', className: 'failed' },
    }[downloadState];
    const label = status ? status.label : (info.supported ? '可下载' : '不支持下载');
    const statusClass = status ? status.className : (info.supported ? 'ok' : 'off');
    const busy = downloadState === 'downloading';
    return `<div class="mk">
    <div class="mk-top">
      <div class="t">${esc(m.title)}</div>
      <span class="mk-status ${statusClass}">${label}</span>
    </div>
    <div class="r">
      <span class="d">${esc(m.doi || '无 DOI')}</span>
      <span class="m">${esc([m.journal, m.year].filter(Boolean).join(' · '))}</span>
      <div class="spacer"></div>
      <button class="mk-download" data-download-marked="${i}" ${info.supported && !busy ? '' : 'disabled'}>${busy ? '下载中…' : (info.supported ? '下载' : '不支持')}</button>
      <button class="rm" data-unmark="${i}">移除</button>
    </div>
    ${info.supported ? '' : `<div class="mk-reason">${esc(info.reason)}</div>`}
  </div>`;
  }).join('');
}

async function refreshMarkedDownloadInfo() {
  if (!persisted.marked.length) return;
  const papers = await Promise.all(
    persisted.marked.map((marked) => apiOrNull(`/papers/${marked.id}`))
  );
  papers.forEach((paper, index) => {
    if (!paper) return;
    persisted.marked[index] = Object.assign({}, persisted.marked[index], {
      doi: paper.doi || persisted.marked[index].doi || '',
      title: paper.title || persisted.marked[index].title,
      journal: paper.journal_name || persisted.marked[index].journal || '',
      year: paper.published_year || persisted.marked[index].year || '',
      oa_status: paper.oa_status || 'unknown',
      oa_pdf_url: paper.oa_pdf_url || '',
    });
    state.paperCache[paper.id] = paper;
  });
  saveStore();
  renderMarked();
}

function attachmentFilename(response, paper) {
  const disposition = response.headers.get('Content-Disposition') || '';
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (encoded) {
    try { return decodeURIComponent(encoded[1]); } catch (error) { /* 使用回退文件名 */ }
  }
  const plain = disposition.match(/filename="?([^";]+)"?/i);
  return plain ? plain[1] : `paper-${paper.id}.pdf`;
}

async function launchPaperDownload(paper) {
  const info = downloadAvailability(paper);
  if (!info.supported) return false;
  const response = await fetch(`${API}/papers/${encodeURIComponent(paper.id)}/download`);
  if (!response.ok) {
    const text = await response.text();
    let payload = null;
    try { payload = text ? JSON.parse(text) : null; } catch (error) { payload = null; }
    const detail = payload && payload.error;
    throw new Error(detail ? detail.message : `PDF 下载失败（HTTP ${response.status}）`);
  }
  const blob = await response.blob();
  download(attachmentFilename(response, paper), blob, blob.type || 'application/pdf');
  return true;
}

async function downloadMarkedPapers() {
  if (state.batchDownloading) return;
  const entries = persisted.marked.map(currentMarkedPaper);
  const available = entries.filter((paper) => downloadAvailability(paper).supported);
  const unsupported = entries.length - available.length;
  if (!available.length) {
    toast('清单中没有支持下载的开放全文', true);
    return;
  }
  state.batchDownloading = true;
  renderMarked();
  let downloaded = 0;
  let failed = 0;
  for (const paper of available) {
    state.markedDownloadState[paper.id] = 'downloading';
    renderMarked();
    try {
      await launchPaperDownload(paper);
      state.markedDownloadState[paper.id] = 'downloaded';
      downloaded += 1;
    } catch (error) {
      state.markedDownloadState[paper.id] = 'failed';
      failed += 1;
    }
    renderMarked();
  }
  state.batchDownloading = false;
  renderMarked();
  toast(
    `已下载 ${downloaded} 篇${failed ? ` · ${failed} 篇失败` : ''}`
      + `${unsupported ? ` · ${unsupported} 篇不支持` : ''}`,
    failed > 0
  );
}

/* ── 文献库 ── */
async function ensureLibrary() {
  if (!state.libLoaded) await loadLibrary();
}

async function loadLibrary() {
  const data = await apiOrNull('/documents?page_size=100');
  state.documents = (data && data.items) || [];
  state.libLoaded = true;
  renderNav();
  await Promise.all(state.documents.map(async (doc) => {
    const [translation, chunks, reactionSets] = await Promise.all([
      apiOrNull(`/documents/${doc.id}/translation`),
      apiOrNull(`/documents/${doc.id}/chunks?page_size=1`),
      apiOrNull(`/documents/${doc.id}/reaction-sets?page_size=50`),
    ]);
    state.docMeta[doc.id] = {
      translation,
      chunkTotal: chunks ? chunks.total : 0,
      reactionSets: (reactionSets && reactionSets.items) || [],
    };
    // 卡片上的标签需要完整的 category_details，document.paper 摘要里没有
    if (doc.paper_id != null && !state.paperCache[doc.paper_id]) {
      const paper = await apiOrNull(`/papers/${doc.paper_id}`);
      if (paper) state.paperCache[doc.paper_id] = paper;
    }
  }));
  renderLibrary();
  renderUploadProjectOptions();
  scheduleLibraryPoll();
}

let pollTimer = null;
function scheduleLibraryPoll() {
  clearTimeout(pollTimer);
  const busy = state.documents.some((d) =>
    d.parse_status === 'parsing' || d.index_status === 'indexing' || d.chemistry_status === 'extracting'
    || ((state.docMeta[d.id] || {}).translation || {}).status === 'pending');
  if (!busy) return;
  pollTimer = setTimeout(() => { if (state.libLoaded) loadLibrary(); }, 2500);
}

function docTitle(doc) {
  return (doc.paper && doc.paper.title) || doc.original_name || `文档 #${doc.id}`;
}

function translationTag(translation) {
  if (!translation) return { cls: 'todo', label: '未翻译' };
  if (translation.status === 'done') return { cls: 'done', label: '已翻译' };
  if (translation.status === 'pending') return { cls: 'doing', label: '翻译中' };
  if (translation.status === 'failed') return { cls: 'fail', label: '翻译失败' };
  return { cls: 'todo', label: '未翻译' };
}

function parseTag(doc) {
  const map = {
    parsed: { cls: 'done', label: '已解析' },
    parsing: { cls: 'info', label: '解析中…' },
    failed: { cls: 'fail', label: '解析失败' },
  };
  return map[doc.parse_status] || { cls: 'todo', label: '未解析' };
}

function ragTag(doc, meta) {
  if (doc.index_status === 'indexed') return { cls: 'rag', label: `RAG ✓ ${meta.chunkTotal} 段` };
  if (doc.index_status === 'indexing') return { cls: 'info', label: '切分入库中…' };
  if (doc.index_status === 'failed') return { cls: 'fail', label: 'RAG 失败' };
  return { cls: 'todo', label: '未入库 RAG' };
}

function renderLibrary() {
  const grid = $('#lib-grid');
  if (!state.documents.length) {
    grid.innerHTML = '<div class="empty-state">文献库为空<br>上传第一份 PDF 开始解析与翻译</div>';
    return;
  }
  grid.innerHTML = state.documents.map((doc) => {
    const meta = state.docMeta[doc.id] || { chunkTotal: 0 };
    const parse = parseTag(doc);
    const trans = translationTag(meta.translation);
    const rag = ragTag(doc, meta);
    const paper = doc.paper;
    const project = persisted.projects.find((p) => p.docs.includes(doc.id));
    const metaLine = [
      paper && paper.journal_name,
      paper && paper.published_date,
      doc.num_pages ? `${doc.num_pages} 页` : null,
      doc.created_at ? `${doc.created_at.slice(0, 10)} 上传` : null,
      project ? `项目「${project.name}」` : null,
    ].filter(Boolean).join(' · ');
    const error = doc.parse_error || doc.index_error
      || (meta.translation && meta.translation.status === 'failed' ? meta.translation.error : null);
    const note = error
      ? `<div class="lib-note bad">${esc(error)}</div>`
      : paper
        ? '<div class="lib-note ok">✓ 已关联检索到的文献记录</div>'
        : '<div class="lib-note idle">未关联文献记录，可重新上传时选择关联</div>';
    const readable = doc.parse_status === 'parsed';
    const cached = doc.paper_id != null ? state.paperCache[doc.paper_id] : null;
    const editing = state.tagEditor === doc.paper_id && doc.paper_id != null;
    const tags = cached && (cached.category_details || []).length ? tagChips(cached) : '';
    const tagRow = doc.paper_id == null
      ? '<div class="tag-note">该文档未关联文献记录，无法打标——标签存在 paper_categories 上，需先关联 paper。</div>'
      : `<div class="lib-foot">
          <span class="chips-label">标签</span>
          ${tags || '<span class="chips-label">尚未打标</span>'}
          <div class="spacer"></div>
          <button class="btn-ghost sm" data-doc-act="tag">${editing ? '收起' : '打标'}</button>
        </div>${editing && cached ? tagEditorMarkup(cached) : ''}`;
    const chemSets = meta.reactionSets || [];
    const chemRow = chemSets.length
      ? `<div class="lib-foot">
          <span class="tag ${chemSets.every((s) => s.export_ready) ? 'done' : 'todo'}">
            反应集 ${chemSets.length} · 待复核 ${chemSets.reduce((n, s) => n + s.unverified_count, 0)}</span>
          <div class="spacer"></div>
          <button class="btn-ghost sm" data-doc-act="chem">去复核</button>
        </div>`
      : '';
    return `<div class="lib-card" data-doc="${doc.id}">
      <div class="lib-head">
        <div class="lib-title">${esc(docTitle(doc))}</div>
        <span class="tag ${rag.cls}">${esc(rag.label)}</span>
        <span class="tag ${trans.cls}">${esc(trans.label)}</span>
      </div>
      <div class="lib-meta">${esc(metaLine || '—')}</div>
      ${note}
      <div class="lib-foot">
        <span class="tag ${parse.cls}">${esc(parse.label)}</span>
        <span class="doi">${paper && paper.doi ? `DOI ${esc(paper.doi)}` : 'DOI 未关联'}</span>
      </div>
      ${tagRow}
      ${chemRow}
      <div class="lib-actions">
        <button class="btn-ghost sm" data-doc-act="parse">解析</button>
        <button class="btn-ghost sm" data-doc-act="translate" ${readable ? '' : 'disabled'}>翻译</button>
        <button class="btn-ghost sm" data-doc-act="index" ${readable ? '' : 'disabled'}>建 RAG 索引</button>
        <button class="btn-ghost sm" data-doc-act="chemistry" ${readable ? '' : 'disabled'}>抽取化学库</button>
        <div class="spacer"></div>
        <button class="btn-ghost sm ${readable ? 'on' : ''}" data-doc-act="open" ${readable ? '' : 'disabled'}>
          ${readable ? '打开阅读' : '解析后可读'}</button>
      </div>
    </div>`;
  }).join('');
}

function renderUploadPaperOptions() {
  const select = $('#upload-paper');
  const options = ['<option value="">不关联</option>'].concat(
    persisted.marked.map((m) => `<option value="${m.id}">${esc(m.title.slice(0, 60))}</option>`)
  );
  select.innerHTML = options.join('');
}

function renderUploadProjectOptions() {
  const select = $('#upload-project');
  select.innerHTML = ['<option value="none">暂不加入</option>'].concat(
    persisted.projects.map((p) => `<option value="${esc(p.id)}">${esc(p.name)}</option>`)
  ).join('');
  select.value = persisted.projects.some((p) => p.id === persisted.uploadProject)
    ? persisted.uploadProject : 'none';
  $('#target-lang').value = persisted.targetLang;
}

async function uploadFiles(files) {
  const list = Array.from(files || []).filter((f) => /\.pdf$/i.test(f.name) || f.type === 'application/pdf');
  if (!list.length) { toast('只支持 PDF 文件', true); return; }
  const paperId = $('#upload-paper').value;
  for (const file of list) {
    const form = new FormData();
    form.append('file', file);
    if (paperId) form.append('paper_id', paperId);
    form.append('auto_process', 'true');
    form.append('target_lang', persisted.targetLang);
    try {
      const doc = await api('/documents', { method: 'POST', body: form });
      assignToProject(doc.id);
      toast(`${file.name} 已上传，正在自动处理…`);
    } catch (e) {
      if (e.status === 409 && e.payload && e.payload.error && e.payload.error.details) {
        const existing = e.payload.error.details.document;
        if (existing) { assignToProject(existing.id); toast(`${file.name} 已存在（文档 #${existing.id}）`); continue; }
      }
      toast(`${file.name} 上传失败：${e.message}`, true);
    }
  }
  await loadLibrary();
}

function assignToProject(docId) {
  const project = persisted.projects.find((p) => p.id === persisted.uploadProject);
  if (project && !project.docs.includes(docId)) { project.docs.push(docId); saveStore(); }
}

async function docAction(docId, action) {
  try {
    if (action === 'parse') {
      await api(`/documents/${docId}/parse`, { method: 'POST' });
      toast('已触发 GROBID 解析');
    } else if (action === 'translate') {
      await api(`/documents/${docId}/translate`, { method: 'POST', body: { target_lang: persisted.targetLang } });
      toast(`已触发翻译（${persisted.targetLang}）`);
    } else if (action === 'index') {
      await api(`/documents/${docId}/index`, { method: 'POST' });
      toast('已触发 RAG 分块与向量化');
    } else if (action === 'chemistry') {
      await api(`/documents/${docId}/extract-chemistry`, { method: 'POST' });
      toast('已触发化学库抽取，完成后到「化学库复核」逐条复核');
    }
  } catch (e) {
    toast(`操作失败：${e.message}`, true);
    return;
  }
  setTimeout(loadLibrary, 600);
}

/* ── 术语表管理 ── */
function glossaryTermById(id) {
  return glossaryTerms().find((term) => term.id === String(id));
}

function glossaryTermForText(text) {
  const normalized = String(text || '').trim().toLowerCase();
  if (!normalized) return null;
  return glossaryTerms().find((term) =>
    term.en.toLowerCase() === normalized || term.zh.toLowerCase() === normalized) || null;
}

function renderGlossaryManager() {
  const list = $('#glossary-manager-list');
  const summary = $('#glossary-manager-summary');
  const search = $('#glossary-search');
  if (!list || !summary || !search) return;
  if (search.value !== state.glossaryQuery) search.value = state.glossaryQuery;
  const query = state.glossaryQuery.trim().toLowerCase();
  const terms = glossaryTerms().filter((term) =>
    !query || `${term.en} ${term.zh}`.toLowerCase().includes(query));
  const pending = glossaryTerms().filter((term) => !term.en || !term.zh).length;
  summary.textContent = `${glossaryTerms().length} 个术语${pending ? ` · ${pending} 个待补充译名` : ''}`;
  if (!terms.length) {
    list.innerHTML = `<div class="glossary-manager-empty">${
      glossaryTerms().length ? '没有匹配的术语' : '术语表为空，可在上方添加或从阅读页选词加入'
    }</div>`;
    return;
  }
  list.innerHTML = terms.map((term) => {
    const incomplete = !term.en || !term.zh;
    return `<div class="glossary-manager-row" data-glossary-row="${esc(term.id)}">
      <div class="glossary-term-value ${term.en ? '' : 'pending'}">${esc(term.en || '待补充英文')}</div>
      <div class="glossary-term-value ${term.zh ? '' : 'pending'}">${esc(term.zh || '待补充中文')}</div>
      <div class="glossary-row-state">${incomplete ? '<span>待完善</span>' : ''}</div>
      <div class="glossary-row-actions">
        <button class="btn-ghost sm" type="button" data-glossary-edit="${esc(term.id)}">编辑</button>
        <button class="btn-ghost sm danger" type="button" data-glossary-delete="${esc(term.id)}">删除</button>
      </div>
    </div>`;
  }).join('');
}

function setGlossaryFormMessage(message, bad) {
  const node = $('#glossary-form-message');
  node.textContent = message || '';
  node.classList.toggle('bad', !!bad);
  node.hidden = !message;
}

function resetGlossaryForm() {
  state.glossaryEditingId = null;
  $('#glossary-form').reset();
  $('#glossary-form-title').textContent = '新增术语';
  $('#glossary-submit').textContent = '加入术语表';
  $('#glossary-cancel').hidden = true;
  setGlossaryFormMessage('', false);
}

function editGlossaryTerm(id) {
  const term = glossaryTermById(id);
  if (!term) return;
  state.glossaryEditingId = term.id;
  $('#glossary-en').value = term.en;
  $('#glossary-zh').value = term.zh;
  $('#glossary-form-title').textContent = '编辑术语';
  $('#glossary-submit').textContent = '保存修改';
  $('#glossary-cancel').hidden = false;
  setGlossaryFormMessage('', false);
  (term.en ? $('#glossary-en') : $('#glossary-zh')).focus();
}

function glossaryFormValidation(en, zh, excludedId) {
  if (!en && !zh) return '英文术语和中文译名至少填写一项。';
  if (en.length > MAX_GLOSSARY_TERM_LENGTH || zh.length > MAX_GLOSSARY_TERM_LENGTH) {
    return `单项术语不能超过 ${MAX_GLOSSARY_TERM_LENGTH} 个字符。`;
  }
  const duplicate = glossaryTerms().find((term) =>
    term.id !== excludedId && (
      (en && term.en.toLowerCase() === en.toLowerCase())
      || (zh && term.zh.toLowerCase() === zh.toLowerCase())
    ));
  return duplicate ? `术语表中已存在「${duplicate.en || duplicate.zh}」。` : '';
}

function saveGlossaryTerm() {
  const en = $('#glossary-en').value.trim().replace(/\s+/g, ' ');
  const zh = $('#glossary-zh').value.trim().replace(/\s+/g, ' ');
  const editingId = state.glossaryEditingId;
  const validation = glossaryFormValidation(en, zh, editingId);
  if (validation) {
    setGlossaryFormMessage(validation, true);
    return;
  }
  if (editingId) {
    const term = glossaryTermById(editingId);
    if (!term) {
      setGlossaryFormMessage('找不到要编辑的术语，请刷新后重试。', true);
      return;
    }
    term.en = en;
    term.zh = zh;
    toast(`已更新术语「${en || zh}」`);
  } else {
    glossaryTerms().unshift({ id: `g${Date.now().toString(36)}`, en, zh });
    toast(`已加入术语「${en || zh}」`);
  }
  saveStore();
  resetGlossaryForm();
  renderGlossaryManager();
  renderGlossbar();
  renderParas();
}

function deleteGlossaryTerm(id) {
  const term = glossaryTermById(id);
  if (!term) return;
  if (!window.confirm(`确认删除术语「${term.en || term.zh}」？\n\n删除后，正文中的对应高亮也会消失。`)) return;
  persisted.glossaryTerms = glossaryTerms().filter((item) => item.id !== term.id);
  if (state.glossaryEditingId === term.id) resetGlossaryForm();
  saveStore();
  renderGlossaryManager();
  renderGlossbar();
  renderParas();
  toast(`已删除术语「${term.en || term.zh}」`);
}

function addSelectionToGlossary() {
  const selected = state.selection;
  if (!selected) return;
  const text = selected.text.trim().replace(/\s+/g, ' ');
  if (!text || text.length > MAX_GLOSSARY_TERM_LENGTH) {
    toast(`术语应为 ${MAX_GLOSSARY_TERM_LENGTH} 个字符以内的词或短语`, true);
    return;
  }
  const existing = glossaryTermForText(text);
  if (existing) {
    hideSelectionPopover();
    toast(`「${text}」已在术语表中`);
    return;
  }
  const isChinese = selected.lang === 'zh' || (
    selected.lang !== 'en' && /[\u3400-\u9fff]/.test(text)
  );
  glossaryTerms().unshift({
    id: `g${Date.now().toString(36)}`,
    en: isChinese ? '' : text,
    zh: isChinese ? text : '',
  });
  saveStore();
  hideSelectionPopover();
  renderGlossbar();
  renderParas();
  toast(`已加入「${text}」；可在术语表管理补充译名`);
}

/* ── 双语阅读 ── */
function readerCandidates() {
  const project = persisted.projects.find((p) => p.id === state.readerProject);
  let pool = project
    ? state.documents.filter((d) => project.docs.includes(d.id))
    : state.documents;
  pool = pool.filter((doc) => documentMatchesCategory(doc, state.readerCategory));
  const q = state.readerSearch.trim().toLowerCase();
  if (!q) return pool;
  return pool.filter((d) => {
    const paper = d.paper || {};
    const categoryText = ((documentPaper(d) || {}).category_details || [])
      .map((category) => `${category.name} ${category.slug}`).join(' ');
    return `${docTitle(d)} ${paper.doi || ''} ${paper.journal_name || ''} ${categoryText}`
      .toLowerCase().includes(q);
  });
}

function renderReaderBar() {
  const select = $('#reader-project');
  select.innerHTML = ['<option value="all">全部文献</option>'].concat(
    persisted.projects.map((p) => `<option value="${esc(p.id)}">${esc(p.name)}</option>`)
  ).join('');
  select.value = state.readerProject;
  $('#reader-category').innerHTML = categoryOptions(state.readerCategory);

  $('#reader-modes').innerHTML = [
    { k: 'both', l: '对照' }, { k: 'zh', l: '仅中文' }, { k: 'en', l: '仅英文' },
    { k: 'qa', l: 'AI 问答' },
  ].map((m) => `<button data-mode="${m.k}" class="${state.readerMode === m.k ? 'on' : ''}">${m.l}</button>`).join('');

  const current = state.documents.find((d) => d.id === state.readerDocId);
  $('#reader-search').placeholder = current ? docTitle(current).slice(0, 64) : '搜索文献…';
  $('#font-label').textContent = `${persisted.fontSize}px`;
  $('#gloss-toggle').classList.toggle('on', persisted.glossary);
  const retranslate = $('#reader-retranslate');
  retranslate.disabled = !current || state.readerLoading || state.readerRetranslating;
  retranslate.dataset.busy = String(state.readerRetranslating);
  retranslate.textContent = state.readerRetranslating ? '翻译中…' : '再次翻译';
  retranslate.title = current
    ? `使用当前翻译引擎重新翻译为 ${state.readerTargetLang}`
    : '请先选择已解析文献';
  const qaMode = state.readerMode === 'qa';
  const readerPanes = $('.reader-panes');
  readerPanes.classList.toggle('qa-mode', qaMode);
  $('#reader-qa-language').hidden = !qaMode;
  $$('#reader-qa-language [data-reader-lang]').forEach((button) => {
    button.classList.toggle('on', button.dataset.readerLang === state.readerQaLang);
  });
  $('#pane-en').hidden = qaMode ? state.readerQaLang !== 'en' : state.readerMode === 'zh';
  $('#pane-zh').hidden = qaMode ? state.readerQaLang !== 'zh' : state.readerMode === 'en';
  $('#reader-chat-panel').hidden = !qaMode;
  renderReaderDrop();
  renderGlossbar();
  renderReaderQa();
  if (!state.readerDocId) {
    const first = readerCandidates().find((d) => d.parse_status === 'parsed');
    if (first) { openReader(first.id); return; }
  }
  renderParas();
}

function renderReaderDrop() {
  const drop = $('#reader-drop');
  drop.hidden = !state.readerDropOpen;
  if (!state.readerDropOpen) return;
  const hits = readerCandidates();
  if (!hits.length) { drop.innerHTML = '<div class="empty">该范围下没有匹配的文献</div>'; return; }
  drop.innerHTML = hits.map((d) => {
    const readable = d.parse_status === 'parsed';
    const trans = translationTag((state.docMeta[d.id] || {}).translation);
    return `<button data-pick="${d.id}" ${readable ? '' : 'disabled'}>
      <span class="flex ellipsis">${esc(docTitle(d))}</span>
      <span class="tag ${trans.cls}">${esc(trans.label)}</span></button>`;
  }).join('');
}

function renderGlossbar() {
  const bar = $('#glossbar');
  bar.hidden = !(persisted.glossary && state.page === 'reader');
  if (bar.hidden) return;
  bar.innerHTML = '<span class="lbl">术语表</span>'
    + glossaryTerms().slice(0, 8).map((term) =>
      `<button class="g" type="button" data-glossary-send="${esc(term.id)}"
        title="发送到对话：${esc(term.en || term.zh)}">${esc(term.en || '—')} <span>${esc(term.zh || '—')}</span></button>`
    ).join('')
    + '<button class="glossbar-manage" type="button" data-open-glossary>管理</button>'
    + '<span class="hint">选中文字可加入术语表或发送到对话</span>';
}

async function openReader(docId) {
  state.readerDocId = docId;
  state.activePara = null;
  state.readerLoading = true;
  setPage('reader');
  renderParas();
  const [sections, translation] = await Promise.all([
    apiOrNull(`/documents/${docId}/sections?page_size=100`),
    apiOrNull(`/documents/${docId}/translation`),
  ]);
  const src = (sections && sections.items) || [];
  const tr = (translation && translation.sections) || [];
  const byId = {};
  tr.forEach((t, i) => { byId[t.section_id != null ? t.section_id : `#${i}`] = t; });
  state.readerParas = src.map((s, i) => {
    const match = byId[s.id] || tr[i] || null;
    return {
      id: s.id,
      seq: s.seq != null ? s.seq : i,
      title: s.title || '',
      type: s.section_type || '',
      en: s.content || '',
      zh: match ? match.target : '',
      note: match ? match.note : null,
    };
  });
  state.readerLoading = false;
  state.translationStatus = translation ? translation.status : null;
  state.readerTargetLang = (translation && translation.target_lang) || persisted.targetLang || 'zh';
  renderReaderBar();
}

async function waitForTranslationJob(docId, translationId, timeoutMilliseconds = 120000) {
  const deadline = Date.now() + timeoutMilliseconds;
  while (Date.now() < deadline) {
    const translation = await api(`/documents/${docId}/translation`);
    if (translation.id === translationId && translation.status === 'done') return translation;
    if (translation.id === translationId && translation.status === 'failed') {
      throw new Error(translation.error || '翻译任务失败');
    }
    await waitForOnlineSearchPoll(900);
  }
  throw new Error('翻译等待超时，请稍后重试');
}

async function retranslateReader() {
  const docId = state.readerDocId;
  if (!docId || state.readerRetranslating) return;
  const targetLang = state.readerTargetLang || persisted.targetLang || 'zh';
  state.readerRetranslating = true;
  renderReaderBar();
  try {
    const job = await api(`/documents/${docId}/translate`, {
      method: 'POST',
      body: { target_lang: targetLang },
    });
    toast(`正在使用当前引擎重新翻译（${targetLang}）…`);
    const translation = await waitForTranslationJob(docId, job.job_id);
    if (state.docMeta[docId]) state.docMeta[docId].translation = translation;
    if (state.page === 'reader' && state.readerDocId === docId) await openReader(docId);
    toast('重新翻译完成，已更新对照内容');
  } catch (error) {
    toast(`重新翻译失败：${error.message}`, true);
  } finally {
    state.readerRetranslating = false;
    renderReaderBar();
  }
}

function highlight(text, lang) {
  if (!persisted.glossary || !text) return esc(text);
  const terms = glossaryTerms()
    .map((term) => lang === 'en' ? term.en : term.zh)
    .filter(Boolean);
  if (!terms.length) return esc(text);
  const sorted = Array.from(new Set(terms.map((term) => term.toLowerCase())))
    .sort((a, b) => b.length - a.length)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const re = new RegExp(`(${sorted.join('|')})`, 'gi');
  return String(text).split(re).map((part, i) => {
    if (i % 2 === 0) return esc(part);
    const g = lang === 'en'
      ? glossaryTerms().find((term) => term.en.toLowerCase() === part.toLowerCase())
      : glossaryTerms().find((term) => term.zh.toLowerCase() === part.toLowerCase());
    const counterpart = g ? (lang === 'en' ? g.zh : g.en) : '';
    return `<span class="term" role="button" tabindex="0" data-glossary-send="${g ? esc(g.id) : ''}"
      title="${counterpart ? esc(counterpart) : '发送到对话'}">${esc(part)}</span>`;
  }).join('');
}

function renderParas() {
  const paneEn = $('#paras-en');
  const paneZh = $('#paras-zh');
  if (state.readerLoading) {
    paneEn.innerHTML = '<div class="empty-state">加载中…</div>';
    paneZh.innerHTML = '';
    return;
  }
  if (!state.readerParas.length) {
    const hint = state.readerDocId
      ? '该文档还没有解析出章节<br>请在「文献库」中先执行 GROBID 解析'
      : '还没有可阅读的文档<br>请先在「文献库」上传并解析 PDF';
    paneEn.innerHTML = `<div class="empty-state">${hint}</div>`;
    paneZh.innerHTML = '';
    return;
  }
  const style = `font-size:${persisted.fontSize}px`;
  const build = (lang) => state.readerParas.map((p) => {
    const head = p.title ? `<div class="sec-head">${esc(p.title)}</div>` : '';
    const raw = lang === 'en' ? p.en : p.zh;
    const body = raw
      ? highlight(raw, lang)
      : '<span class="empty">（该段尚无译文，请在「文献库」中触发翻译）</span>';
    return `${head}<div class="para ${state.activePara === p.seq ? 'on' : ''}" id="p${lang}-${p.seq}"
      data-para="${p.seq}" style="${style}"><span class="no">¶${p.seq}</span>${body}</div>`;
  }).join('');
  paneEn.innerHTML = build('en');
  paneZh.innerHTML = build('zh');
}

function currentReaderQaThread() {
  if (!state.readerDocId) return [];
  const key = String(state.readerDocId);
  if (!state.readerQaThreads[key]) state.readerQaThreads[key] = [];
  return state.readerQaThreads[key];
}

function readerQaReady() {
  const current = state.documents.find((doc) => doc.id === state.readerDocId);
  return Boolean(current && current.index_status === 'indexed');
}

function readerQaEmptyMarkup(ready) {
  if (!ready) {
    return `<div class="reader-chat-empty unavailable">
      <div class="reader-chat-orbit" aria-hidden="true">AI</div>
      <div class="title">当前论文尚未进入知识库</div>
      <div class="desc">请先在「文献库」完成解析并建立 RAG 索引，再回到这里提问。</div>
    </div>`;
  }
  const prompts = [
    '这篇论文的核心结论是什么？',
    '请梳理实验条件和关键等离子体参数。',
    '哪些结论有原文证据支持？',
  ];
  return `<div class="reader-chat-empty">
    <div class="reader-chat-orbit" aria-hidden="true">AI</div>
    <div class="title">边读，边问这篇论文</div>
    <div class="desc">回答只使用当前论文的已索引段落，并保留可回查引用。</div>
    <div class="reader-chat-suggestions">
      ${prompts.map((prompt) => `<button type="button" data-reader-question="${esc(prompt)}">${esc(prompt)}</button>`).join('')}
    </div>
  </div>`;
}

function renderReaderQa() {
  const panel = $('#reader-chat-panel');
  if (!panel || panel.hidden) return;
  const current = state.documents.find((doc) => doc.id === state.readerDocId);
  const ready = readerQaReady();
  const input = $('#reader-chat-input');
  const send = $('#reader-chat-send');
  $('#reader-chat-context').textContent = current
    ? docTitle(current)
    : '选择一篇已解析论文后开始提问';
  $('#reader-chat-status').textContent = ready ? '当前论文 · 已索引' : '需要 RAG 索引';
  $('#reader-chat-status').classList.toggle('ready', ready);
  input.disabled = !ready || state.readerQaTyping;
  send.disabled = !ready || state.readerQaTyping;
  input.placeholder = ready ? '针对当前论文提问…' : '当前论文尚未建立 RAG 索引';

  const messages = currentReaderQaThread();
  const log = $('#reader-chat-log');
  if (!messages.length && !state.readerQaTyping) {
    log.innerHTML = readerQaEmptyMarkup(ready);
    return;
  }
  log.innerHTML = messages.map((message, messageIndex) => {
    if (message.role === 'user') {
      return `<div class="msg-row user"><div class="bubble">
        <div class="who">你</div><div class="body">${esc(message.text)}</div></div></div>`;
    }
    const sources = message.sources || [];
    const citations = sources.map((source, sourceIndex) => `<button class="cite"
      data-reader-cite="${messageIndex}:${sourceIndex}"
      title="${esc(source.section_title || '')} · 点击跳回左侧原文">[${sourceIndex + 1}·¶${
        source.section_seq != null ? source.section_seq : '?'}]</button>`).join('');
    const hits = sources.length
      ? `<div class="hits">命中 ${sources.length} 个当前论文切块 · 点击引用回到原文</div>`
      : '';
    return `<div class="msg-row ai"><div class="bubble">
      <div class="who">助手 · 当前论文</div>${hits}
      <div class="body">${esc(message.text)}${citations ? ` ${citations}` : ''}</div>
    </div></div>`;
  }).join('') + (state.readerQaTyping
    ? '<div class="typing"><i></i><i></i><i></i><span>正在检索当前论文并生成回答…</span></div>'
    : '');
  log.scrollTop = log.scrollHeight;
}

async function sendReaderQa(text) {
  const question = String(text || '').trim();
  const docId = state.readerDocId;
  if (!question || state.readerQaTyping || !docId) return;
  if (!readerQaReady()) {
    toast('当前论文尚未建立 RAG 索引，请先在文献库完成索引', true);
    return;
  }
  const messages = currentReaderQaThread();
  messages.push({ role: 'user', text: question });
  state.readerQaTyping = true;
  $('#reader-chat-input').value = '';
  renderReaderQa();
  try {
    const data = await api('/rag/query', {
      method: 'POST',
      body: { question, document_ids: [docId], top_k: 6 },
    });
    messages.push({
      role: 'ai',
      text: stripSourceTrailer(data.answer) || '（检索到的切块没有可用内容）',
      sources: data.sources || [],
    });
  } catch (error) {
    messages.push({ role: 'ai', text: `检索失败：${error.message}`, sources: [] });
  } finally {
    state.readerQaTyping = false;
    renderReaderQa();
    $('#reader-chat-input').focus();
  }
}

let scrollLock = false;
function syncScroll(src, dst) {
  if (scrollLock || src.hidden || dst.hidden) return;
  scrollLock = true;
  const d1 = src.scrollHeight - src.clientHeight;
  const d2 = dst.scrollHeight - dst.clientHeight;
  if (d1 > 0 && d2 > 0) dst.scrollTop = (src.scrollTop / d1) * d2;
  requestAnimationFrame(() => { scrollLock = false; });
}

async function jumpToSource(docId, seq) {
  if (state.readerDocId !== docId) await openReader(docId);
  else setPage('reader');
  state.activePara = seq;
  renderParas();
  setTimeout(() => {
    const en = document.getElementById(`pen-${seq}`);
    const zh = document.getElementById(`pzh-${seq}`);
    if (en) $('#pane-en').scrollTop = Math.max(0, en.offsetTop - 70);
    if (zh) $('#pane-zh').scrollTop = Math.max(0, zh.offsetTop - 70);
  }, 60);
}

/* ── AI 问答 ── */
function chatDocumentIds() {
  const available = indexedDocs();
  if (state.chatScope === 'all') return state.chatCategory ? available.map((doc) => doc.id) : [];
  if (state.chatScope === 'project') {
    const project = persisted.projects.find((p) => p.id === state.selProject);
    return project ? available.filter((doc) => project.docs.includes(doc.id)).map((doc) => doc.id) : [];
  }
  return state.chatDocs.filter((id) => available.some((doc) => doc.id === id));
}

function indexedDocs() {
  return state.documents.filter((doc) =>
    doc.index_status === 'indexed' && documentMatchesCategory(doc, state.chatCategory));
}

function totalChunks(docs) {
  return (docs || state.documents).reduce(
    (sum, d) => sum + ((state.docMeta[d.id] || {}).chunkTotal || 0),
    0
  );
}

function renderChatSide() {
  const available = indexedDocs();
  const chunks = totalChunks(available);
  const activeTag = categoryBySlug(state.chatCategory);
  const scopes = [
    { k: 'single', l: '单篇文献', h: '精读' },
    { k: 'project', l: '项目问答', h: '跨文献' },
    { k: 'all', l: '全库 RAG', h: `${chunks} 段` },
  ];
  $('#scope-opts').innerHTML = scopes.map((s) => `
    <button class="scope-btn ${state.chatScope === s.k ? 'on' : ''}" data-scope="${s.k}">
      <span class="dot"></span>${s.l}<span class="hint">${s.h}</span></button>`).join('');
  $('#chat-category').innerHTML = categoryOptions(state.chatCategory);

  $('#proj-picker').hidden = state.chatScope !== 'project';
  $('#all-note').hidden = state.chatScope !== 'all';
  $('#doc-picker').hidden = state.chatScope !== 'single';
  $('#all-doc-count').textContent = available.length;
  $('#all-chunk-count').textContent = chunks;
  $('#all-note .allbox').innerHTML = activeTag
    ? `标签「${esc(activeTag.name)}」匹配 <span id="all-doc-count">${available.length}</span> 篇已索引文献、`
      + `<span id="all-chunk-count">${chunks}</span> 个切块。`
    : `全库检索覆盖全部 <span id="all-doc-count">${available.length}</span> 篇文献的 `
      + `<span id="all-chunk-count">${chunks}</span> 个切块，无需选择文献。`;

  if (!state.selProject && persisted.projects.length) state.selProject = persisted.projects[0].id;
  $('#proj-rows').innerHTML = persisted.projects.length
    ? persisted.projects.map((p) => `
      <button class="proj-btn ${state.selProject === p.id ? 'on' : ''}" data-proj="${esc(p.id)}">
        <span class="dot"></span><span class="name">${esc(p.name)}</span>
        <span class="cnt">${p.docs.length} 篇</span></button>`).join('')
    : '<div class="side-note">还没有项目，可在「文献库」中新建</div>';
  const project = persisted.projects.find((p) => p.id === state.selProject);
  $('#proj-docs').innerHTML = ((project && project.docs) || [])
    .map((id) => state.documents.find((d) => d.id === id))
    .filter((doc) => doc && documentMatchesCategory(doc, state.chatCategory))
    .map((d) => `<div class="proj-doc">${esc(docTitle(d))}</div>`).join('');

  const q = state.docSearch.trim().toLowerCase();
  const docs = available.filter((d) => {
    const categoryText = ((documentPaper(d) || {}).category_details || [])
      .map((category) => `${category.name} ${category.slug}`).join(' ');
    return !q || `${docTitle(d)} ${(d.paper && d.paper.doi) || ''} ${categoryText}`
      .toLowerCase().includes(q);
  });
  $('#doc-opts').innerHTML = docs.length
    ? docs.map((d) => {
      const on = state.chatDocs.includes(d.id);
      const meta = state.docMeta[d.id] || {};
      return `<button class="doc-btn ${on ? 'on' : ''}" data-chatdoc="${d.id}">
        <span class="box">${on ? '✓' : ''}</span>
        <span class="name">${esc(docTitle(d))}</span>
        <span class="tag rag">${meta.chunkTotal || 0} 段</span></button>`;
    }).join('')
    : '<div class="side-note">没有已建索引的文档，请先在「文献库」执行「建 RAG 索引」</div>';

  $('#presets').innerHTML = allPresets().map((p) => `
    <div class="preset-item">
      <button class="preset-btn" data-preset-id="${esc(p.id)}">
        <div class="cmd">${esc(p.cmd)}</div>
        <div class="desc">${esc(p.desc || '预设指令')}</div>
      </button>
      <div class="preset-actions">
        <button type="button" title="编辑 ${esc(p.cmd)}" aria-label="编辑 ${esc(p.cmd)}" data-preset-edit="${esc(p.id)}">编辑</button>
        <button class="danger" type="button" title="删除 ${esc(p.cmd)}" aria-label="删除 ${esc(p.cmd)}" data-preset-delete="${esc(p.id)}">删除</button>
      </div>
    </div>`).join('');
  renderPresetEditor();

  const ids = chatDocumentIds();
  const tagSummary = activeTag ? ` · 标签「${activeTag.name}」` : '';
  $('#scope-summary').textContent = state.chatScope === 'all'
    ? `范围：全库 RAG${tagSummary} · ${available.length} 篇 · ${chunks} 个切块向量`
    : state.chatScope === 'project'
      ? `范围：项目「${project ? project.name : '未选择'}」${tagSummary} · ${ids.length} 篇`
      : ids.length
        ? `范围：单篇精读${tagSummary} · ${docTitle(state.documents.find((d) => d.id === ids[0]) || {})}`
        : `范围：单篇精读${tagSummary} · 未选择文献`;
}

function renderPresetEditor() {
  const editor = $('#preset-editor');
  const draft = state.presetEditor;
  editor.hidden = !draft;
  $('#preset-error').hidden = true;
  if (!draft) return;
  $('#preset-cmd').value = draft.cmd || '';
  $('#preset-desc').value = draft.desc || '';
  $('#preset-question').value = draft.q || '';
}

function openPresetEditor(preset) {
  state.presetEditor = preset
    ? { id: preset.id, cmd: preset.cmd, desc: preset.desc, q: preset.q }
    : { id: null, cmd: '/', desc: '', q: '' };
  renderPresetEditor();
  $('#preset-cmd').focus();
  $('#preset-cmd').setSelectionRange($('#preset-cmd').value.length, $('#preset-cmd').value.length);
}

function presetEditorError(message) {
  const error = $('#preset-error');
  error.textContent = message;
  error.hidden = false;
}

async function savePresetEditor() {
  const draft = state.presetEditor;
  if (!draft) return;
  const cmd = normalizePresetCommand($('#preset-cmd').value);
  const desc = $('#preset-desc').value.trim();
  const q = $('#preset-question').value.trim();
  if (!/^\/[^\s/]{1,23}$/.test(cmd)) {
    presetEditorError('快捷指令需为 / 开头且不能包含空格，最多 24 个字符');
    $('#preset-cmd').focus();
    return;
  }
  if (!q) {
    presetEditorError('发送内容不能为空');
    $('#preset-question').focus();
    return;
  }
  const duplicate = allPresets().find((preset) =>
    preset.id !== draft.id && preset.cmd.toLowerCase() === cmd.toLowerCase());
  if (duplicate) {
    presetEditorError(`快捷指令 ${cmd} 已存在`);
    $('#preset-cmd').focus();
    return;
  }
  const editing = draft.id != null;
  try {
    await api(editing ? `/prompt-presets/${draft.id}` : '/prompt-presets', {
      method: editing ? 'PUT' : 'POST',
      body: { command: cmd, description: desc || null, prompt: q },
    });
    await loadPresets();
    state.presetEditor = null;
    renderChatSide();
    toast(editing ? `已更新预设 ${cmd}` : `已保存预设 ${cmd}`);
  } catch (error) {
    if (error.code === 'prompt_preset_conflict') {
      presetEditorError(`快捷指令 ${cmd} 已存在`);
      $('#preset-cmd').focus();
      return;
    }
    presetEditorError(`保存失败：${error.message}`);
  }
}

async function deletePreset(id) {
  const preset = presetById(id);
  if (!preset || !window.confirm(`删除预设 ${preset.cmd}？`)) return;
  try {
    await api(`/prompt-presets/${id}`, { method: 'DELETE' });
    state.presets = state.presets.filter((item) => String(item.id) !== String(id));
    if (state.presetEditor && String(state.presetEditor.id) === String(id)) state.presetEditor = null;
    renderChatSide();
    toast(`已删除预设 ${preset.cmd}`);
  } catch (error) {
    toast(`删除失败：${error.message}`, true);
  }
}

function stripSourceTrailer(answer) {
  const lines = String(answer || '').split('\n');
  const kept = [];
  for (const line of lines) {
    if (/^Source:\s/i.test(line.trim())) continue;
    kept.push(line);
  }
  return kept.join('\n').trim();
}

function renderChatLog() {
  const log = $('#chat-log');
  log.innerHTML = state.messages.map((m, mi) => {
    if (m.role === 'user') {
      return `<div class="msg-row user"><div class="bubble">
        <div class="who">你</div><div class="body">${esc(m.text)}</div></div></div>`;
    }
    const sources = m.sources || [];
    const hits = sources.length
      ? `<div class="hits">向量检索命中 ${sources.length} 个切块 · top 相似度 ${
        sources[0].score != null ? Number(sources[0].score).toFixed(2) : '—'} · 引用以 [n·¶段] 标注</div>`
      : '';
    const cites = sources.map((s, i) => `<button class="cite" data-cite="${mi}:${i}"
      title="${esc(s.section_title || '')} · ${esc(s.section_type || '')} · 点击跳转原文">[${i + 1}·¶${s.section_seq != null ? s.section_seq : '?'}]</button>`).join('');
    const related = (m.related || []).length ? `<div class="related">
      <div class="related-label">相关文献 · 本地文献库检索</div>
      <div class="related-list">${m.related.map((p) => `<div class="related-item">
        <div class="t">${esc(p.title)}</div>
        <div class="r">
          <span class="m">${esc([p.journal_name, p.published_year].filter(Boolean).join(' · '))}</span>
          <div class="spacer"></div>
          <button class="btn-ghost" data-rel-copy="${esc(p.doi || '')}" ${p.doi ? '' : 'disabled'}>复制 DOI</button>
        </div></div>`).join('')}</div></div>` : '';
    return `<div class="msg-row ai"><div class="bubble">
      <div class="who">助手 · 引用 RAG 切块</div>
      ${hits}
      <div class="body">${esc(m.text)}${cites ? ` ${cites}` : ''}</div>
      ${related}</div></div>`;
  }).join('') + (state.typing
    ? `<div class="typing"><i></i><i></i><i></i><span>正在检索 RAG 切块向量并生成回答…</span></div>` : '');
  log.scrollTop = log.scrollHeight;
}

async function sendChat(text) {
  const question = (text || '').trim();
  if (!question || state.typing) return;
  const ids = chatDocumentIds();
  if ((state.chatScope !== 'all' || state.chatCategory) && !ids.length) {
    toast('请先在左侧选择文献或项目', true);
    return;
  }
  state.messages.push({ role: 'user', text: question });
  state.typing = true;
  state.chatInput = '';
  $('#chat-input').value = '';
  state.slashOpen = false;
  $('#slash-pop').hidden = true;
  renderChatLog();
  try {
    const data = await api('/rag/query', {
      method: 'POST',
      body: { question, document_ids: ids, top_k: 6 },
    });
    const related = await relatedPapers(question);
    state.messages.push({
      role: 'ai',
      text: stripSourceTrailer(data.answer) || '（检索到的切块没有可用内容）',
      sources: data.sources || [],
      related,
    });
  } catch (e) {
    state.messages.push({ role: 'ai', text: `检索失败：${e.message}`, sources: [], related: [] });
  }
  state.typing = false;
  renderChatLog();
}

async function relatedPapers(question) {
  const words = question.replace(/[^\w\s一-龥]/g, ' ').split(/\s+/).filter((w) => w.length > 2);
  if (!words.length) return [];
  const params = new URLSearchParams({
    q: words.slice(0, 4).join(' '),
    sort: 'relevance',
    page_size: '2',
  });
  if (state.chatCategory) params.set('category', state.chatCategory);
  const data = await apiOrNull(`/papers?${params.toString()}`);
  return (data && data.items) || [];
}

/* ── 化学库复核 ── */
function chemistryDocs() {
  return state.documents.filter((d) => ((state.docMeta[d.id] || {}).reactionSets || []).length
    || d.chemistry_status === 'extracted' || d.chemistry_status === 'extracting');
}

/* 进入本页时自动选中第一个有反应集的文档，否则左侧列了文档而右侧空着 */
async function openChemistry() {
  const docs = chemistryDocs();
  if (!docs.length) { renderChemistry(); return; }
  const stillThere = docs.some((d) => d.id === state.chemDocId);
  if (stillThere && state.chemSet) { renderChemistry(); return; }
  await loadChemDoc((stillThere ? state.chemDocId : docs[0].id));
}

async function loadChemDoc(docId) {
  state.chemDocId = docId;
  state.chemSetId = null;
  state.chemSet = null;
  const data = await apiOrNull(`/documents/${docId}/reaction-sets?page_size=50`);
  state.chemSets = (data && data.items) || [];
  if (state.chemSets.length) await loadChemSet(state.chemSets[0].id);
  else renderChemistry();
}

async function loadChemSet(setId) {
  state.chemSetId = setId;
  state.chemLoading = true;
  renderChemistry();
  state.chemSet = await apiOrNull(`/reaction-sets/${setId}`);
  state.chemLoading = false;
  renderChemistry();
}

function renderChemistry() {
  const docs = chemistryDocs();
  $('#chem-docs').innerHTML = docs.length
    ? docs.map((d) => {
      const sets = (state.docMeta[d.id] || {}).reactionSets || [];
      const pending = sets.reduce((n, s) => n + s.unverified_count, 0);
      return `<button class="doc-btn ${state.chemDocId === d.id ? 'on' : ''}" data-chemdoc="${d.id}">
        <span class="name">${esc(docTitle(d))}</span>
        <span class="tag ${pending ? 'todo' : 'done'}">${sets.length ? (pending ? `待 ${pending}` : '已复核') : d.chemistry_status || '—'}</span>
      </button>`;
    }).join('')
    : '<div class="side-note">还没有抽取过化学库。在「文献库」中对已解析文档点「抽取化学库」。</div>';

  $('#chem-sets').innerHTML = state.chemSets.length
    ? state.chemSets.map((s) => `<button class="set-btn ${state.chemSetId === s.id ? 'on' : ''}" data-chemset="${s.id}">
        <span class="name">${esc(s.gas_mixture || s.name || `反应集 #${s.id}`)}</span>
        <span class="tag ${s.export_ready ? 'done' : 'todo'}">${s.verified_count}/${s.reaction_count}</span>
      </button>`).join('')
    : '<div class="side-note">该文档下没有反应集</div>';

  const set = state.chemSet;
  const body = $('#chem-body');
  const gate = $('#chem-gate');
  $('#chem-exports').hidden = !set;

  if (state.chemLoading) {
    $('#chem-summary').textContent = '载入中…';
    gate.hidden = true;
    body.innerHTML = '<div class="empty-state">载入中…</div>';
    return;
  }
  if (!set) {
    $('#chem-summary').textContent = docs.length ? '选择左侧文档以载入反应集' : '尚无可复核的反应集';
    gate.hidden = true;
    body.innerHTML = `<div class="empty-state">${docs.length
      ? '选择左侧的文档与反应集开始复核'
      : '还没有抽取过化学库<br>先在「文献库」对已解析文档执行「抽取化学库」'}</div>`;
    return;
  }

  $('#chem-summary').textContent = [
    set.gas_mixture ? `气体 ${set.gas_mixture}` : null,
    set.lxcat_db ? `LXCat ${set.lxcat_db}` : 'LXCat 未识别',
    `${set.reaction_count} 条反应`,
    `已复核 ${set.verified_count}`,
    set.status ? `状态 ${set.status}` : null,
  ].filter(Boolean).join(' · ');

  gate.hidden = false;
  gate.className = set.export_ready ? 'gate ok' : 'gate';
  gate.innerHTML = set.export_ready
    ? '✓ 人工复核闸门已通过：全部反应均已 verified，可以导出仿真输入。'
    : `⚠ 人工复核闸门未通过：还有 <b>${set.unverified_count}</b> 条反应未复核。闸门不可绕过——此时调用导出接口会返回 409。`;

  body.innerHTML = set.reactions.map((r) => reactionCard(r)).join('')
    || '<div class="empty-state">该反应集没有反应条目</div>';
}

function reactionCard(r) {
  const source = [
    r.source_label ? `<span class="lbl">出处</span>${esc(r.source_label)}` : null,
    r.source_section_title && !r.source_label ? `<span class="lbl">章节</span>${esc(r.source_section_title)}` : null,
  ].filter(Boolean).join(' · ');
  const excerpt = r.source_excerpt
    ? `<div><span class="lbl">原文</span><span class="ex">${esc(r.source_excerpt)}</span></div>` : '';
  const audits = state.chemAudit[r.id] && (r.audit_log || []).length
    ? `<div class="rx-audit"><div class="lbl">复核审计 · ${r.audit_log.length} 条</div>${
      r.audit_log.map((a) => `<div class="row">
        <span class="who">${esc(reviewerDisplayName(a.verified_by))}</span> · ${esc(a.action)} · ${esc(a.verified_at || a.created_at)}
        ${Object.keys(a.field_changes || {}).length
        ? `<div class="chg">${Object.entries(a.field_changes).map(([k, v]) =>
          `${esc(k)}: ${esc(JSON.stringify(v))}`).join('；')}</div>` : ''}
      </div>`).join('')}</div>`
    : '';
  const opt = (list, current) => ['<option value="">（空）</option>']
    .concat(list.map((v) => `<option value="${v}" ${current === v ? 'selected' : ''}>${v}</option>`)).join('');
  return `<div class="rx ${r.verified ? 'done' : ''}" data-rx="${r.id}">
    <div class="rx-head">
      <div class="rx-eq">${esc(r.reaction)}</div>
      <span class="tag ${r.verified ? 'done' : 'todo'}">${r.verified ? '✓ 已复核' : '待复核'}</span>
      ${r.confidence != null ? `<span class="rx-conf">置信度 ${esc(r.confidence)}</span>` : ''}
    </div>
    ${source || excerpt ? `<div class="rx-src">${source}${excerpt}</div>` : ''}
    <div class="rx-grid">
      <div class="rx-field"><label>反应类型</label>
        <select class="select" data-f="reaction_type">${opt(REACTION_TYPES, r.reaction_type)}</select></div>
      <div class="rx-field"><label>速率类型</label>
        <select class="select" data-f="rate_type">${opt(RATE_TYPES, r.rate_type)}</select></div>
      <div class="rx-field"><label>速率系数（保留原文）</label>
        <input class="input" data-f="rate_value" value="${esc(r.rate_value || '')}" placeholder="照抄论文原文"></div>
      <div class="rx-field"><label>阈值 eV</label>
        <input class="input" data-f="threshold_ev" value="${r.threshold_ev != null ? esc(r.threshold_ev) : ''}" placeholder="留空表示缺失"></div>
      <div class="rx-field"><label>截面链接</label>
        <input class="input" data-f="cross_section_url" value="${esc(r.cross_section_url || '')}" placeholder="http(s)://"></div>
    </div>
    <div class="rx-hint">速率系数与阈值一律保留论文原文，不做单位换算、不填补缺失值。清空某字段即为如实记录「原文未给出」，该动作也会进审计日志。</div>
    <div class="rx-foot">
      <button class="btn-ghost sm" data-rx-act="audit">${state.chemAudit[r.id] ? '收起审计' : `审计日志 ${(r.audit_log || []).length}`}</button>
      <div class="spacer"></div>
      ${r.verified ? '<button class="btn-ghost sm" data-rx-act="unverify">撤回复核</button>' : ''}
      <button class="btn-ghost sm" data-rx-act="save">仅保存修正</button>
      <button class="btn-primary sm" data-rx-act="verify">${r.verified ? '重新确认' : '通过复核'}</button>
    </div>
    ${audits}
  </div>`;
}

function reviewerDisplayName(verifiedBy) {
  return verifiedBy === SELF_REVIEWER ? '本人' : (verifiedBy || '未署名');
}

function reactionFormPayload(card, verified) {
  const payload = { verified, verified_by: SELF_REVIEWER };
  $$('[data-f]', card).forEach((input) => {
    const field = input.dataset.f;
    const raw = input.value.trim();
    if (field === 'threshold_ev') {
      payload[field] = raw === '' ? null : Number(raw);
      return;
    }
    payload[field] = raw === '' ? null : raw;
  });
  return payload;
}

async function submitReaction(reactionId, card, verified) {
  const payload = reactionFormPayload(card, verified);
  if (payload.threshold_ev != null && Number.isNaN(payload.threshold_ev)) {
    toast('阈值 eV 必须是数字，或留空表示原文未给出', true);
    return;
  }
  try {
    state.chemSet = await api(`/reactions/${reactionId}/verify`, { method: 'PUT', body: payload });
    toast(verified ? '已通过复核并记入审计' : '已保存修正');
  } catch (e) {
    toast(`复核失败：${e.message}`, true);
    return;
  }
  const list = await apiOrNull(`/documents/${state.chemDocId}/reaction-sets?page_size=50`);
  state.chemSets = (list && list.items) || state.chemSets;
  if (state.docMeta[state.chemDocId]) state.docMeta[state.chemDocId].reactionSets = state.chemSets;
  renderChemistry();
}

async function exportReactionSet(format) {
  if (!state.chemSetId) return;
  try {
    const result = await api(`/reaction-sets/${state.chemSetId}/export?format=${format}`, { method: 'POST' });
    const gate = $('#chem-gate');
    gate.className = 'gate ok';
    gate.innerHTML = `✓ 已导出 ${EXPORT_LABELS[format]}：<span class="mono">${esc(result.output_path)}</span>
      · ${result.reaction_count} 条反应 · ${result.audit_entry_count} 条审计记录`;
    toast(`已导出 ${EXPORT_LABELS[format]}`);
  } catch (e) {
    const gate = $('#chem-gate');
    gate.className = 'gate bad';
    gate.innerHTML = e.status === 409
      ? `✗ 导出被人工复核闸门拦下（409 ${esc(e.code)}）：${esc(e.message)}。这是速率系数的强制闸门，必须逐条复核通过后才能导出。`
      : `✗ 导出失败（${e.status} ${esc(e.code)}）：${esc(e.message)}`;
    toast(`导出失败：${e.message}`, true);
  }
}

/* ── 事件绑定 ── */
function bindNav() {
  $('#nav').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-nav]');
    if (btn) setPage(btn.dataset.nav);
  });
}

function bindSearch() {
  $('#search-q').addEventListener('input', (e) => { state.query = e.target.value; });
  $('#search-q').addEventListener('keydown', (e) => { if (e.key === 'Enter') runSearch(); });
  $('#do-search').addEventListener('click', () => runSearch());
  $('#do-online-search').addEventListener('click', () => runOnlineSearch());
  $('#save-search-batch').addEventListener('click', () => saveOnlineSearchBatch());
  $('#discard-search-batch').addEventListener('click', () => discardOnlineSearchBatch());
  $('#search-mode').addEventListener('change', (e) => {
    state.queryMode = e.target.value;
    if (state.searched) runSearch();
  });
  $('#search-limit').addEventListener('change', (e) => {
    state.resultLimit = Number(e.target.value);
    if (state.searched) runSearch();
  });
  $('#search-sort').addEventListener('change', (e) => { state.sort = e.target.value; runSearch(); });
  $('#oa-chip').addEventListener('click', (e) => {
    state.oaOnly = !state.oaOnly;
    if (state.oaOnly) state.downloadOnly = false;
    e.currentTarget.classList.toggle('on', state.oaOnly);
    $('#download-chip').classList.toggle('on', state.downloadOnly);
    runSearch();
  });
  $('#download-chip').addEventListener('click', (e) => {
    state.downloadOnly = !state.downloadOnly;
    if (state.downloadOnly) state.oaOnly = false;
    e.currentTarget.classList.toggle('on', state.downloadOnly);
    $('#oa-chip').classList.toggle('on', state.oaOnly);
    runSearch();
  });
  $('#journal-chips').addEventListener('click', (e) => {
    const chip = e.target.closest('[data-journal]');
    if (!chip) return;
    const id = Number(chip.dataset.journal);
    state.activeJournal = state.activeJournal === id ? null : id;
    renderJournalChips();
    runSearch();
  });
  $('#category-chips').addEventListener('click', (e) => {
    const chip = e.target.closest('[data-category]');
    if (!chip) return;
    const slug = chip.dataset.category;
    state.activeCategory = state.activeCategory === slug ? null : slug;
    renderCategoryChips();
    runSearch();
  });

  const pop = $('#year-pop');
  $('#year-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    pop.hidden = !pop.hidden;
    $('#year-btn').classList.toggle('on', !pop.hidden);
  });
  document.addEventListener('click', (e) => {
    if (!pop.hidden && !pop.contains(e.target)) { pop.hidden = true; $('#year-btn').classList.remove('on'); }
  });
  $('#year-presets').innerHTML = YEAR_PRESETS.map((p, i) => `<button data-yp="${i}">${p.l}</button>`).join('');
  $('#year-presets').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-yp]');
    if (!btn) return;
    const preset = YEAR_PRESETS[Number(btn.dataset.yp)];
    state.yearFrom = preset.f;
    state.yearTo = preset.t;
    syncYearInputs();
    runSearch();
  });
  $('#year-from').addEventListener('input', (e) => {
    state.yearFrom = Math.min(Number(e.target.value), state.yearTo);
    syncYearInputs();
  });
  $('#year-to').addEventListener('input', (e) => {
    state.yearTo = Math.max(Number(e.target.value), state.yearFrom);
    syncYearInputs();
  });
  $('#year-from').addEventListener('change', () => runSearch());
  $('#year-to').addEventListener('change', () => runSearch());

  $('#search-results').addEventListener('click', (e) => {
    const card = e.target.closest('[data-paper]');
    const action = e.target.closest('[data-act]');
    if (!card || !action) return;
    const paper = state.results.find((p) => p.id === Number(card.dataset.paper));
    if (!paper) return;
    const act = action.dataset.act;
    if (act === 'expand') { state.expanded[paper.id] = !state.expanded[paper.id]; renderResults(); }
    else if (act === 'copy') copyText(paper.doi);
    else if (act === 'mark') toggleMark(paper);
    else if (act === 'zh') showAbstractTranslation(paper.id);
  });
  $('[data-page-prev]').addEventListener('click', () => { state.searchPage -= 1; runSearch(false); });
  $('[data-page-next]').addEventListener('click', () => { state.searchPage += 1; runSearch(false); });
}

function bindJournals() {
  $('#journal-create-form').addEventListener('submit', (event) => {
    event.preventDefault();
    saveJournalFromWorkbench();
  });
  $('#journal-form-reset').addEventListener('click', resetJournalForm);
  $('#journal-manager-list').addEventListener('click', (event) => {
    const edit = event.target.closest('[data-journal-edit]');
    if (edit) {
      editJournalFromWorkbench(Number(edit.dataset.journalEdit));
      return;
    }
    const remove = event.target.closest('[data-journal-delete]');
    if (remove) deleteJournalFromWorkbench(Number(remove.dataset.journalDelete));
  });
}

function syncYearInputs() {
  $('#year-from').value = state.yearFrom;
  $('#year-to').value = state.yearTo;
  $('#year-from-val').textContent = state.yearFrom;
  $('#year-to-val').textContent = state.yearTo;
  $('#year-label').textContent = `${state.yearFrom}–${state.yearTo}`;
  $$('#year-presets button').forEach((btn, i) => {
    const p = YEAR_PRESETS[i];
    btn.classList.toggle('on', state.yearFrom === p.f && state.yearTo === p.t);
  });
}

function bindDrawer() {
  const drawer = $('#drawer');
  const scrim = $('#scrim');
  const setOpen = (open) => { drawer.classList.toggle('open', open); scrim.hidden = !open; };
  $('#open-drawer').addEventListener('click', () => {
    setOpen(true);
    refreshMarkedDownloadInfo();
  });
  $('#close-drawer').addEventListener('click', () => setOpen(false));
  scrim.addEventListener('click', () => setOpen(false));
  $('#drawer-body').addEventListener('click', async (e) => {
    const downloadButton = e.target.closest('[data-download-marked]');
    if (downloadButton) {
      const index = Number(downloadButton.dataset.downloadMarked);
      const paper = currentMarkedPaper(persisted.marked[index]);
      const info = downloadAvailability(paper);
      if (!info.supported) {
        toast(`暂不支持下载：${info.reason}`, true);
        return;
      }
      if (state.markedDownloadState[paper.id] === 'downloading') return;
      state.markedDownloadState[paper.id] = 'downloading';
      renderMarked();
      try {
        await launchPaperDownload(paper);
        state.markedDownloadState[paper.id] = 'downloaded';
        toast('PDF 已下载');
      } catch (error) {
        state.markedDownloadState[paper.id] = 'failed';
        toast(`PDF 下载失败：${error.message}`, true);
      }
      renderMarked();
      return;
    }
    const btn = e.target.closest('[data-unmark]');
    if (!btn) return;
    persisted.marked.splice(Number(btn.dataset.unmark), 1);
    saveStore();
    renderMarked();
    renderResults();
    renderUploadPaperOptions();
  });
  $('#download-marked').addEventListener('click', downloadMarkedPapers);
  $('#export-txt').addEventListener('click', () => {
    if (!persisted.marked.length) { toast('清单为空', true); return; }
    download('doi-list.txt', persisted.marked.map((m) => m.doi || m.title).join('\n'), 'text/plain');
  });
  $('#export-csv').addEventListener('click', () => {
    if (!persisted.marked.length) { toast('清单为空', true); return; }
    const rows = ['DOI,Title,Journal,Year'].concat(persisted.marked.map((m) =>
      `"${m.doi}","${String(m.title).replace(/"/g, '""')}","${m.journal}",${m.year}`));
    download('doi-list.csv', rows.join('\n'), 'text/csv');
  });
  $('#clear-marked').addEventListener('click', () => {
    persisted.marked = [];
    saveStore();
    renderMarked();
    renderResults();
    renderUploadPaperOptions();
  });
}

function bindLibrary() {
  const zone = $('#dropzone');
  const input = $('#file-input');
  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', (e) => { uploadFiles(e.target.files); e.target.value = ''; });
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('over');
    uploadFiles(e.dataTransfer.files);
  });
  $('#upload-project').addEventListener('change', (e) => {
    persisted.uploadProject = e.target.value;
    saveStore();
  });
  $('#target-lang').addEventListener('change', (e) => {
    persisted.targetLang = e.target.value;
    saveStore();
  });
  $('#open-newproj').addEventListener('click', () => {
    $('#newproj-closed').hidden = true;
    $('#newproj-open').hidden = false;
    $('#newproj-name').focus();
  });
  $('#confirm-newproj').addEventListener('click', () => {
    const name = $('#newproj-name').value.trim() || `项目 ${persisted.projects.length + 1}`;
    const id = `j${Date.now()}`;
    persisted.projects.push({ id, name, docs: [] });
    persisted.uploadProject = id;
    state.selProject = id;
    saveStore();
    $('#newproj-name').value = '';
    $('#newproj-closed').hidden = false;
    $('#newproj-open').hidden = true;
    renderUploadProjectOptions();
    toast(`已创建项目「${name}」`);
  });
  $('#lib-grid').addEventListener('click', (e) => {
    const card = e.target.closest('[data-doc]');
    if (!card) return;
    const docId = Number(card.dataset.doc);
    const doc = state.documents.find((d) => d.id === docId);

    const tagOpt = e.target.closest('[data-tag]');
    if (tagOpt) { tagOpt.classList.toggle('on'); tagOpt.querySelector('.box').textContent = tagOpt.classList.contains('on') ? '✓' : ''; return; }

    const tagAct = e.target.closest('[data-tag-act]');
    if (tagAct && doc) {
      const editor = tagAct.closest('.tag-editor');
      if (tagAct.dataset.tagAct === 'cancel') { state.tagEditor = null; renderLibrary(); }
      else if (tagAct.dataset.tagAct === 'create') createCategory($('[data-new-tag]', editor).value);
      else if (tagAct.dataset.tagAct === 'auto') autoClassify(doc.paper_id);
      else if (tagAct.dataset.tagAct === 'save') {
        saveTags(doc.paper_id, $$('.tag-opt.on', editor).map((b) => Number(b.dataset.tag)));
      }
      return;
    }

    const btn = e.target.closest('[data-doc-act]');
    if (!btn || btn.disabled) return;
    const action = btn.dataset.docAct;
    if (action === 'open') openReader(docId);
    else if (action === 'tag') {
      state.tagEditor = state.tagEditor === doc.paper_id ? null : doc.paper_id;
      renderLibrary();
    } else if (action === 'chem') { setPage('chemistry'); loadChemDoc(docId); }
    else docAction(docId, action);
  });
}

function bindTags() {
  $('#tag-create-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const name = $('#tag-manage-name').value;
    const description = $('#tag-manage-description').value;
    const created = await createCategory(name, description);
    if (!created) return;
    $('#tag-manage-name').value = '';
    $('#tag-manage-description').value = '';
    $('#tag-manage-name').focus();
  });
  $('#tag-manager-list').addEventListener('click', (event) => {
    const edit = event.target.closest('[data-category-edit]');
    if (edit) {
      state.categoryEditingId = Number(edit.dataset.categoryEdit);
      renderTagManager();
      const input = $('[data-category-edit-name]');
      input.focus();
      input.select();
      return;
    }
    const cancel = event.target.closest('[data-category-edit-cancel]');
    if (cancel) {
      state.categoryEditingId = null;
      renderTagManager();
      return;
    }
    const remove = event.target.closest('[data-category-delete]');
    if (!remove || remove.disabled) return;
    deleteCategory(Number(remove.dataset.categoryDelete));
  });
  $('#tag-manager-list').addEventListener('submit', (event) => {
    const form = event.target.closest('[data-category-edit-form]');
    if (!form) return;
    event.preventDefault();
    updateCategory(Number(form.dataset.categoryEditForm), form);
  });
}

function bindGlossary() {
  $('#glossary-form').addEventListener('submit', (event) => {
    event.preventDefault();
    saveGlossaryTerm();
  });
  $('#glossary-cancel').addEventListener('click', resetGlossaryForm);
  $('#glossary-search').addEventListener('input', (event) => {
    state.glossaryQuery = event.target.value;
    renderGlossaryManager();
  });
  $('#glossary-manager-list').addEventListener('click', (event) => {
    const edit = event.target.closest('[data-glossary-edit]');
    if (edit) {
      editGlossaryTerm(edit.dataset.glossaryEdit);
      return;
    }
    const remove = event.target.closest('[data-glossary-delete]');
    if (remove) deleteGlossaryTerm(remove.dataset.glossaryDelete);
  });
}

function bindChemistry() {
  $('#chem-docs').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-chemdoc]');
    if (btn) loadChemDoc(Number(btn.dataset.chemdoc));
  });
  $('#chem-sets').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-chemset]');
    if (btn) loadChemSet(Number(btn.dataset.chemset));
  });
  $('#chem-exports').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-export]');
    if (btn) exportReactionSet(btn.dataset.export);
  });
  $('#chem-body').addEventListener('click', (e) => {
    const card = e.target.closest('[data-rx]');
    const btn = e.target.closest('[data-rx-act]');
    if (!card || !btn) return;
    const reactionId = Number(card.dataset.rx);
    const action = btn.dataset.rxAct;
    if (action === 'audit') {
      state.chemAudit[reactionId] = !state.chemAudit[reactionId];
      renderChemistry();
    } else if (action === 'verify') submitReaction(reactionId, card, true);
    else if (action === 'unverify') submitReaction(reactionId, card, false);
    else if (action === 'save') submitReaction(reactionId, card, !!card.classList.contains('done'));
  });
}

function hideSelectionPopover() {
  state.selection = null;
  $('#selection-popover').hidden = true;
}

function showSelectionPopover(pane) {
  const selection = window.getSelection();
  const popover = $('#selection-popover');
  if (!selection || selection.isCollapsed || !selection.rangeCount) {
    hideSelectionPopover();
    return;
  }
  const anchorInPane = pane.contains(selection.anchorNode);
  const focusInPane = pane.contains(selection.focusNode);
  const text = selection.toString().trim().replace(/\s+/g, ' ');
  if (!anchorInPane || !focusInPane || !text) {
    hideSelectionPopover();
    return;
  }
  const rect = selection.getRangeAt(0).getBoundingClientRect();
  if (!rect.width && !rect.height) {
    hideSelectionPopover();
    return;
  }
  state.selection = { text, lang: pane.id === 'pane-zh' ? 'zh' : 'en' };
  const addButton = $('[data-selection-action="glossary"]', popover);
  addButton.disabled = text.length > MAX_GLOSSARY_TERM_LENGTH;
  addButton.title = addButton.disabled
    ? `词或短语不能超过 ${MAX_GLOSSARY_TERM_LENGTH} 个字符`
    : '加入当前浏览器的术语表';
  popover.hidden = false;
  const gap = 10;
  const width = popover.offsetWidth;
  const height = popover.offsetHeight;
  const center = rect.left + rect.width / 2;
  const left = Math.max(10, Math.min(center - width / 2, window.innerWidth - width - 10));
  let top = rect.top - height - gap;
  const below = top < 52;
  if (below) top = rect.bottom + gap;
  popover.style.left = `${left}px`;
  popover.style.top = `${top}px`;
  popover.style.setProperty('--selection-pointer-x', `${Math.max(18, Math.min(center - left, width - 18))}px`);
  popover.classList.toggle('below', below);
}

function sendTextToChat(text, kind) {
  const normalized = String(text || '').trim().replace(/\s+/g, ' ');
  if (!normalized) return;
  hideSelectionPopover();
  state.chatScope = 'single';
  if (state.readerDocId && !state.chatDocs.includes(state.readerDocId)) state.chatDocs = [state.readerDocId];
  setPage('chat');
  const question = kind === 'term'
    ? `请解释术语“${normalized.slice(0, MAX_GLOSSARY_TERM_LENGTH)}”在本文语境中的含义。`
    : `请解释这段话：“${normalized.slice(0, 160)}”`;
  $('#chat-input').value = question;
  state.chatInput = question;
  renderChatSide();
  $('#chat-input').focus();
}

function bindReader() {
  const applyReaderFilters = () => {
    state.readerSearch = '';
    $('#reader-search').value = '';
    const candidates = readerCandidates();
    const currentVisible = candidates.some((doc) => doc.id === state.readerDocId);
    if (currentVisible) {
      state.readerDropOpen = true;
      renderReaderBar();
      return;
    }
    const first = candidates.find((doc) => doc.parse_status === 'parsed');
    if (first) {
      openReader(first.id);
      return;
    }
    state.readerDocId = null;
    state.readerParas = [];
    state.readerDropOpen = true;
    renderReaderBar();
  };
  $('#back-to-lib').addEventListener('click', () => setPage('library'));
  $('#reader-retranslate').addEventListener('click', retranslateReader);
  $('#reader-project').addEventListener('change', (e) => {
    state.readerProject = e.target.value;
    applyReaderFilters();
  });
  $('#reader-category').addEventListener('change', (e) => {
    state.readerCategory = e.target.value;
    applyReaderFilters();
  });
  $('#reader-search').addEventListener('input', (e) => {
    state.readerSearch = e.target.value;
    state.readerDropOpen = true;
    renderReaderDrop();
  });
  $('#reader-search').addEventListener('focus', () => { state.readerDropOpen = true; renderReaderDrop(); });
  $('#reader-search').addEventListener('blur', () => {
    setTimeout(() => { state.readerDropOpen = false; renderReaderDrop(); }, 180);
  });
  $('#reader-drop').addEventListener('mousedown', (e) => {
    const btn = e.target.closest('[data-pick]');
    if (!btn || btn.disabled) return;
    state.readerSearch = '';
    state.readerDropOpen = false;
    $('#reader-search').value = '';
    openReader(Number(btn.dataset.pick));
  });
  $('#reader-modes').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-mode]');
    if (!btn) return;
    state.readerMode = btn.dataset.mode;
    renderReaderBar();
  });
  $('#reader-qa-language').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-reader-lang]');
    if (!btn) return;
    state.readerQaLang = btn.dataset.readerLang;
    renderReaderBar();
  });
  const readerChatInput = $('#reader-chat-input');
  readerChatInput.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    sendReaderQa(readerChatInput.value);
  });
  $('#reader-chat-send').addEventListener('click', () => sendReaderQa(readerChatInput.value));
  $('#reader-chat-log').addEventListener('click', (event) => {
    const suggestion = event.target.closest('[data-reader-question]');
    if (suggestion) {
      readerChatInput.value = suggestion.dataset.readerQuestion;
      readerChatInput.focus();
      return;
    }
    const citation = event.target.closest('[data-reader-cite]');
    if (!citation) return;
    const [messageIndex, sourceIndex] = citation.dataset.readerCite.split(':').map(Number);
    const source = ((currentReaderQaThread()[messageIndex] || {}).sources || [])[sourceIndex];
    if (source) jumpToSource(source.document_id, source.section_seq);
  });
  $('#font-dec').addEventListener('click', () => {
    persisted.fontSize = Math.max(12, persisted.fontSize - 1);
    saveStore();
    $('#font-label').textContent = `${persisted.fontSize}px`;
    renderParas();
  });
  $('#font-inc').addEventListener('click', () => {
    persisted.fontSize = Math.min(20, persisted.fontSize + 1);
    saveStore();
    $('#font-label').textContent = `${persisted.fontSize}px`;
    renderParas();
  });
  $('#gloss-toggle').addEventListener('click', () => {
    persisted.glossary = !persisted.glossary;
    saveStore();
    $('#gloss-toggle').classList.toggle('on', persisted.glossary);
    renderGlossbar();
    renderParas();
  });
  $('#glossbar').addEventListener('click', (event) => {
    if (event.target.closest('[data-open-glossary]')) {
      setPage('glossary');
      return;
    }
    const button = event.target.closest('[data-glossary-send]');
    const term = button && glossaryTermById(button.dataset.glossarySend);
    if (term) sendTextToChat(term.en || term.zh, 'term');
  });
  const paneEn = $('#pane-en');
  const paneZh = $('#pane-zh');
  paneEn.addEventListener('scroll', () => { syncScroll(paneEn, paneZh); hideSelectionPopover(); });
  paneZh.addEventListener('scroll', () => { syncScroll(paneZh, paneEn); hideSelectionPopover(); });
  [paneEn, paneZh].forEach((pane) => {
    pane.addEventListener('click', (e) => {
      const glossaryTerm = e.target.closest('[data-glossary-send]');
      if (glossaryTerm) {
        const term = glossaryTermById(glossaryTerm.dataset.glossarySend);
        if (term) sendTextToChat(term.en || term.zh, 'term');
        return;
      }
      if ((window.getSelection() || '').toString().trim()) return;
      const para = e.target.closest('[data-para]');
      if (!para) return;
      const seq = Number(para.dataset.para);
      state.activePara = state.activePara === seq ? null : seq;
      $$('.para').forEach((node) => {
        node.classList.toggle('on', Number(node.dataset.para) === state.activePara);
      });
    });
    pane.addEventListener('keydown', (event) => {
      const glossaryTerm = event.target.closest('[data-glossary-send]');
      if (!glossaryTerm || !['Enter', ' '].includes(event.key)) return;
      event.preventDefault();
      const term = glossaryTermById(glossaryTerm.dataset.glossarySend);
      if (term) sendTextToChat(term.en || term.zh, 'term');
    });
    pane.addEventListener('mouseup', () => {
      requestAnimationFrame(() => showSelectionPopover(pane));
    });
  });
  const selectionPopover = $('#selection-popover');
  selectionPopover.addEventListener('pointerdown', (event) => {
    event.preventDefault();
  });
  selectionPopover.addEventListener('click', (event) => {
    const action = event.target.closest('[data-selection-action]');
    if (!action || action.disabled) return;
    if (action.dataset.selectionAction === 'glossary') {
      addSelectionToGlossary();
      return;
    }
    if (action.dataset.selectionAction === 'chat' && state.selection) {
      sendTextToChat(state.selection.text, 'selection');
    }
  });
  document.addEventListener('mousedown', (event) => {
    if (!selectionPopover.hidden && !selectionPopover.contains(event.target)
      && !paneEn.contains(event.target) && !paneZh.contains(event.target)) {
      hideSelectionPopover();
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !selectionPopover.hidden) {
      hideSelectionPopover();
      const selection = window.getSelection();
      if (selection) selection.removeAllRanges();
    }
  });
  window.addEventListener('resize', () => {
    if (!selectionPopover.hidden) hideSelectionPopover();
  });
}

function bindChat() {
  $('#scope-opts').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-scope]');
    if (!btn) return;
    state.chatScope = btn.dataset.scope;
    renderChatSide();
  });
  $('#proj-rows').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-proj]');
    if (!btn) return;
    state.selProject = btn.dataset.proj;
    renderChatSide();
  });
  $('#chat-category').addEventListener('change', (e) => {
    state.chatCategory = e.target.value;
    state.chatDocs = state.chatDocs.filter((id) => indexedDocs().some((doc) => doc.id === id));
    state.docSearch = '';
    $('#doc-search').value = '';
    renderChatSide();
  });
  $('#doc-search').addEventListener('input', (e) => { state.docSearch = e.target.value; renderChatSide(); });
  $('#doc-opts').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-chatdoc]');
    if (!btn) return;
    state.chatDocs = [Number(btn.dataset.chatdoc)];
    renderChatSide();
  });
  $('#presets').addEventListener('click', (e) => {
    const edit = e.target.closest('[data-preset-edit]');
    if (edit) {
      openPresetEditor(presetById(edit.dataset.presetEdit));
      return;
    }
    const remove = e.target.closest('[data-preset-delete]');
    if (remove) {
      deletePreset(remove.dataset.presetDelete);
      return;
    }
    const btn = e.target.closest('[data-preset-id]');
    if (!btn) return;
    const preset = presetById(btn.dataset.presetId);
    if (!preset) return;
    $('#chat-input').value = preset.q;
    state.chatInput = preset.q;
    $('#chat-input').focus();
  });
  $('#new-preset').addEventListener('click', () => openPresetEditor());
  $('#cancel-preset').addEventListener('click', () => {
    state.presetEditor = null;
    renderPresetEditor();
  });
  $('#preset-editor').addEventListener('submit', (e) => {
    e.preventDefault();
    savePresetEditor();
  });
  [
    ['preset-cmd', 'cmd'],
    ['preset-desc', 'desc'],
    ['preset-question', 'q'],
  ].forEach(([elementId, field]) => {
    $(`#${elementId}`).addEventListener('input', (e) => {
      if (state.presetEditor) state.presetEditor[field] = e.target.value;
    });
  });
  const input = $('#chat-input');
  input.addEventListener('input', (e) => {
    state.chatInput = e.target.value;
    const v = e.target.value;
    const matches = allPresets().filter((p) => p.cmd.indexOf(v.trim()) === 0);
    state.slashOpen = v.startsWith('/') && !v.includes(' ') && matches.length > 0;
    const pop = $('#slash-pop');
    pop.hidden = !state.slashOpen;
    if (state.slashOpen) {
      pop.innerHTML = matches.map((p) => `<button data-slash="${esc(p.cmd)}">
        <span class="cmd">${esc(p.cmd)}</span><span class="desc">${esc(p.desc)}</span></button>`).join('');
    }
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); sendChat(input.value); }
  });
  $('#slash-pop').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-slash]');
    if (!btn) return;
    const preset = allPresets().find((p) => p.cmd === btn.dataset.slash);
    if (!preset) return;
    input.value = preset.q;
    state.chatInput = preset.q;
    state.slashOpen = false;
    $('#slash-pop').hidden = true;
    input.focus();
  });
  $('#chat-send').addEventListener('click', () => sendChat(input.value));
  $('#chat-log').addEventListener('click', (e) => {
    const cite = e.target.closest('[data-cite]');
    if (cite) {
      const [mi, si] = cite.dataset.cite.split(':').map(Number);
      const source = ((state.messages[mi] || {}).sources || [])[si];
      if (source) jumpToSource(source.document_id, source.section_seq);
      return;
    }
    const copy = e.target.closest('[data-rel-copy]');
    if (copy && copy.dataset.relCopy) copyText(copy.dataset.relCopy);
  });
}

/* ── 启动 ── */
async function boot() {
  bindNav();
  bindSearch();
  bindJournals();
  bindDrawer();
  bindLibrary();
  bindTags();
  bindGlossary();
  bindReader();
  bindChat();
  bindChemistry();
  syncYearInputs();
  renderMarked();
  renderNav();
  setPage('search');
  state.status = await apiOrNull('/system/status');
  renderSysbox();
  try {
    await migrateLegacyPromptPresets();
  } catch (error) {
    toast(`旧预设迁移失败：${error.message}`, true);
  }
  await Promise.all([loadJournals(), loadCategories(), loadPresets()]);
  await runSearch();
  await ensureLibrary();
}

document.addEventListener('DOMContentLoaded', boot);
