# Contributing to AI-Bridge

首先，感谢你考虑为 AI-Bridge 做出贡献！🎉

## 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议，请通过 [GitHub Issues](https://github.com/Louis830903/AI-Bridge/issues) 提交。

提交前请检查：
- [ ] 问题是否已被报告
- [ ] 使用最新的代码版本测试
- [ ] 提供清晰的复现步骤

### 提交代码

1. **Fork 项目**
   ```bash
   git clone https://github.com/your-username/AI-Bridge.git
   cd AI-Bridge
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

3. **安装开发依赖**
   ```bash
   pip install -e ".[dev]"
   ```

4. **运行测试**
   ```bash
   pytest tests/ -v
   ```

5. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add your feature"
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**

### 代码规范

- 遵循 PEP 8 规范
- 使用类型注解
- 添加文档字符串
- 保持测试覆盖率 >90%

### Commit 规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具相关
```

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/Louis830903/AI-Bridge.git
cd AI-Bridge

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/

# 代码格式化
black src/ tests/
ruff check src/ tests/

# 类型检查
mypy src/
```

### 添加新适配器

如果你想添加对新平台的支持：

1. 在 `src/aibridge/adapters/` 下创建新目录
2. 继承 `BaseAdapter` 类
3. 实现必需的方法：`connect`, `disconnect`, `execute`
4. 添加测试用例
5. 更新文档

示例：

```python
from aibridge.adapters.base import BaseAdapter, AdapterInfo, AdapterType

class MyAdapter(BaseAdapter):
    info = AdapterInfo(
        id="myplatform",
        name="My Platform",
        type=AdapterType.IM,
        actions=["send_message", "read_message"]
    )
    
    async def connect(self) -> bool:
        # 实现连接逻辑
        pass
    
    async def disconnect(self) -> bool:
        # 实现断开逻辑
        pass
    
    async def execute(self, action, target=None, value=None, options=None):
        # 实现执行逻辑
        pass
```

## 社区

- 💬 [GitHub Discussions](https://github.com/Louis830903/AI-Bridge/discussions)
- 🐦 Twitter: [@AI_Bridge](https://twitter.com/AI_Bridge)
- 📧 Email: contact@ai-bridge.dev

## 许可证

通过提交代码，你同意你的贡献将在 [Apache License 2.0](LICENSE) 下发布。

---

再次感谢你的贡献！🚀
