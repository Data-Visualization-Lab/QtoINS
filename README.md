# QtoINS 项目文档

## 1. 项目简介

QtoINS 是一个“表格问答到可视化洞察”的全栈原型系统，核心能力是：

- 上传 CSV 数据并自动生成数据描述
- 将自然语言问题转成 SQL（支持模糊概念占位 `{}`）
- 对“文本模糊”和“字符串模糊”进行交互式澄清
- 自动推荐 Vega-Lite 图表并生成分步 insight
- 支持对图表和 insight 进行二次改写

前端在 `data_prompt`，后端在 `server4`。

## 2. 当前架构

### 前端（React + TypeScript）

- 入口：`data_prompt/src/app/App.tsx`
- 主要区域：
  - Table View（CSV 预览 + 上传）
  - Chatbot Query View（对话与模糊澄清）
  - Preview Chart View（图表列表）
  - Expanded Chart + Insight View（大图与 insight 编辑）

### 后端（Flask + DuckDB）

- 入口：`server4/app10.py`
- 端口：`127.0.0.1:5000`
- 核心接口：
  - `POST /upload`
  - `POST /gettext`
  - `POST /api/fuzzytext`
  - `POST /api/fuzzystring`
  - `POST /api/runfollowups`
  - `POST /api/changechart`
  - `POST /api/changeinsight`

## 3. 目录结构（核心）

```text
QtoINS
├── README.md
├── data_prompt/                  # 前端
│   ├── package.json
│   ├── src/app/App.tsx
│   ├── src/views/upload.tsx
│   ├── src/views/plot.tsx
│   ├── src/views/PlotPreview.tsx
│   └── src/hooks/*.ts
└── server4/                      # 后端
    ├── app10.py
    ├── features/                 # 特征工程（图表推荐辅助）
    └── function/                 # SQL生成/模糊处理/图表和insight逻辑
```

## 4. 运行环境

建议：

- Python `3.10+`
- Node.js `18+`（或与 CRA 兼容的 LTS）
- npm `9+`

## 5. 快速启动

### 5.1 启动后端

```bash
cd server4
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install flask pandas numpy duckdb sqlglot openai sentence-transformers torch scipy python-dateutil editdistance altair vl-convert-python regex sql-metadata sqlparse
python app10.py
```

后端启动成功后会监听：`http://127.0.0.1:5000`

### 5.2 启动前端

```bash
cd data_prompt
npm install
npm start
```

前端默认地址：`http://localhost:3000`

前端已在 `data_prompt/package.json` 配置了：

```json
"proxy": "http://127.0.0.1:5000"
```

因此前端使用相对路径请求后端接口即可。

## 6. 使用流程（端到端）

1. 打开页面，点击 `Upload` 上传 CSV
2. 后端 `/upload` 返回数据摘要（会显示在聊天首条 system 消息）
3. 在聊天框输入问题，触发 `/gettext`
4. 若存在模糊概念：
   - 文本模糊：前端依次提交 `/api/fuzzytext`
   - 字符串模糊：前端依次提交 `/api/fuzzystring`
5. 当后端返回 `awaitingFollowup=true` 后，点击 `Run Next Two Steps`
6. 前端调用 `/api/runfollowups`，后端生成图表与 insight
7. 在右侧可继续：
   - 输入图表修改请求（`/api/changechart`）
   - 按 insight 步骤改写（`/api/changeinsight`）

## 7. 接口说明（重点）

### 7.1 `POST /upload`

上传 CSV 并初始化数据上下文。

- Content-Type：`multipart/form-data`
- 字段：
  - `csv_file`: 文件
  - `file_name`: 表名（建议无空格）

返回示例：

```json
{
  "message": "File uploaded successfully",
  "description": "This tabular data has ..."
}
```

注意：后端会把列名中的空格替换为下划线 `_`。

### 7.2 `POST /gettext`

输入用户自然语言问题，执行 SQL 生成与模糊检测。

请求示例：

```json
{
  "text": "Compare sales by region in 2023"
}
```

典型返回分支：

- 无模糊（进入 followup）：
  - `textfuzzy=false`
  - `stringfuzzy=false`
  - `awaitingFollowup=true`
  - `finalquestion=...`
- 有文本模糊：
  - `textfuzzy=true`
  - `textrecommend={...}`
- 有字符串模糊：
  - `stringfuzzy=true`
  - `stringresult={...}`

### 7.3 `POST /api/fuzzytext`

提交文本模糊项选择/输入。

请求示例：

```json
{
  "keyName": "rating+SELECT+uuid",
  "category": "multiple_column",
  "solution": ["avg_rating", "max_rating"],
  "userInput": "[\"avg_rating\"]"
}
```

### 7.4 `POST /api/fuzzystring`

提交字符串模糊项选择。

请求示例：

```json
{
  "keyName": "condition_0 - Genre",
  "category": "multiple_string",
  "solution": ["Fiction", "Historical Fiction"],
  "userInput": "[\"Fiction\"]",
  "columnname": "Genre",
  "backendKey": "condition_0+uuid"
}
```

### 7.5 `POST /api/runfollowups`

在所有模糊问题解决后触发图表与 insight 正式生成。

请求示例（直接传最终结果数组）：

```json
[
  { "8d4d9fd6-1fbf-4cf1-9aeb-2ea706d5b255": "Fiction" },
  { "5c50d328-afaf-4e8b-9aab-0f1840e0f7fc": ["10", "20"] }
]
```

返回核心字段：

```json
{
  "message": "Data received",
  "vis": {
    "uuid-1": {
      "description": "...",
      "question": "...",
      "VisualRecommend_instance_result": {},
      "insight": []
    }
  }
}
```

### 7.6 `POST /api/changechart`

根据自然语言请求改写当前图表（Vega-Lite）。

### 7.7 `POST /api/changeinsight`

基于用户选中的 insight step 继续推理，并可选返回更新后的图表。

## 8. 关键实现说明

- SQL 占位符规则由 `server4/function/brace_toolkit.py` 控制，严格限制 `{}` 的合法位置
- 字符串模糊匹配使用 `SentenceTransformer` 向量检索
- 图表推荐先做字段统计特征抽取（`server4/features/*`），再调用模型生成 Vega-Lite
- 图表统一注入基础交互能力（`add_basic_interactive_features`）

## 9. 开发与排错

### 常见问题

1. 前端 3000 能开，但请求失败  
   - 确认后端 `app10.py` 是否启动在 `127.0.0.1:5000`
2. 字符串模糊处理报设备错误  
   - 当前代码里嵌入模型默认设备是 `mps`（Apple 芯片），其他环境可改为 `cpu`
3. 图表/insight 生成慢  
   - 该流程会调用多次模型接口，属于正常现象

### 调试建议

- 后端日志直接查看 `server4/app10.py` 控制台输出
- 前端交互主流程在：
  - `data_prompt/src/hooks/useChatLogic.ts`
  - `data_prompt/src/hooks/useFuzzyTextLogic.ts`
  - `data_prompt/src/hooks/useFuzzyStringLogic.ts`

## 10. 当前风险与改进建议

1. **密钥管理风险**：多个后端文件中存在硬编码 API Key，建议立即改为环境变量读取
2. **并发隔离风险**：后端使用全局变量保存会话状态，当前更适合单用户演示
3. **依赖管理缺失**：建议补充 `server4/requirements.txt` 固化版本
4. **生产配置**：当前 Flask 为 `debug=True`，生产部署需关闭并使用 WSGI 服务
