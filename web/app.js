/* 等离子体文献工作台 — 前端工作台
 * 所有数据来自 /api/v1 真实接口；仅「待下载清单」「项目分组」「阅读偏好」是本地视图状态，存 localStorage。
 */
'use strict';

const API = '/api/v1';
const LS_KEY = 'plasma-workbench';

/* ── 术语表（中英对照，用于阅读页高亮） ── */
const GLOSSARY = [
  { en: 'capacitively coupled', zh: '容性耦合' },
  { en: 'electron energy distribution function', zh: '电子能量分布函数' },
  { en: 'EEDF', zh: '电子能量分布函数' },
  { en: 'particle-in-cell', zh: '粒子网格法' },
  { en: 'Monte Carlo collisions', zh: '蒙特卡罗碰撞' },
  { en: 'secondary electron emission', zh: '二次电子发射' },
  { en: 'ohmic heating', zh: '欧姆加热' },
  { en: 'cross section', zh: '截面' },
  { en: 'dissociation', zh: '解离' },
  { en: 'ionization', zh: '电离' },
  { en: 'attachment', zh: '吸附' },
  { en: 'radical', zh: '自由基' },
  { en: 'ion flux', zh: '离子通量' },
  { en: 'sheath', zh: '鞘层' },
  { en: 'self-bias', zh: '自偏压' },
  { en: 'rate coefficient', zh: '速率系数' },
];
const ZH_TERMS = ['电子能量分布函数', '二次电子发射', '蒙特卡罗碰撞', '容性耦合', '粒子网格',
  '欧姆加热', '离子通量', '速率系数', '自偏压', '自由基', '鞘层', '解离', '电离', '截面', 'EEDF'];

const PRESETS = [
  { cmd: '/总结', desc: '总结当前范围内文献的核心结论', q: '总结当前范围内文献的核心结论、方法与主要数据。' },
  { cmd: '/术语', desc: '提取并解释文中的专业术语', q: '提取当前范围文献中的关键专业术语，并逐条解释其含义。' },
  { cmd: '/相关工作', desc: '梳理相关工作与研究脉络', q: '梳理当前范围文献涉及的相关工作与研究脉络。' },
  { cmd: '/提问我', desc: '就所选文献向我提问，考察理解', q: '就当前范围的文献内容，向我提出两个考察理解的问题。' },
];

const NAV = [
  { key: 'search', label: '文献检索', sub: 'SEARCH' },
  { key: 'library', label: '文献库', sub: 'LIBRARY' },
  { key: 'reader', label: '双语阅读', sub: 'READER' },
  { key: 'chat', label: 'AI 问答', sub: 'Q&A' },
  { key: 'chemistry', label: '化学库复核', sub: 'CHEMISTRY' },
];

const REACTION_TYPES = ['elastic', 'excitation', 'ionization', 'attachment', 'recombination'];
const RATE_TYPES = ['cross_section', 'arrhenius', 'constant'];
const EXPORT_LABELS = { json: 'JSON', txt: 'TXT', bolsig: 'BOLSIG+' };

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
    uploadProject: 'none', targetLang: 'zh', reviewer: '',
  },
  readStore()
);

function readStore() {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || '{}'); } catch (e) { return {}; }
}
function saveStore() {
  try { localStorage.setItem(LS_KEY, JSON.stringify(persisted)); } catch (e) { /* 隐私模式下忽略 */ }
}

