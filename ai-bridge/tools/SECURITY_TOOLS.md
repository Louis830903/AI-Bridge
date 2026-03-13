# AI-Bridge 安全工具包

完整的代码安全扫描和漏洞检测工具集

## 快速开始

```bash
# 安装安全工具
pip install bandit safety semgrep

# 运行完整安全扫描
python tools/security_auditor.py

# 运行 bandit 扫描
bandit -r src/ -f json -o security-report.json

# 检查依赖漏洞
safety check
```

## 工具清单

### 1. 内置审计工具

**文件**: `tools/security_auditor.py`

自定义安全审计工具，检查：
- JS 注入漏洞
- SQL 注入
- 命令注入
- 路径遍历
- 硬编码密钥
- 不安全的反序列化
- 弱加密算法
- 资源泄漏
- 无限循环
- 异常吞没
- 缺少超时

**使用**:
```bash
python tools/security_auditor.py
```

### 2. Bandit - Python 安全扫描

**安装**:
```bash
pip install bandit
```

**使用**:
```bash
# 基础扫描
bandit -r src/

# 详细报告
bandit -r src/ -f json -o bandit-report.json

# 只显示高危问题
bandit -r src/ -ll
```

### 3. Safety - 依赖漏洞检查

**安装**:
```bash
pip install safety
```

**使用**:
```bash
# 检查当前环境
safety check

# 检查 requirements.txt
safety check -r requirements.txt

# 生成 JSON 报告
safety check --json -o safety-report.json
```

### 4. Semgrep - 静态分析

**安装**:
```bash
pip install semgrep
```

**使用**:
```bash
# 使用默认规则集
semgrep --config=auto src/

# 使用 Python 安全规则
semgrep --config=p/python src/

# 使用 OWASP 规则
semgrep --config=p/owasp-top-ten src/

# 生成 SARIF 报告
semgrep --config=auto src/ --sarif -o semgrep-report.sarif
```

### 5. Pylint - 代码质量

**安装**:
```bash
pip install pylint
```

**使用**:
```bash
pylint src/ --output-format=json:pylint-report.json
```

## CI/CD 集成

在 `.github/workflows/security.yml` 中添加：

```yaml
name: Security Audit

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    # 每天凌晨2点运行
    - cron: '0 2 * * *'

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install bandit safety semgrep
        pip install -e ".[dev]"
    
    - name: Run custom security auditor
      run: |
        python tools/security_auditor.py
      continue-on-error: true
    
    - name: Run Bandit
      run: |
        bandit -r src/ -f json -o bandit-report.json || true
    
    - name: Run Safety
      run: |
        safety check --json -o safety-report.json || true
    
    - name: Run Semgrep
      run: |
        semgrep --config=p/python --config=p/owasp-top-ten src/ --sarif -o semgrep-report.sarif || true
    
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json
          semgrep-report.sarif
          ai-bridge-security-report.json
```

## 预提交钩子

安装 pre-commit:

```bash
pip install pre-commit
```

创建 `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-r', 'src/', '-ll']
  
  - repo: local
    hooks:
      - id: security-auditor
        name: Security Auditor
        entry: python tools/security_auditor.py
        language: system
        pass_filenames: false
        always_run: true
```

安装钩子:
```bash
pre-commit install
```

## 安全配置建议

### 1. 代码审查 checklist

- [ ] 所有用户输入都经过验证/转义
- [ ] 没有使用 eval() 或 exec()
- [ ] 没有硬编码密钥/密码
- [ ] 所有网络请求都有超时
- [ ] 文件操作使用 with 语句
- [ ] 异常处理具体化（不用裸 except）
- [ ] 循环有退出条件

### 2. 定期审计计划

| 频率 | 任务 | 工具 |
|------|------|------|
| 每次提交 | 基础安全扫描 | pre-commit + bandit |
| 每周 | 完整安全审计 | security_auditor.py |
| 每月 | 依赖漏洞检查 | safety |
| 每季度 | 深度代码审计 | semgrep + 人工审查 |

### 3. 安全响应流程

1. **发现问题** → 创建安全 Issue（标记 `security` 标签）
2. **评估风险** → P0/P1/P2 分级
3. **修复问题** → 创建 PR，链接到 Issue
4. **审查验证** → 安全负责人审查
5. **发布更新** → 发布安全公告，更新版本

## 报告格式

安全审计报告包含：

```json
{
  "audit_time": "2024-03-13T14:30:00",
  "repo_path": "/path/to/repo",
  "total_issues": 5,
  "issues": [
    {
      "level": "P0",
      "category": "JS Injection",
      "file": "src/adapters/browser/chrome.py",
      "line": 259,
      "code": "await self._page.evaluate(f'...')",
      "description": "存在 JS 注入风险",
      "fix_suggestion": "使用参数化 API 或转义输入",
      "cwe_id": "CWE-79"
    }
  ]
}
```

## 参考资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE 漏洞列表](https://cwe.mitre.org/)
- [Bandit 文档](https://bandit.readthedocs.io/)
- [Semgrep 规则库](https://semgrep.dev/explore)

---

**记住**: 安全是持续的过程，不是一次性的检查！
