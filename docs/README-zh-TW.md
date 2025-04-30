# Graph-Codebase-MCP

[ [English](../README.md) | [繁體中文](README-zh-TW.md) ]

透過 Neo4j 知識圖譜實現程式碼庫的智慧搜尋與分析

## 專案概述

Graph-Codebase-MCP 是一個專門為程式碼庫建立知識圖譜的工具，結合了 Neo4j 圖形資料庫與 Model Context Protocol (MCP) 提供智慧化的程式碼搜尋與分析能力。專案使用 AST (抽象語法樹) 分析 Python 程式碼結構，並透過 OpenAI Embeddings 進行語義編碼，將程式碼的實體與關係儲存於 Neo4j 中形成知識圖譜。

透過 MCP server 介面，AI 代理能夠更加智慧地理解與搜尋程式碼，超越傳統文字搜尋的限制，實現對程式碼結構與語義的更深入理解。

### 知識圖譜視覺化範例

下圖展示了一個 [範例程式碼](../example_codebase) 的知識圖譜：

![知識圖譜範例](images/example_graph.svg)

圖中展示了檔案（粉色）、類別（藍色）、函數和方法（黃色）、變數（綠色）之間的關係網絡，包括：
- 檔案間的導入關係 (IMPORTS_FROM)
- 檔案對特定符號的導入 (IMPORTS_DEFINITION)
- 類別的繼承關係 (EXTENDS)
- 函數調用關係 (CALLS)
- 類別與其方法/屬性的定義關係 (DEFINES)

這種結構化的表示使得 AI 可以更有效地理解程式碼的結構與語義關係。

## 核心功能

- **程式碼解析**：使用 AST (Abstract Syntax Tree) 分析 Python 程式碼結構，提取變數、函數、類別及其關係
- **語義嵌入**：利用 OpenAI Embeddings 為程式碼元素生成向量表示，捕捉語義特性
- **知識圖譜建立**：將解析的程式碼元素與關係儲存到 Neo4j 圖形資料庫，形成完整的知識圖譜
- **知識圖譜視覺化**：透過 Neo4j 的視覺化功能，直觀呈現程式碼結構與關係
- **MCP 查詢介面**：遵循 Model Context Protocol 標準，提供 AI 代理友好的查詢接口
- **關係型查詢**：支援複雜的程式碼關係查詢，如函數調用鏈、依賴關係等
- **跨檔案分析**：準確追蹤檔案間的依賴關係，包括模組導入與符號引用

## 支援的程式語言

- [x] Python
- [ ] Java
- [ ] C++
- [ ] JavaScript

## 系統需求

- Python 3.12.7 或更高版本
- Neo4j 圖形資料庫 (5.x 版本建議)
- Docker (可選，用於容器化部署)

## 安裝指南

### 1. 複製專案

```bash
git clone https://github.com/your-username/graph-codebase-mcp.git
cd graph-codebase-mcp
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

創建 `.env` 檔案或使用 `mcp.json` 指定環境參數：

`.env` 檔案範例：
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
OPENAI_API_KEY=your_openai_api_key
```

或 `mcp.json` 檔案範例：
```json
{
  "mcpServers": {
    "graph-codebase-mcp": {
      "command": "python",
      "args": [
          "src/mcp_server.py",
          "--codebase-path",
          "path/to/your/codebase"
        ],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password",
        "OPENAI_API_KEY": "your_openai_api_key"
      }
    }
  }
}
```

### 4. 啟動 Neo4j

若使用 Docker：
```bash
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
```

訪問 Neo4j 瀏覽器：http://localhost:7474

## 使用說明

### 1. 建立程式碼知識圖譜

執行主程式以分析程式碼庫並建立知識圖譜：

```bash
python src/main.py --codebase-path /path/to/your/codebase
```

### 2. 啟動 MCP Server

```bash
python src/mcp_server.py
```
## MCP 查詢範例

本專案支援多種程式碼相關查詢，例如：

- 查找特定函數的所有調用者：`"find all callers of function:process_data"`
- 查找特定類別的繼承結構：`"show inheritance hierarchy of class:DataProcessor"`
- 查詢某文件的依賴關係：`"list dependencies of file:main.py"`
- 查找與特定模塊相關的代碼：`"search code related to module:data_processing"`
- 跨檔案追蹤符號的導入與使用：`"trace imports and usages of class:Employee"`
- 分析檔案間的依賴網絡：`"analyze dependency network starting from file:main.py"`

## 架構概述

```
graph-codebase-mcp/
├── src/
│   ├── ast_parser/           # 程式碼 AST 解析模組
│   │   └── parser.py         # AST 解析器實現，含跨檔案依賴分析
│   ├── embeddings/           # OpenAI Embeddings 處理模組
│   ├── neo4j_storage/        # Neo4j 資料庫操作模組
│   ├── mcp/                  # MCP Server 實現
│   ├── main.py               # 主程式入口
│   └── mcp_server.py         # MCP Server 啟動入口
├── examples/                 # 使用範例
├── tests/                    # 測試案例
├── docs/                     # 文件與圖表
│   └── images/               # 圖片資源
├── .env.example              # 環境變數範例
├── requirements.txt          # 依賴套件清單
└── README.md                 # 說明文件
```

## 技術棧

- **程式語言**：Python 3.12.7
- **程式碼分析**：Python AST 模組
- **向量嵌入**：OpenAI Embeddings
- **圖形資料庫**：Neo4j
- **介面協議**：Model Context Protocol (MCP)
- **SDK 支援**：MCP Python SDK, Neo4j Python SDK

## 授權條款

MIT License

## 參考資源

- [Neo4j GraphRAG Python Package](https://neo4j.com/blog/news/graphrag-python-package/)
- [Model Context Protocol](https://github.com/modelcontextprotocol/specification)
- [Neo4j Python Driver Documentation](https://neo4j.com/docs/api/python-driver/)
- [Python AST Module Documentation](https://docs.python.org/3/library/ast.html)

---


