# 鸣潮抽卡分析器

一个用于分析鸣潮（Wuthering Waves）抽卡记录的 Web 工具。

## 功能特性

- 支持分析所有卡池类型（角色UP、武器UP、常驻角色、常驻武器）
- 保底进度追踪（当前距离五星/四星保底的抽数）
- 五星出货记录展示（含提前出货标记）
- 运气评价系统（天选之人 / 运气不错 / 中规中矩 / 有点非了 / 大非酋）
- 可视化图表（卡池分布饼图、出货抽数柱状图）
- 深色主题 UI

## 安装与运行

### 1. 安装依赖

```bash
cd wuwa-gacha-analyzer
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

### 3. 访问页面

打开浏览器访问 http://localhost:5000

## 如何获取抽卡链接

### 方法一：从游戏日志获取

1. 打开鸣潮游戏，进入**唤取**（抽卡）界面
2. 点击历史记录按钮，打开抽卡历史页面
3. 关闭游戏
4. 找到游戏日志文件：`%AppData%\..\Local\Wuthering Waves\Client\Saved\Logs\Client.log`
5. 在日志中搜索 `gacha/record/query`，找到完整的请求 URL
6. 复制 URL 粘贴到分析器输入框

### 方法二：使用抓包工具

1. 打开抓包工具（如 Fiddler、Charles、mitmproxy）
2. 打开鸣潮游戏，进入**唤取**界面
3. 点击历史记录按钮
4. 在抓包工具中找到包含 `gacha/record/query` 的请求
5. 复制完整的请求 URL 或 JSON 请求体

### 输入格式支持

- **完整 URL**: `https://gmserver-api.aki-game2.com/gacha/record/query?serverId=xxx&playerId=xxx&roleId=xxx&...`
- **JSON 格式**: `{"serverId": "xxx", "playerId": "xxx", "roleId": "xxx", ...}`
- **查询参数**: `serverId=xxx&playerId=xxx&roleId=xxx&...`

### 抓包工具推荐

- **Windows**: [Fiddler](https://www.telerik.com/fiddler) / [Charles](https://www.charlesproxy.com/)
- **通用**: [mitmproxy](https://mitmproxy.org/)（命令行工具）

## 技术栈

- **后端**: Python + Flask
- **前端**: HTML + CSS + JavaScript
- **图表**: Chart.js

## 项目结构

```
wuwa-gacha-analyzer/
├── app.py              # Flask 后端
├── requirements.txt    # Python 依赖
├── static/
│   ├── style.css       # 样式文件
│   └── app.js          # 前端逻辑
├── templates/
│   └── index.html      # 主页面
└── README.md           # 本文件
```

## 注意事项

- 抽卡链接有时效性，过期后需要重新获取
- 请勿频繁请求 API，避免触发频率限制
- 本工具仅供个人分析使用
