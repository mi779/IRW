# 词根/前缀多对多数据库模型与业务逻辑实现计划

## Context

项目是一个英语单词学习软件，核心差异化功能是「同前缀/同词根分组学习」。当前已完成项目脚手架（Vue 3 + FastAPI），但后端无数据模型和 API，前端仅脚手架示例。需要从零设计数据库模型、实现 SM-2 间隔重复算法、构建词根关系图可视化。

## 一、数据库 Schema 设计

### 表结构

**Word（单词表）**
- `id` Integer PK
- `spelling` String(100) unique not null — 拼写
- `phonetics` JSON — `{"us": "...", "uk": "..."}`
- `definitions` JSON — `[{"pos": "v.", "text": "检查"}]`
- `part_of_speech` String(20) — 冗余字段
- `example_sentences` JSON — 例句列表
- `created_at` / `updated_at` DateTime

**Root / Prefix / Suffix（词根/前缀/后缀表，结构相同）**
- `id` Integer PK
- `text` String(50) unique not null — 如 `spect`、`pre`、`-tion`
- `meaning` String(200) — 如 `看`
- `description` Text — 详细说明

**关联表（Table，非 ORM 类）**
- `word_root` — (word_id, root_id) 复合主键
- `word_prefix` — (word_id, prefix_id) 复合主键
- `word_suffix` — (word_id, suffix_id) 复合主键
- 均带 `ondelete="CASCADE"`

**ReviewLog（复习记录表）— SM-2 字段**
- `id` Integer PK
- `word_id` FK(words.id) not null
- `review_date` DateTime not null default now
- `quality` Integer not null — 0-5
- `ease_factor` Float not null default 2.5
- `interval_days` Integer not null default 0
- `repetitions` Integer not null default 0
- `due_date` DateTime not null — 下次到期

**User（用户表，占位）**
- `id` / `username` / `email` / `hashed_password` / `created_at`

### 关键设计取舍
- JSON 字段用 `sqlalchemy.JSON`（SQLite 兼容，迁 PostgreSQL 可改 JSONB）
- 关联表用 `Table` 而非 ORM 类（轻量，后续可升级）
- SM-2 状态存在 ReviewLog（保留完整复习历史，查队列用子查询取最新记录）
- `lazy="selectin"` 避免 async 下 N+1 问题

## 二、后端文件结构

```
backend/
├── main.py              [改] 注册 routers + lifespan 建表
├── .env                 [新] DATABASE_URL
├── core/
│   ├── config.py        [新] pydantic-settings Settings
│   └── database.py      [新] async engine + Base + get_db + init_db
├── models/
│   ├── __init__.py      [新] 统一导出
│   ├── base.py          [新] TimestampMixin
│   ├── associations.py  [新] word_root/word_prefix/word_suffix Table
│   ├── word.py          [新] Word model + relationships
│   ├── morpheme.py      [新] Root/Prefix/Suffix（同构一个文件）
│   ├── review.py        [新] ReviewLog model
│   └── user.py          [新] User model
├── schemas/
│   ├── word.py          [新] WordCreate/WordRead/WordReadWithRelations
│   ├── morpheme.py      [新] Root/Prefix/Suffix 的 Create/Read
│   ├── review.py        [新] ReviewLogCreate/Read, ReviewQueueItem
│   ├── graph.py         [新] G6Node/G6Edge/GraphData
│   └── user.py          [新] UserCreate/UserRead
├── services/
│   ├── sm2.py           [新] SM-2 纯函数算法（可单测）
│   └── review_service.py [新] apply_review / get_due_queue
├── routers/
│   ├── words.py         [新] /api/words CRUD + by-root/by-prefix
│   ├── morphemes.py     [新] /api/roots /api/prefixes /api/suffixes
│   ├── review.py        [新] /api/review/queue、/api/review/log
│   ├── graph.py         [新] /api/graph/root/{id} 返回 G6 数据
│   └── users.py         [新] 占位
└── tests/
    └── test_sm2.py      [新] SM-2 单测
```

## 三、SM-2 算法实现

`services/sm2.py` — 纯函数，无 IO：

