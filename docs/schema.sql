-- =============================================================
-- 等离子体文献系统 · SQLite 建库脚本
-- 用法：sqlite3 plasma.db < schema.sql
-- 约定：日期统一用 ISO8601 文本（'2026-06-23' 或 'YYYY-MM-DD HH:MM:SS'）
--       多值字段（authors / keywords / reactants 等）统一存 JSON 文本
-- =============================================================

PRAGMA foreign_keys = ON;

-- -------------------------------------------------------------
-- 模块 A：期刊白名单（确定性检索层的唯一判断依据）
-- 对应你上传的白名单文件，一行一本期刊
-- -------------------------------------------------------------
CREATE TABLE journals (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    publisher       TEXT,                       -- AIP / IOP / Springer / IEEE ...
    platform        TEXT,
    url             TEXT,
    issn_print      TEXT,                       -- 抓取时用 ISSN 精确锁定期刊
    issn_electronic TEXT,
    keywords        TEXT,                       -- 兼容旧数据；在线搜索不再作为期刊级准入条件
    year_from       INTEGER DEFAULT 1990,
    year_to         INTEGER,                    -- NULL = 至今
    sci_zone        TEXT,
    impact_factor   REAL,
    active          INTEGER DEFAULT 1,          -- 软删/启停
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- -------------------------------------------------------------
-- 模块 C：文献元数据索引（抓取器 + API 的产物）
-- 只存元数据，不存正文 —— 合法、可日更
-- -------------------------------------------------------------
CREATE TABLE papers (
    id              INTEGER PRIMARY KEY,
    doi             TEXT UNIQUE,                -- 可空：少数无 DOI
    title           TEXT NOT NULL,
    abstract        TEXT,
    authors         TEXT,                       -- JSON: [{"name":..,"affiliation":..}]
    journal_id      INTEGER REFERENCES journals(id),
    journal_name    TEXT,                       -- 冗余一份，便于展示
    published_date  TEXT,
    published_year  INTEGER,
    landing_url     TEXT,                       -- 出版社落地页
    oa_status       TEXT,                       -- gold/green/hybrid/bronze/closed/unknown
    oa_pdf_url      TEXT,                        -- Unpaywall 找到的合法全文链接
    source_api      TEXT,                       -- crossref/openalex/arxiv
    dedupe_key      TEXT UNIQUE,                -- 无 DOI 时的保守去重键，NULL 表示不自动合并
    raw_metadata    TEXT,                        -- JSON 原始响应，便于重处理
    library_status  TEXT NOT NULL DEFAULT 'saved', -- preview / saved；联网搜索新增项先预览
    indexed_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_papers_journal ON papers(journal_id);
CREATE INDEX idx_papers_year    ON papers(published_year);
CREATE INDEX idx_papers_oa      ON papers(oa_status);
CREATE INDEX idx_papers_library_status ON papers(library_status);

-- 全文检索（标题 + 摘要 + 作者 + DOI），供检索界面与在线搜索缓存复用
CREATE VIRTUAL TABLE papers_fts USING fts5(
    title, abstract, authors, doi,
    content='papers', content_rowid='id',
    tokenize='unicode61'
);
CREATE TRIGGER papers_ai AFTER INSERT ON papers BEGIN
    INSERT INTO papers_fts(rowid, title, abstract, authors, doi)
    VALUES (new.id, new.title, new.abstract, new.authors, new.doi);
END;
CREATE TRIGGER papers_ad AFTER DELETE ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, title, abstract, authors, doi)
    VALUES ('delete', old.id, old.title, old.abstract, old.authors, old.doi);
END;
CREATE TRIGGER papers_au AFTER UPDATE ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, title, abstract, authors, doi)
    VALUES ('delete', old.id, old.title, old.abstract, old.authors, old.doi);
    INSERT INTO papers_fts(rowid, title, abstract, authors, doi)
    VALUES (new.id, new.title, new.abstract, new.authors, new.doi);
END;

-- -------------------------------------------------------------
-- 模块 D：分类体系（LLM 分类的目标 taxonomy）
-- -------------------------------------------------------------
CREATE TABLE categories (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE,
    description TEXT,
    parent_id   INTEGER REFERENCES categories(id)
);