/* ── 运行时状态 ── */
const state = {
  page: 'search',
  status: null,
  journals: [],
  categories: [],
  activeJournal: null,
  activeCategory: null,
  tagEditor: null,
  oaOnly: false,
  query: '',
  yearFrom: YEAR_MIN,
  yearTo: YEAR_MAX,
  sort: 'date_desc',
  searchPage: 1,
  searchTotal: 0,
  results: [],
  searched: false,
  searchMode: 'local',
  onlineSyncing: false,
  syncSummary: null,
  expanded: {},
  absZh: {},
  documents: [],
  docMeta: {},
  paperCache: {},
  libLoaded: false,
  readerDocId: null,
  readerProject: 'all',
  readerMode: 'both',
  readerParas: [],
  readerLoading: false,
  activePara: null,
  readerSearch: '',
  readerDropOpen: false,
  chatScope: 'single',
  chatDocs: [],
  selProject: null,
  docSearch: '',
  messages: [],
  typing: false,
  chatInput: '',
  slashOpen: false,
  selection: null,
  drawerOpen: false,
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

function authorsText(authors) {
  if (!Array.isArray(authors) || !authors.length) return '作者信息缺失';
  const names = authors
    .map((a) => (typeof a === 'string' ? a : (a && (a.name || a.display_name || a.full_name)) || ''))
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
  a.href = URL.createObjectURL(new Blob([content], { type }));
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/* ── 导航与系统状态 ── */
function renderNav() {
  const badges = { library: state.documents.length };
  $('#nav').innerHTML = NAV.map((n) => `
    <button data-nav="${n.key}" class="${state.page === n.key ? 'on' : ''}">
      <span class="lbl">${n.label}</span>
      ${badges[n.key] ? `<span class="badge">${badges[n.key]}</span>` : ''}
      <span class="sub">${n.sub}</span>
    </button>`).join('');
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
  $('#sel-btn').hidden = true;
  $$('.screen').forEach((node) => { node.hidden = node.dataset.screen !== page; });
  renderNav();
  if (page === 'library') loadLibrary();
  if (page === 'reader') { ensureLibrary().then(renderReaderBar); }
  if (page === 'chat') { ensureLibrary().then(renderChatSide); }
  if (page === 'chemistry') { ensureLibrary().then(openChemistry); }
}

/* ── 文献检索 ── */
async function loadJournals() {
  const data = await apiOrNull('/journals?active=1&page_size=100');
  state.journals = (data && data.items) || [];
  $('#search-source').textContent =
    `默认检索本地库 · 在线同步 OpenAlex → Crossref 回退 · 期刊白名单 ${state.journals.length} 本`;
  renderJournalChips();
  renderUploadPaperOptions();
}

function renderJournalChips() {
  $('#journal-chips').innerHTML = state.journals.map((j) => {
    const zone = j.sci_zone ? `<span class="zone ${zoneClass(j.sci_zone)}">${esc(j.sci_zone)}</span>` : '';
    const imp = j.impact_factor != null ? `<span class="imp">IF ${esc(j.impact_factor)}</span>` : '';
    return `<button class="chip ${state.activeJournal === j.id ? 'on' : ''}" data-journal="${j.id}">
      ${esc(j.name)}${zone}${imp}</button>`;
  }).join('');
}

/* ── 标签（复用 categories / paper_categories） ── */
async function loadCategories() {
  const data = await apiOrNull('/categories?page_size=100');
  state.categories = (data && data.items) || [];
  renderCategoryChips();
}

function renderCategoryChips() {
  $('#category-chips').innerHTML = state.categories.length
    ? state.categories.map((c) => `<button class="chip ${state.activeCategory === c.slug ? 'on' : ''}"
        data-category="${esc(c.slug)}" title="${esc(c.description || '')}">${esc(c.name)}</button>`).join('')
    : '<span class="chips-label">（分类表为空）</span>';
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

async function createCategory(name, paperId) {
  const label = (name || '').trim();
  if (!label) { toast('标签名称不能为空', true); return; }
  const slug = label.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9_-]/g, '') || `tag-${Date.now()}`;
  try {
    await api('/categories', { method: 'POST', body: { name: label, slug } });
    toast(`已新建标签「${label}」`);
  } catch (e) {
    toast(`新建标签失败：${e.message}`, true);
    return;
  }
  await loadCategories();
  if (state.tagEditor === paperId) renderLibrary();
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
  if (state.query.trim()) params.set('q', state.query.trim());
  if (state.activeJournal != null) params.set('journal_id', state.activeJournal);
  if (state.activeCategory) params.set('category', state.activeCategory);
  params.set('year_from', state.yearFrom);
  params.set('year_to', state.yearTo);
  if (state.oaOnly) params.set('oa_only', 'true');
  params.set('sort', state.query.trim() ? state.sort : 'date_desc');
  params.set('page', state.searchPage);
  params.set('page_size', '20');
  return params.toString();
}

async function runSearch(resetPage, options) {
  options = options || {};
  if (resetPage !== false) state.searchPage = 1;
  if (!options.keepSyncSummary) {
    state.searchMode = 'local';
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
  const sync = state.searchMode === 'online' && state.syncSummary
    ? `在线同步完成：${state.syncSummary.succeeded}/${state.syncSummary.total} 个期刊成功`
      + ` · 新增 ${state.syncSummary.newPapers} 篇 · `
    : '本地文献库 · ';
  meta.textContent = `${sync}共 ${state.searchTotal} 条结果 · 已标记 ${persisted.marked.length} 条待下载`
    + (state.activeJournal != null ? ' · 已按白名单期刊过滤' : '');
  const wrap = $('#search-results');
  if (!state.results.length) {
    wrap.innerHTML = `<div class="empty-state">${state.searched
      ? '没有命中文献<br>可放宽年份区间、清除期刊筛选，或点击「在线同步并检索」更新元数据'
      : '输入关键词后检索本地库，或从学术 API 在线同步'}</div>`;
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
  button.textContent = label || (busy ? '在线同步中…' : '在线同步并检索');
}

function waitForOnlineSearchPoll(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function waitForCrawlJobs(jobIds) {
  const deadline = Date.now() + 180000;
  while (Date.now() < deadline) {
    const jobs = await Promise.all(jobIds.map((jobId) => api(`/crawl/jobs/${jobId}`)));
    const finished = jobs.filter((job) => ['success', 'failed'].includes(job.status));
    const newPapers = jobs.reduce((total, job) => total + Number(job.papers_new || 0), 0);
    $('#search-meta').textContent =
      `在线同步中：${finished.length}/${jobs.length} 个期刊完成 · 已新增 ${newPapers} 篇`;
    setOnlineSearchBusy(true, `同步中 ${finished.length}/${jobs.length}`);
    if (finished.length === jobs.length) return jobs;
    await waitForOnlineSearchPoll(1000);
  }
  throw new Error('在线同步等待超过 3 分钟，请稍后在本地库中重试检索');
}

async function runOnlineSearch() {
  if (state.onlineSyncing) return;
  const query = state.query.trim();
  if (!query) {
    toast('请先输入在线检索关键词', true);
    $('#search-q').focus();
    return;
  }
  setOnlineSearchBusy(true);
  $('#search-meta').textContent = '正在创建 OpenAlex / Crossref 在线同步任务…';
  const body = Object.assign({ period: 'manual', search_query: query }, onlineDateRange());
  if (state.activeJournal != null) body.journal_ids = [state.activeJournal];
  try {
    const accepted = await api('/crawl/run', { method: 'POST', body });
    const jobIds = (accepted.jobs || []).map((job) => job.job_id);
    if (!jobIds.length) throw new Error('在线同步没有创建任何期刊任务');
    const jobs = await waitForCrawlJobs(jobIds);
    const succeeded = jobs.filter((job) => job.status === 'success');
    const failed = jobs.filter((job) => job.status === 'failed');
    state.searchMode = 'online';
    state.syncSummary = {
      total: jobs.length,
      succeeded: succeeded.length,
      failed: failed.length,
      newPapers: jobs.reduce((total, job) => total + Number(job.papers_new || 0), 0),
    };
    await runSearch(true, { keepSyncSummary: true });
    if (failed.length) toast(`${failed.length} 个期刊同步失败，已展示其余结果`, true);
    else toast('在线同步完成，已刷新本地结果');
  } catch (e) {
    $('#search-meta').textContent = `在线同步失败：${e.message} · 本地结果未改变`;
    toast(`在线同步失败：${e.message}`, true);
  } finally {
    setOnlineSearchBusy(false);
  }
}

function paperCard(p) {
  const expanded = !!state.expanded[p.id];
  const marked = persisted.marked.some((m) => m.id === p.id);
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
      <button class="btn-ghost sm mark-btn ${marked ? 'on' : ''}" data-act="mark">${marked ? '✓ 已在清单' : '加入待下载'}</button>
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
function toggleMark(paper) {
  const index = persisted.marked.findIndex((m) => m.id === paper.id);
  if (index >= 0) persisted.marked.splice(index, 1);
  else {
    persisted.marked.push({
      id: paper.id, doi: paper.doi || '', title: paper.title,
      journal: paper.journal_name || '', year: paper.published_year || '',
    });
  }
  saveStore();
  renderMarked();
  renderResults();
}

function renderMarked() {
  $$('[data-marked-count]').forEach((node) => { node.textContent = persisted.marked.length; });
  const body = $('#drawer-body');
  if (!persisted.marked.length) {
    body.innerHTML = '<div class="drawer-empty">清单为空<br>在检索结果中点击「加入待下载」收集 DOI</div>';
    return;
  }
  body.innerHTML = persisted.marked.map((m, i) => `<div class="mk">
    <div class="t">${esc(m.title)}</div>
    <div class="r">
      <span class="d">${esc(m.doi || '无 DOI')}</span>
      <span class="m">${esc([m.journal, m.year].filter(Boolean).join(' · '))}</span>
      <div class="spacer"></div>
      <button class="rm" data-unmark="${i}">移除</button>
    </div></div>`).join('');
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
  $('#lib-sub').textContent =
    `共 ${state.documents.length} 篇 · 上传 PDF 后按 file_hash 去重，可依次执行解析 / 翻译 / 索引`;
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
    try {
      const doc = await api('/documents', { method: 'POST', body: form });
      assignToProject(doc.id);
      toast(`${file.name} 已上传，正在解析…`);
      api(`/documents/${doc.id}/parse`, { method: 'POST' }).catch(() => {});
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

/* ── 双语阅读 ── */
function readerCandidates() {
  const project = persisted.projects.find((p) => p.id === state.readerProject);
  const pool = project
    ? state.documents.filter((d) => project.docs.includes(d.id))
    : state.documents;
  const q = state.readerSearch.trim().toLowerCase();
  if (!q) return pool;
  return pool.filter((d) => {
    const paper = d.paper || {};
    return `${docTitle(d)} ${paper.doi || ''} ${paper.journal_name || ''}`.toLowerCase().includes(q);
  });
}

function renderReaderBar() {
  const select = $('#reader-project');
  select.innerHTML = ['<option value="all">全部文献</option>'].concat(
    persisted.projects.map((p) => `<option value="${esc(p.id)}">${esc(p.name)}</option>`)
  ).join('');
  select.value = state.readerProject;

  $('#reader-modes').innerHTML = [
    { k: 'both', l: '对照' }, { k: 'zh', l: '仅中文' }, { k: 'en', l: '仅英文' },
  ].map((m) => `<button data-mode="${m.k}" class="${state.readerMode === m.k ? 'on' : ''}">${m.l}</button>`).join('');

  const current = state.documents.find((d) => d.id === state.readerDocId);
  $('#reader-search').placeholder = current ? docTitle(current).slice(0, 64) : '搜索文献…';
  $('#font-label').textContent = `${persisted.fontSize}px`;
  $('#gloss-toggle').classList.toggle('on', persisted.glossary);
  $('#pane-en').hidden = state.readerMode === 'zh';
  $('#pane-zh').hidden = state.readerMode === 'en';
  renderReaderDrop();
  renderGlossbar();
  if (!state.readerDocId) {
    const first = state.documents.find((d) => d.parse_status === 'parsed');
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
    + GLOSSARY.slice(0, 8).map((g) => `<span class="g">${esc(g.en)} <span>${esc(g.zh)}</span></span>`).join('')
    + '<span class="hint">选中任意文字可发送到问答</span>';
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
  renderReaderBar();
}

function highlight(text, lang) {
  if (!persisted.glossary || !text) return esc(text);
  const terms = lang === 'en' ? GLOSSARY.map((g) => g.en) : ZH_TERMS;
  const sorted = terms.slice().sort((a, b) => b.length - a.length)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const re = new RegExp(`(${sorted.join('|')})`, 'gi');
  return esc(text).split(re).map((part, i) => {
    if (i % 2 === 0) return part;
    const g = lang === 'en'
      ? GLOSSARY.find((x) => x.en.toLowerCase() === part.toLowerCase())
      : GLOSSARY.find((x) => x.zh === part);
    return `<span class="term" title="${g ? esc(lang === 'en' ? g.zh : g.en) : ''}">${part}</span>`;
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
  if (state.chatScope === 'all') return [];
  if (state.chatScope === 'project') {
    const project = persisted.projects.find((p) => p.id === state.selProject);
    return project ? project.docs.slice() : [];
  }
  return state.chatDocs.slice();
}

function indexedDocs() {
  return state.documents.filter((d) => d.index_status === 'indexed');
}

function totalChunks() {
  return state.documents.reduce((sum, d) => sum + ((state.docMeta[d.id] || {}).chunkTotal || 0), 0);
}

function renderChatSide() {
  const chunks = totalChunks();
  const scopes = [
    { k: 'single', l: '单篇文献', h: '精读' },
    { k: 'project', l: '项目问答', h: '跨文献' },
    { k: 'all', l: '全库 RAG', h: `${chunks} 段` },
  ];
  $('#scope-opts').innerHTML = scopes.map((s) => `
    <button class="scope-btn ${state.chatScope === s.k ? 'on' : ''}" data-scope="${s.k}">
      <span class="dot"></span>${s.l}<span class="hint">${s.h}</span></button>`).join('');

  $('#proj-picker').hidden = state.chatScope !== 'project';
  $('#all-note').hidden = state.chatScope !== 'all';
  $('#doc-picker').hidden = state.chatScope !== 'single';
  $('#all-doc-count').textContent = indexedDocs().length;
  $('#all-chunk-count').textContent = chunks;

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
    .filter(Boolean)
    .map((d) => `<div class="proj-doc">${esc(docTitle(d))}</div>`).join('');

  const q = state.docSearch.trim().toLowerCase();
  const docs = indexedDocs().filter((d) => !q
    || `${docTitle(d)} ${(d.paper && d.paper.doi) || ''}`.toLowerCase().includes(q));
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

  $('#presets').innerHTML = PRESETS.map((p, i) => `
    <button class="preset-btn" data-preset="${i}">
      <div class="cmd">${esc(p.cmd)}</div><div class="desc">${esc(p.desc)}</div></button>`).join('');

  const ids = chatDocumentIds();
  $('#scope-summary').textContent = state.chatScope === 'all'
    ? `范围：全库 RAG · ${indexedDocs().length} 篇 · ${chunks} 个切块向量`
    : state.chatScope === 'project'
      ? `范围：项目「${project ? project.name : '未选择'}」· ${ids.length} 篇`
      : ids.length
        ? `范围：单篇精读 · ${docTitle(state.documents.find((d) => d.id === ids[0]) || {})}`
        : '范围：单篇精读 · 未选择文献';
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
  if (state.chatScope !== 'all' && !ids.length) {
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
  const data = await apiOrNull(`/papers?q=${encodeURIComponent(words.slice(0, 4).join(' '))}&sort=relevance&page_size=2`);
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
  $('#reviewer').value = persisted.reviewer;
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
        <span class="who">${esc(a.verified_by || '未署名')}</span> · ${esc(a.action)} · ${esc(a.verified_at || a.created_at)}
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

function reactionFormPayload(card, verified) {
  const payload = { verified, verified_by: persisted.reviewer.trim() };
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
  if (!persisted.reviewer.trim()) {
    toast('请先在左侧填写复核人——每次复核都要有可追溯的责任人', true);
    $('#reviewer').focus();
    return;
  }
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
  $('#search-sort').addEventListener('change', (e) => { state.sort = e.target.value; runSearch(); });
  $('#oa-chip').addEventListener('click', (e) => {
    state.oaOnly = !state.oaOnly;
    e.currentTarget.classList.toggle('on', state.oaOnly);
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
  $('#open-drawer').addEventListener('click', () => setOpen(true));
  $('#close-drawer').addEventListener('click', () => setOpen(false));
  scrim.addEventListener('click', () => setOpen(false));
  $('#drawer-body').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-unmark]');
    if (!btn) return;
    persisted.marked.splice(Number(btn.dataset.unmark), 1);
    saveStore();
    renderMarked();
    renderResults();
    renderUploadPaperOptions();
  });
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
      else if (tagAct.dataset.tagAct === 'create') createCategory($('[data-new-tag]', editor).value, doc.paper_id);
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

function bindChemistry() {
  $('#reviewer').addEventListener('input', (e) => {
    persisted.reviewer = e.target.value;
    saveStore();
  });
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

function bindReader() {
  $('#back-to-lib').addEventListener('click', () => setPage('library'));
  $('#reader-project').addEventListener('change', (e) => {
    state.readerProject = e.target.value;
    state.readerSearch = '';
    renderReaderDrop();
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
  const paneEn = $('#pane-en');
  const paneZh = $('#pane-zh');
  paneEn.addEventListener('scroll', () => syncScroll(paneEn, paneZh));
  paneZh.addEventListener('scroll', () => syncScroll(paneZh, paneEn));
  [paneEn, paneZh].forEach((pane) => {
    pane.addEventListener('click', (e) => {
      const para = e.target.closest('[data-para]');
      if (!para) return;
      const seq = Number(para.dataset.para);
      state.activePara = state.activePara === seq ? null : seq;
      renderParas();
    });
    pane.addEventListener('mouseup', (e) => {
      const text = (window.getSelection() || '').toString().trim();
      const btn = $('#sel-btn');
      if (text.length > 3) {
        state.selection = text;
        btn.style.left = `${Math.min(e.clientX, window.innerWidth - 170)}px`;
        btn.style.top = `${Math.max(56, e.clientY - 48)}px`;
        btn.hidden = false;
      } else {
        state.selection = null;
        btn.hidden = true;
      }
    });
  });
  $('#sel-btn').addEventListener('click', () => {
    const text = state.selection || '';
    $('#sel-btn').hidden = true;
    state.selection = null;
    state.chatScope = 'single';
    if (state.readerDocId && !state.chatDocs.includes(state.readerDocId)) state.chatDocs = [state.readerDocId];
    setPage('chat');
    const question = `请解释这段话：“${text.slice(0, 160)}”`;
    $('#chat-input').value = question;
    state.chatInput = question;
    renderChatSide();
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
  $('#doc-search').addEventListener('input', (e) => { state.docSearch = e.target.value; renderChatSide(); });
  $('#doc-opts').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-chatdoc]');
    if (!btn) return;
    state.chatDocs = [Number(btn.dataset.chatdoc)];
    renderChatSide();
  });
  $('#presets').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-preset]');
    if (!btn) return;
    const preset = PRESETS[Number(btn.dataset.preset)];
    $('#chat-input').value = preset.q;
    state.chatInput = preset.q;
    $('#chat-input').focus();
  });
  const input = $('#chat-input');
  input.addEventListener('input', (e) => {
    state.chatInput = e.target.value;
    const v = e.target.value;
    const matches = PRESETS.filter((p) => p.cmd.indexOf(v.trim()) === 0);
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
    const preset = PRESETS.find((p) => p.cmd === btn.dataset.slash);
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
  bindDrawer();
  bindLibrary();
  bindReader();
  bindChat();
  bindChemistry();
  syncYearInputs();
  renderMarked();
  renderNav();
  setPage('search');
  state.status = await apiOrNull('/system/status');
  renderSysbox();
  await Promise.all([loadJournals(), loadCategories()]);
  await runSearch();
  await ensureLibrary();
}

document.addEventListener('DOMContentLoaded', boot);