```python
def sm2_update(quality, prev_ease=2.5, prev_interval=0, prev_repetitions=0):
    # quality >= 3: reps=0→interval=1, reps=1→interval=6, else→interval=round(prev*ef)
    # quality < 3: 重置 reps=0, interval=1
    # EF = max(1.3, prev_ease + (0.1 - (5-q)*(0.08+(5-q)*0.02)))
    return SM2Result(ease_factor, interval_days, repetitions, due_offset_days)
```

- `review_service.apply_review(db, word_id, quality)`：取最新 ReviewLog → sm2_update → 写新 ReviewLog
- `review_service.get_due_queue(db)`：子查询取每个 word 最新 ReviewLog → 筛 due_date <= now

## 四、前端文件结构

```
frontend/src/
├── main.ts              [改] 注册 Element Plus + 样式
├── App.vue              [改] 导航栏 + RouterView
├── router/index.ts      [改] +/words /roots /review 路由
├── types/index.ts       [新] TS 接口定义
├── services/
│   ├── request.ts       [新] axios 实例
│   ├── wordService.ts   [新] 单词 CRUD + by-root/by-prefix
│   ├── morphemeService.ts [新] 词根/前缀/后缀 CRUD + graph
│   └── reviewService.ts [新] 队列 + logReview
├── stores/
│   ├── word.ts          [新] words 列表 + selectedWord
│   ├── morpheme.ts      [新] roots 列表 + graphData
│   └── review.ts        [新] reviewQueue + logReview
├── components/
│   ├── WordCard.vue     [新] 单词详情卡片
│   ├── RootGraph.vue    [新] AntV G6 v5 词根派生图（核心差异化）
│   ├── ReviewPanel.vue  [新] 复习面板 + 0-5 质量按钮
│   └── WordForm.vue     [新] 新增/编辑单词表单
└── views/
    ├── HomeView.vue     [改] Dashboard 入口
    ├── WordsView.vue    [新] 单词管理列表
    ├── RootsView.vue    [新] 词根分组 + 图谱
    └── ReviewView.vue   [新] 复习流程
```

### G6 v5 关键实现
- `new Graph({ container, data: {nodes, edges}, node: {type:'rect', style}, edge: {type:'line', endArrow}, layout: {type:'radial'}, behaviors: [...] })`
- root 节点橙色，word 节点蓝色，点击 word 触发详情展示
- `onMounted` 创建，`onBeforeUnmount` destroy，`watch` 数据更新

## 五、实施顺序（5 个阶段）

### 阶段 1：后端数据层
1. `core/config.py` + `core/database.py`
2. `models/` 全部模型文件
3. `main.py` 添加 lifespan 建表，验证 vocab.db 生成

### 阶段 2：后端算法与 API
4. `services/sm2.py` + 单测
5. `schemas/` 全部 Pydantic 模型
6. `services/review_service.py`
7. `routers/` 全部路由文件
8. `main.py` 注册 routers，Swagger 联调

### 阶段 3：前端基础层
9. `main.ts` 注册 Element Plus
10. `types/index.ts` + `services/` + `stores/`

### 阶段 4：前端组件与页面
11. `WordCard` → `WordForm` → `WordsView`
12. `RootGraph`（G6 v5 核心） → `RootsView`
13. `ReviewPanel` → `ReviewView`
14. 路由 + 导航更新

### 阶段 5：联调与种子数据
15. spect 词根族种子数据（inspect/spectator/respect/prospect...）
16. 端到端走查

## 六、验证方式

1. **后端**：启动 uvicorn → 打开 `http://localhost:8000/docs` Swagger → 测试所有 API
2. **SM-2**：运行 `pytest tests/test_sm2.py` 验证算法正确性
3. **前端**：`npm run dev` → 访问各页面 → 词根图谱渲染 → 复习流程跑通
4. **端到端**：添加词 → 关联词根 → 图谱显示 → 进入复习 → 记录复习 → 队列更新

## 七、关键注意事项

- Element Plus **必须**在 `main.ts` 中 `app.use(ElementPlus)` + 导入 CSS，否则所有 el-* 组件不渲染
- G6 是 **v5**，API 与 v4 完全不同，用配置式 `new Graph({data, node, edge, layout})`
- SQLAlchemy 2.0 async 用 `Mapped`/`mapped_column`，关系用 `lazy="selectin"` 避免 N+1
- CORS 已配置（允许 localhost:5173），`@` alias 已就绪（→ src）
