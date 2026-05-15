# GiftMaster - 挑礼大师 - Multi-Agent 送礼推荐系统
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-black?logo=flask&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-purple)
![Status](https://img.shields.io/badge/Status-Active-success)

基于 LangGraph 的智能送礼推荐助手，通过多Agent协作帮助用户快速找到合适的礼物。

## 项目结构
```
gift-master/
├── backend/
│   ├── __init__.py
│   ├── state.py          # 状态定义
│   ├── agents.py         # 5个Agent实现
│   ├── nodes.py          # LangGraph节点函数
│   ├── graph.py          # 状态机构建
│   ├── utils.py          # 工具函数
│   ├── main.py           # 主函数
│   └── gifts.json        # 商品库
├── frontend/
│   ├── index.html        # 首页
│   └── chat.html         # 对话页面
├── start.sh              # 启动脚本
├── requirements.txt
└── output.log
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API Key

```bash
export DEEPSEEK_API_KEY="your-deepseek-api-key"
```

或直接修改 `server.py` 第16行：

```python
API_KEY = "your-deepseek-api-key"
```

### 3. 运行

```bash
python server.py
```

访问：http://localhost:5000

## 核心功能

### 双路径推荐

**目标明确型**：用户已知送礼对象、场合、预算 → 直接推荐商品

**探索型**：用户不确定 → 引导式提问 → 逐步推荐

### 5个Agent协作

1. **意图识别Agent**：判断用户模式（目标型/探索型）
2. **澄清提问Agent**：从用户输入提取结构化标签
3. **探索推荐Agent**：生成品类探索卡片
4. **理由生成Agent**：为商品生成推荐理由
5. **校验Agent**：多重验证防止幻觉

### 标签体系

- **recipient**：朋友/恋人/妈妈/爸爸/同事/领导/老师/长辈/孩子
- **occasion**：生日/纪念日/节日/感谢/探望/乔迁/婚礼/商务往来/日常惊喜
- **budget**：100以内/100-300/300-500/500以上/不限
- **time**：明天就要/3天内/一周内/不着急
- **preference**：实用/有心意/小众特别/稳妥不出错/仪式感/高级感
- **category**：数码/美妆护肤/饰品配饰/食品礼盒/家居生活/文创礼品/鲜花绿植/玩具潮玩/服饰箱包/个护香氛

## 使用示例

### 示例1：目标明确

```
用户：送女朋友生日礼物，预算300以内，想要有心意一点的

系统：【永生花礼盒】¥228
      适合作为送恋人的生日礼物，永生花寓意长久，比较容易传达心意
      
      【口红礼盒套装】¥299
      经典色号组合，有仪式感且实用
```

### 示例2：探索型

```
用户：想送朋友一个礼物，但不知道送什么

系统：你这份礼物主要是送给谁？
      [朋友] [恋人] [妈妈] [爸爸] [同事] [领导]

用户：朋友

系统：为你推荐以下几个方向：
      
      【家居生活】稳妥实用，适合大多数送礼场景
      【文创礼品】更有记忆点，适合表达心意
      【美妆护肤】适合送女性朋友，实用且贴心
```

## 开发指南

### 添加新商品

编辑 `backend/gifts.json`：

```json
{
  "product_id": "sku_041",
  "title": "商品名称",
  "category": "品类",
  "price": 199,
  "budget": "100-300",
  "description": "商品描述",
  "fast_delivery": true,
  "recipient_fit": ["朋友", "恋人"],
  "occasion_fit": ["生日", "节日"],
  "preference_fit": ["有心意", "实用"],
  "popularity_score": 8.5
}
```

### 修改推荐逻辑

编辑 `backend/utils.py`：

- 'filter_products()'：商品过滤规则
- 'score_product()'：商品评分算法
- 'validate_recommendations()'：结果校验规则

## API接口

### POST /api/chat

请求：

```json
{
  "message": "用户输入",
  "session_id": "会话ID"
}
```

响应：

```json
{
  "success": true,
  "response": {
    "type": "product_recommendations",
    "products": [
      {
        "product_id": "sku_001",
        "title": "商品名称",
        "price": 199,
        "reason": "推荐理由"
      }
    ],
    "actions": ["换一批", "看便宜一点的"]
  }
}
```

## 技术栈

- LangGraph 0.2.45 - 状态机编排
- LangChain 0.3.7 - LLM框架
- Flask 3.0.0 - Web服务器
- DeepSeek API - 大语言模型

## 环境要求

- Python 3.8+
- DeepSeek API Key

## 注意事项

1. 首次运行需要联网下载依赖
2. API Key必须配置否则无法使用
3. 商品库可根据实际需求扩展
4. 推荐逻辑可根据业务调整

## License

MIT