-- 文献 ↔ 分类，多对多（一篇可属多个主题）
CREATE TABLE paper_categories (
    paper_id    INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    confidence  REAL,                           -- LLM 置信度
    method      TEXT DEFAULT 'auto',            -- auto / manual
    created_at  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (paper_id, category_id)
);

-- -------------------------------------------------------------
-- 模块 B：抓取任务日志（每日/每周/每月调度的记录，保证可追溯+增量）
-- -------------------------------------------------------------
CREATE TABLE crawl_jobs (
    id           INTEGER PRIMARY KEY,
    journal_id   INTEGER REFERENCES journals(id),
    period       TEXT,                          -- daily/weekly/monthly/manual
    date_from    TEXT,
    date_to      TEXT,
    status       TEXT DEFAULT 'pending',        -- pending/running/success/failed
    papers_found INTEGER DEFAULT 0,
    papers_filtered INTEGER DEFAULT 0,
    papers_new   INTEGER DEFAULT 0,
    search_terms TEXT,                          -- JSON 数组；NULL 表示非定向同步
    search_mode  TEXT,                          -- or / and
    max_results  INTEGER,                       -- 单次搜索期望的全局结果上限
    search_history_id INTEGER,                  -- 对应 search_history.id（兼容迁移不加 FK）
    error        TEXT,
    started_at   TEXT,
    finished_at  TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_crawljobs_journal ON crawl_jobs(journal_id);

-- -------------------------------------------------------------
-- 模块 B.1：在线搜索缓存索引
-- 论文正文仍只存 papers；本表用于判断同一搜索范围是否可复用
-- -------------------------------------------------------------
CREATE TABLE search_history (
    id             INTEGER PRIMARY KEY,
    cache_key      TEXT NOT NULL,
    query_text     TEXT NOT NULL,
    search_terms   TEXT NOT NULL,               -- JSON 数组；逗号/换行分隔后的词或短语
    search_mode    TEXT NOT NULL DEFAULT 'or',  -- or / and
    journal_ids    TEXT NOT NULL,               -- JSON 数组；升序规范化
    date_from      TEXT NOT NULL,
    date_to        TEXT NOT NULL,
    max_results    INTEGER NOT NULL DEFAULT 50,
    status         TEXT NOT NULL DEFAULT 'pending', -- pending/running/success/failed
    decision_status TEXT NOT NULL DEFAULT 'preview', -- preview/saved/discarded
    job_ids        TEXT NOT NULL DEFAULT '[]',  -- JSON 数组；关联本次 crawl_jobs
    result_count   INTEGER DEFAULT 0,
    new_result_count INTEGER DEFAULT 0,
    saved_at       TEXT,
    discarded_at   TEXT,
    error          TEXT,
    created_at     TEXT DEFAULT (datetime('now')),
    finished_at    TEXT
);
CREATE INDEX idx_search_history_cache
    ON search_history(cache_key, status, finished_at);

-- 在线搜索批次 ↔ 命中文献。
-- 保留标题/DOI 快照，使撤销后仍可审计本次曾删除哪些预览项。
CREATE TABLE search_results (
    id                INTEGER PRIMARY KEY,
    search_history_id INTEGER NOT NULL REFERENCES search_history(id) ON DELETE CASCADE,
    paper_id          INTEGER REFERENCES papers(id) ON DELETE SET NULL,
    paper_title       TEXT NOT NULL,
    paper_doi         TEXT,
    was_new           INTEGER NOT NULL DEFAULT 0,
    result_status     TEXT NOT NULL DEFAULT 'preview', -- preview/existing/saved/removed/preserved
    created_at        TEXT DEFAULT (datetime('now')),
    updated_at        TEXT DEFAULT (datetime('now')),
    UNIQUE(search_history_id, paper_id)
);
CREATE INDEX idx_search_results_search ON search_results(search_history_id);
CREATE INDEX idx_search_results_paper  ON search_results(paper_id);

-- -------------------------------------------------------------
-- 模块 E：导入的全文 PDF（理解层入口）
-- -------------------------------------------------------------
CREATE TABLE documents (
    id            INTEGER PRIMARY KEY,
    paper_id      INTEGER REFERENCES papers(id),-- 可空：允许导入未入索引的 PDF
    file_path     TEXT NOT NULL,
    file_hash     TEXT UNIQUE,                  -- 去重
    original_name TEXT,
    num_pages     INTEGER,
    parse_status  TEXT DEFAULT 'uploaded',      -- uploaded/parsing/parsed/failed
    parse_error   TEXT,
    index_status  TEXT DEFAULT 'not_indexed',   -- not_indexed/indexing/indexed/failed
    index_error   TEXT,
    chemistry_status TEXT DEFAULT 'not_extracted', -- not_extracted/extracting/extracted/rejected/failed
    chemistry_error  TEXT,
    tei_path      TEXT,                         -- GROBID TEI/XML 存放路径
    created_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_documents_paper ON documents(paper_id);

-- OA PDF 后台下载任务；成功后 document_id 指向已进入文献库的本地 PDF
CREATE TABLE paper_downloads (
    id            INTEGER PRIMARY KEY,
    paper_id      INTEGER NOT NULL UNIQUE REFERENCES papers(id) ON DELETE CASCADE,
    document_id   INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    status        TEXT NOT NULL DEFAULT 'pending', -- pending/downloading/downloaded/failed
    source_url    TEXT,
    file_path     TEXT,
    error         TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_paper_downloads_status ON paper_downloads(status);

-- GROBID 解析出的结构化章节
CREATE TABLE sections (
    id           INTEGER PRIMARY KEY,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    parent_id    INTEGER REFERENCES sections(id),
    seq          INTEGER,
    title        TEXT,
    content      TEXT,
    section_type TEXT                           -- body/abstract/table/figure_caption/reference
);
CREATE INDEX idx_sections_doc ON sections(document_id);

-- -------------------------------------------------------------
-- 模块 F：翻译
-- -------------------------------------------------------------
CREATE TABLE translations (
    id           INTEGER PRIMARY KEY,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_lang  TEXT,
    target_lang  TEXT,
    status       TEXT DEFAULT 'pending',        -- pending/done/failed
    output_path  TEXT,                          -- 双语对照文档路径
    error        TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_translations_doc ON translations(document_id);

-- 检索元数据中的摘要翻译；不依赖 PDF 文档或 GROBID 解析
CREATE TABLE paper_abstract_translations (
    id           INTEGER PRIMARY KEY,
    paper_id     INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    source_lang  TEXT,
    target_lang  TEXT NOT NULL,
    source_text  TEXT NOT NULL,                 -- 翻译时的摘要快照，用于缓存失效判断
    target_text  TEXT,
    status       TEXT DEFAULT 'pending',        -- pending/done/failed
    error        TEXT,
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_paper_abstract_translations_paper
    ON paper_abstract_translations(paper_id, target_lang, id);

-- 阅读页划选的术语翻译任务。
-- context_text 只保存发起翻译时的段落快照，用于消歧和缓存失效判断。
CREATE TABLE term_translations (
    id           INTEGER PRIMARY KEY,
    source_text  TEXT NOT NULL,
    source_lang  TEXT NOT NULL,
    target_lang  TEXT NOT NULL,
    context_text TEXT,
    target_text  TEXT,
    status       TEXT DEFAULT 'pending',        -- pending/done/failed
    error        TEXT,
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_term_translations_lookup
    ON term_translations(source_text, source_lang, target_lang, status, id);

-- 阅读页双语术语表；作为本地工作台的持久化真理来源。
CREATE TABLE glossary_terms (
    id                 INTEGER PRIMARY KEY,
    en                 TEXT COLLATE NOCASE,
    zh                 TEXT COLLATE NOCASE,
    translation_job_id INTEGER REFERENCES term_translations(id) ON DELETE SET NULL,
    translation_status TEXT,                    -- pending/failed；成功后清空
    translation_error  TEXT,
    created_at         TEXT DEFAULT (datetime('now')),
    updated_at         TEXT DEFAULT (datetime('now')),
    CHECK (
        (en IS NOT NULL AND length(trim(en)) > 0)
        OR (zh IS NOT NULL AND length(trim(zh)) > 0)
    )
);
CREATE INDEX idx_glossary_terms_en
    ON glossary_terms(en) WHERE en IS NOT NULL;
CREATE INDEX idx_glossary_terms_zh
    ON glossary_terms(zh) WHERE zh IS NOT NULL;

-- -------------------------------------------------------------
-- 模块 G：RAG 分块（向量本身存外部向量库，这里只存文本+映射）
-- -------------------------------------------------------------
CREATE TABLE chunks (
    id           INTEGER PRIMARY KEY,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_id   INTEGER REFERENCES sections(id),
    seq          INTEGER,
    text         TEXT NOT NULL,
    token_count  INTEGER,
    vector_id    TEXT,                          -- Chroma/FAISS 中的 ID
    embedded     INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_chunks_doc ON chunks(document_id);

-- -------------------------------------------------------------
-- 模块 G.1：RAG 问答预设指令（本地可编辑资产）
-- 默认指令与用户新增指令统一存储，均可编辑/删除
-- -------------------------------------------------------------
CREATE TABLE prompt_presets (
    id          INTEGER PRIMARY KEY,
    command     TEXT NOT NULL UNIQUE COLLATE NOCASE,
    description TEXT,
    prompt      TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- -------------------------------------------------------------
-- 模块 H：化学库抽取（真正的交付物）
-- 一篇文献 → 一个或多个反应集 → 多条反应
-- -------------------------------------------------------------
CREATE TABLE reaction_sets (
    id            INTEGER PRIMARY KEY,
    document_id   INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    name          TEXT,
    gas_mixture   TEXT,                          -- 如 "Ar/O2"
    lxcat_db      TEXT,                          -- 引用的 LXCat 库：Phelps/Biagi/IST-Lisbon...
    source_note   TEXT,                          -- 出处：表号/章节
    status        TEXT DEFAULT 'pending',        -- pending/verified/rejected（人工闸门）
    verified_by   TEXT,
    verified_at   TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_rsets_doc ON reaction_sets(document_id);

CREATE TABLE reactions (
    id                INTEGER PRIMARY KEY,
    reaction_set_id   INTEGER NOT NULL REFERENCES reaction_sets(id) ON DELETE CASCADE,
    reaction          TEXT NOT NULL,             -- "e + Ar -> e + e + Ar+"
    reaction_type     TEXT,                      -- elastic/excitation/ionization/attachment/recombination
    reactants         TEXT,                      -- JSON
    products          TEXT,                      -- JSON
    rate_type         TEXT,                      -- cross_section / arrhenius / constant
    rate_value        TEXT,                      -- 表达式或数值（保留原文，避免转换误差）
    threshold_ev      REAL,
    reference         TEXT,
    cross_section_url TEXT,                       -- LXCat 链接
    source_section_id INTEGER REFERENCES sections(id),
    source_label      TEXT,                       -- 表号/出处标签，如 table 7: Reaction kinetics
    source_excerpt    TEXT,
    confidence        REAL,
    verified          INTEGER DEFAULT 0,
    review_status     TEXT DEFAULT 'pending',    -- pending/accepted/rejected；verified=1 仅兼容 accepted
    created_at        TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_reactions_set ON reactions(reaction_set_id);

-- 人工复核审计日志：记录每次字段修正与复核动作，保证导出可追溯
CREATE TABLE reaction_audits (
    id          INTEGER PRIMARY KEY,
    reaction_id INTEGER NOT NULL REFERENCES reactions(id) ON DELETE CASCADE,
    action      TEXT NOT NULL,
    changes     TEXT,                          -- JSON object
    verified_by TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_reaction_audits_reaction ON reaction_audits(reaction_id);

-- =============================================================
-- 种子数据：6 本白名单期刊（ISSN 已填，电子版 ISSN 建议上线前核一遍）
-- =============================================================
INSERT INTO journals (name, publisher, platform, url, issn_print, issn_electronic, keywords, year_from, year_to, sci_zone, impact_factor) VALUES
('Physics of Plasmas', 'AIP Publishing', 'AIP', 'https://pubs.aip.org/aip/pop', '1070-664X', '1089-7674',
 '["low temperature plasma","plasma sources","plasma theory","plasma chemistry","plasma physics","plasma diagnostics","capacitively coupled plasma","inductively coupled plasma","plasma simulation","plasma experiment","pulsed plasma"]', 1990, NULL, 'SCI Q3', 2.2),
('Plasma Sources Science and Technology', 'IOP Publishing', 'IOPscience', 'https://iopscience.iop.org/journal/0963-0252', '0963-0252', '1361-6595',
 '["low temperature plasma","plasma sources","plasma theory","plasma chemistry","plasma physics","plasma diagnostics","capacitively coupled plasma","inductively coupled plasma","plasma simulation","plasma experiment","pulsed plasma"]', 1990, NULL, 'SCI Q2', 3.3),
('Plasma Chemistry and Plasma Processing', 'Springer', 'SpringerLink', 'https://link.springer.com/journal/11090', '0272-4324', '1572-8986',
 '["low temperature plasma","plasma sources","plasma theory","plasma chemistry","plasma physics","plasma diagnostics","capacitively coupled plasma","inductively coupled plasma","plasma simulation","plasma experiment","pulsed plasma"]', 1990, NULL, 'SCI Q3', 2.5),
('IEEE Transactions on Plasma Science', 'IEEE', 'IEEE Xplore', 'https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=27', '0093-3813', '1939-9375',
 '["low temperature plasma","plasma sources","plasma theory","plasma chemistry","plasma physics","plasma diagnostics","capacitively coupled plasma","inductively coupled plasma","plasma simulation","plasma experiment","pulsed plasma"]', 1990, NULL, 'SCI Q3', 1.5),
('Plasma Physics and Controlled Fusion', 'IOP Publishing', 'IOPscience', 'https://iopscience.iop.org/journal/0741-3335', '0741-3335', '1361-6587',
 '["low temperature plasma","plasma sources","plasma theory","plasma chemistry","plasma physics","plasma diagnostics","capacitively coupled plasma","inductively coupled plasma","plasma simulation","plasma experiment","pulsed plasma"]', 1990, NULL, 'SCI Q2', 2.3),
('Plasma Science and Technology', 'IOP Publishing', 'IOPscience', 'https://iopscience.iop.org/journal/1009-0630', '1009-0630', '2058-6272',
 '["low temperature plasma","plasma sources","plasma theory","plasma chemistry","plasma physics","plasma diagnostics","capacitively coupled plasma","inductively coupled plasma","plasma simulation","plasma experiment","pulsed plasma"]', 1990, NULL, 'SCI Q4', 1.8);

-- 种子数据：起步用的分类体系（可后续细化/加 parent_id 做层级）
INSERT INTO categories (name, slug, description) VALUES
('放电与等离子体源', 'sources',      'CCP / ICP / DBD / 微波 / 脉冲放电'),
('等离子体化学',     'chemistry',    '反应动力学、反应集'),
('鞘层与边界',       'sheath',       '鞘层、边界、表面相互作用'),
('输运与扩散',       'transport',    '迁移率、扩散、输运系数'),
('等离子体诊断',     'diagnostics',  '探针、光谱、成像等'),
('仿真方法',         'methods',      'Fluid / PIC-MCC / Hybrid / Global model'),
('截面与速率数据',   'cross-section','电子碰撞截面、速率系数、LXCat 数据');

-- 种子数据：问答页默认预设。写入数据库后与用户预设完全相同，均可编辑/删除。
INSERT INTO prompt_presets (command, description, prompt) VALUES
('/总结', '总结当前范围内文献的核心结论', '总结当前范围内文献的核心结论、方法与主要数据。'),
('/术语', '提取并解释文中的专业术语', '提取当前范围文献中的关键专业术语，并逐条解释其含义。'),
('/相关工作', '梳理相关工作与研究脉络', '梳理当前范围文献涉及的相关工作与研究脉络。'),
('/提问我', '就所选文献向我提问，考察理解', '就当前范围的文献内容，向我提出两个考察理解的问题。');

-- 种子数据：阅读页默认双语术语。写入数据库后均可编辑/删除，重启不会重新覆盖。
INSERT INTO glossary_terms (en, zh) VALUES
('capacitively coupled', '容性耦合'),
('electron energy distribution function', '电子能量分布函数'),
('EEDF', '电子能量分布函数'),
('particle-in-cell', '粒子网格法'),
('Monte Carlo collisions', '蒙特卡罗碰撞'),
('secondary electron emission', '二次电子发射'),
('ohmic heating', '欧姆加热'),
('cross section', '截面'),
('dissociation', '解离'),
('ionization', '电离'),
('attachment', '吸附'),
('radical', '自由基'),
('ion flux', '离子通量'),
('sheath', '鞘层'),
('self-bias', '自偏压'),
('rate coefficient', '速率系数');
