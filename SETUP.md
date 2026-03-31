# QQ 卡片解析插件 - 项目配置指南

## 📁 项目结构

```
astrbot_plugin_qcard_parser/
├── main.py              # 插件主代码
├── metadata.yaml        # 插件元数据配置
├── README.md           # 详细使用文档
├── test_parser.py      # 单元测试脚本
├── requirements.txt    # 依赖列表
├── .gitignore          # Git 忽略配置
├── LICENSE             # 开源许可证（AGPL-3.0）
└── SETUP.md            # 本文件
```

## 🚀 快速开始

### 1. 在本地测试

不需要完整安装 AstrBot，直接测试卡片解析逻辑：

```bash
# 克隆仓库
git clone https://github.com/NekyuuYa/astrbot_plugin_qcard_parser
cd astrbot_plugin_qcard_parser

# 运行测试
python test_parser.py

# 预期输出
============================================================
QQ 卡片解析插件 - 单元测试
============================================================
✅ PASS | 小程序卡片 - 基础解析
✅ PASS | 小程序卡片 - 最小信息
...
✅ PASS | 链接分享卡片 - 最小信息
============================================================
测试结果: 10/10 通过
============================================================
```

### 2. 安装到 AstrBot

有两种方式：

#### 方式 A: 从 GitHub 直接安装（推荐）

```bash
# 在 AstrBot 项目根目录下
git clone https://github.com/NekyuuYa/astrbot_plugin_qcard_parser data/plugins/qcard_parser
```

#### 方式 B: 手动复制文件

```bash
# 1. 创建插件目录
mkdir -p data/plugins/qcard_parser

# 2. 复制文件
cp main.py data/plugins/qcard_parser/
cp metadata.yaml data/plugins/qcard_parser/

# 3. 启动 AstrBot
uv run main.py
```

### 3. 验证安装

启动 AstrBot 后，查看日志：

```
[INFO] QQ Card Parser plugin loaded
```

表示插件已成功加载。

## 📋 文件说明

### `main.py` - 插件核心代码

```python
class CardParser:
    """卡片解析器"""
    @staticmethod
    def parse_miniapp_card(data: dict) -> Optional[str]
    @staticmethod
    def parse_link_share_card(data: dict) -> Optional[str]
    @classmethod
    def parse_json_card(cls, raw_json) -> Optional[str]

class Main(Star):
    """插件主类"""
    def parse_qq_cards(self, event: AstrMessageEvent) -> None
```

**关键点**：
- 继承 `Star` 类，符合 AstrBot 插件规范
- 使用高优先级 (maxsize-2) 拦截消息
- 完整的错误处理和日志记录

### `metadata.yaml` - 插件元数据

```yaml
name: "qcard-parser"              # 插件唯一标识
version: "1.0.0"                  # 插件版本
desc: "QQ 卡片消息解析插件..."      # 描述
author: "NekyuuYa"                # 作者
repo: "https://github.com/..."    # 仓库地址
```

**注**：`name` 字段必须与仓库目录名保持一致或相容。

### `test_parser.py` - 单元测试

包含 10 个测试用例：
- ✅ 小程序卡片基础解析
- ✅ 小程序卡片最小信息
- ✅ 小程序卡片过滤无用字段
- ✅ 链接分享基础解析
- ✅ 链接分享描述截断
- ✅ 链接分享过滤无用字段
- ✅ 未知卡片类型处理
- ✅ 无效 JSON 处理
- ✅ 空数据处理
- ✅ 链接分享最小信息

**运行**：
```bash
python test_parser.py
```

### `requirements.txt` - 依赖列表

当前插件无额外第三方依赖，仅依赖 AstrBot 核心库。

## 🔧 配置和部署

### 无需配置

该插件设计为零配置，启用后即可自动工作。

### 日志级别

要查看更详细的解析日志，修改 AstrBot 的日志配置：

```yaml
# config/config.yaml
log:
  level: "DEBUG"  # 调整为 DEBUG 查看详细日志
```

## 📦 打包发布

### 发布到 PyPI（可选）

1. 编辑 `setup.py`（如果需要）
2. 运行 `python setup.py sdist bdist_wheel`
3. 上传到 PyPI

### GitHub Release

1. 提交和推送代码
2. 创建 Release 标签
3. AstrBot 插件系统会自动识别

## 🧪 开发和测试工作流

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/NekyuuYa/astrbot_plugin_qcard_parser
cd astrbot_plugin_qcard_parser

# 编辑代码
vim main.py

# 运行测试验证
python test_parser.py

# 提交更改
git add .
git commit -m "feat: add support for new card type"
git push origin main
```

### 添加新测试

在 `test_parser.py` 中添加新的测试函数：

```python
def test_new_feature():
    """测试说明"""
    # 测试代码
    result = CardParser.parse_json_card(card_data)
    passed = # 验证逻辑
    print_test("测试名称", passed)
```

## 🎯 版本管理

### 版本号规则

使用 Semantic Versioning: MAJOR.MINOR.PATCH

- **MAJOR**: 不兼容的 API 更改
- **MINOR**: 向后兼容的功能新增
- **PATCH**: 向后兼容的问题修复

### 更新版本

1. 编辑 `metadata.yaml` 中的 `version` 字段
2. 编辑 `main.py` 中的插件说明（可选）
3. 提交和创建 GitHub Release

## 📚 相关文档

- [AstrBot 官方文档](https://docs.astrbot.app/)
- [AstrBot 插件开发指南](https://docs.astrbot.app/dev/star/plugin-new.html)
- [OneBot V11 协议](https://onebot.dev/)

## 🐛 问题排查

### 插件未加载

**症状**：启动时没有 "QQ Card Parser plugin loaded" 消息

**排查步骤**：
1. 检查 metadata.yaml 路径和内容
2. 验证 main.py 语法正确
3. 查看 AstrBot 启动日志中的错误信息
4. 检查插件目录权限

### 卡片未被解析

**症状**：卡片消息未被转换为可读文本

**排查步骤**：
1. 验证卡片类型是否被支持（小程序、链接分享）
2. 启用 DEBUG 日志查看解析过程
3. 检查 JSON 数据格式是否正确

### 性能问题

**症状**：插件导致消息处理变慢

**说明**：
- 插件仅处理 Json 组件，不应有性能问题
- 如有疑问，请提交 Issue

## 📝 贡献指南

欢迎提交：
- 🐛 Bug 报告
- 💡 功能建议
- 🔧 Pull Requests
- 📖 文档改进

### 贡献步骤

1. Fork 仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 📄 许可证

AGPL-3.0 - 参见 [LICENSE](LICENSE) 文件

## 📞 联系方式

- GitHub Issues: [提交 Issue](https://github.com/NekyuuYa/astrbot_plugin_qcard_parser/issues)
- 作者: NekyuuYa

---

**最后更新**: 2026-04-01
**插件版本**: 1.0.0
**状态**: ✅ 生产就绪
