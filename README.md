# QQ 卡片解析插件 (QCard Parser)

将 OneBot 传递的 QQ 卡片 JSON 转换为结构化可读文本，使 LLM 能够理解卡片内容。

## 功能特性

### 支持的卡片类型

#### 1️⃣ 小程序卡片
- **标识**: `app="com.tencent.miniapp"`
- **提取信息**:
  - 应用名称 (title)
  - 预览图链接 (preview)
  - 跳转链接 (jumpUrl)

**示例输出**:
```
[小程序]
名称: 天气预报
预览: https://example.com/weather.png
链接: pages/weather?city=beijing
```

#### 2️⃣ 链接分享卡片
- **标识**: `app="com.tencent.structmsg"` + `view="news"`
- **提取信息**:
  - 链接标题 (title)
  - 链接描述 (desc，超过100字自动截断)
  - 来源标签 (tag)
  - 目标链接 (url)

**示例输出**:
```
[分享]
标题: Python 3.13 发布
描述: Python 官方发布了 3.13 版本，包含多项性能改进...
来源: 技术新闻
链接: https://www.python.org/news/release-3.13
```

## 工作原理

```
接收消息事件
    ↓
qcard-parser 高优先级拦截 (priority: maxsize-2)
    ↓
检查是否包含 Json 组件（卡片消息）
    ↓
按优先级识别卡片类型
    ├─ 小程序卡片 → parse_miniapp_card()
    ├─ 链接分享卡片 → parse_link_share_card()
    └─ 未知类型 → 跳过
    ↓
提取关键信息，构造易读文本
    ↓
注入到 message_str
    ↓
LLM 接收到完整的卡片内容 + 消息
```

## 安装

### 方式 1️⃣: 从 GitHub 安装（推荐）

```bash
# 使用 AstrBot 的插件管理界面或命令
# 或手动克隆到 data/plugins/ 目录
git clone https://github.com/NekyuuYa/astrbot_plugin_qcard_parser data/plugins/qcard_parser
```

### 方式 2️⃣: 手动安装

1. 克隆仓库到项目的 `data/plugins/` 目录
2. AstrBot 启动时会自动加载插件
3. 无需额外配置

```bash
# 项目结构
AstrBot/
├── data/
│   └── plugins/
│       └── qcard_parser/
│           ├── main.py
│           ├── metadata.yaml
│           └── ...
```

## 使用示例

### 用户在 QQ 群发送小程序卡片

**用户操作**：分享天气小程序

**OneBot 消息**：
```json
{
  "message": [
    {"type": "text", "data": {"text": "看看今天天气"}},
    {
      "type": "json",
      "data": {
        "data": "{\"app\":\"com.tencent.miniapp\",\"title\":\"天气预报\",\"preview\":\"https://...\",\"jumpUrl\":\"pages/weather?city=beijing\"}"
      }
    }
  ]
}
```

**LLM 接收到**：
```
看看今天天气

[小程序]
名称: 天气预报
预览: https://...
链接: pages/weather?city=beijing
```

**LLM 能够理解** → 生成更准确的回复

## 配置说明

该插件 **无需配置**，启用后即可自动工作。

### 高级配置（可选）

如需修改解析行为，编辑 `main.py`：

```python
# 修改描述截断长度（默认 100 字符）
if len(desc) > 150:  # 改为 150
    desc = desc[:150] + "..."
```

## 代码结构

### CardParser 类

核心解析逻辑：

- `parse_miniapp_card(data: dict) -> Optional[str]`
  - 解析小程序卡片
  - 提取 title, preview, jumpUrl
  
- `parse_link_share_card(data: dict) -> Optional[str]`
  - 解析链接分享卡片
  - 提取 meta.news 中的关键字段
  
- `parse_json_card(raw_json) -> Optional[str]`
  - 通用卡片解析入口
  - 按优先级尝试各类型解析器

### Main 类

插件主类，继承自 `Star`：

- `__init__(context: Context)`
  - 初始化插件
  
- `parse_qq_cards(event: AstrMessageEvent)`
  - 消息事件处理器
  - 高优先级 (maxsize-2) 拦截
  - 遍历消息链，解析 Json 组件

## 扩展指南

### 添加新卡片类型支持

1️⃣ 在 `CardParser` 类中添加解析方法：

```python
@staticmethod
def parse_music_card(data: dict) -> Optional[str]:
    """解析音乐卡片"""
    if data.get("app") != "com.tencent.music":
        return None
    
    title = data.get("title", "").strip()
    singer = data.get("singer", "").strip()
    url = data.get("url", "").strip()
    
    parts = ["[音乐]"]
    if title:
        parts.append(f"歌曲: {title}")
    if singer:
        parts.append(f"歌手: {singer}")
    if url:
        parts.append(f"链接: {url}")
    
    return "\n".join(parts) if len(parts) > 1 else None
```

2️⃣ 在 `parse_json_card` 中注册：

```python
@classmethod
def parse_json_card(cls, raw_json) -> Optional[str]:
    # ... existing code ...
    
    # 音乐卡片
    result = cls.parse_music_card(data)
    if result:
        return result
    
    return None
```

## 日志输出

插件会输出调试日志：

```
[QCard Parser] Successfully parsed: [小程序]名称: 天气预报...
[QCard Parser] Injected 1 card(s) into message
```

启用调试日志可查看解析详情。

## 已知限制

1. **不支持的卡片类型**
   - 音乐卡片 (com.tencent.music)
   - 投票卡片 (com.tencent.qappsrv, type=poll)
   - 群公告卡片
   - 等其他卡片类型
   
   → 可通过上述扩展方式添加支持

2. **描述长度限制**
   - 链接分享卡片的描述将被截断至 100 字符
   - 防止消息过长影响 LLM 处理

3. **嵌套卡片**
   - 暂不支持卡片内包含其他卡片的情况

## 技术细节

### 优先级选择

使用优先级 `maxsize - 2`：
- 确保在其他插件处理前就解析完毕
- 为最高优先级插件预留空间 (maxsize-1)

### 错误处理

- 解析异常被捕捉并记录为调试日志
- 不会中断事件流，确保消息继续处理
- 无法识别的卡片类型会被安全跳过

### 性能考虑

- 仅遍历消息链中的 `Json` 组件
- 轻量级解析，不影响性能
- 调试日志仅在需要时输出

## 相关文件

- `main.py` - 插件核心代码
- `metadata.yaml` - 插件元数据
- `README.md` - 本文件

## 常见问题

### Q: 如何验证插件已加载？

**A**: 启动 AstrBot 后查看日志：
```
QQ Card Parser plugin loaded
```

### Q: 卡片信息为什么没有显示给 LLM？

**A**: 检查以下几点：
1. 确认卡片类型是否被支持（小程序、链接分享）
2. 检查 metadata.yaml 中的 name 是否与实际一致
3. 查看启动日志中是否有错误信息

### Q: 如何添加对新卡片类型的支持？

**A**: 参考上述 **扩展指南** 部分

## 许可证

AGPL-3.0

## 贡献

欢迎提交 Issue 和 PR！

## 相关资源

- [AstrBot 官方仓库](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发指南 (中文)](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot 插件开发指南 (English)](https://docs.astrbot.app/en/dev/star/plugin-new.html)
- [OneBot 协议文档](https://onebot.dev/)

---

**插件状态**: ✅ 生产就绪

该插件已完全测试，可在生产环境中使用。
