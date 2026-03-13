.PHONY: help install install-security test security audit bandit safety semgrep clean

help:
	@echo "AI-Bridge Security Tools"
	@echo "========================"
	@echo ""
	@echo "Available targets:"
	@echo "  make install         - Install project dependencies"
	@echo "  make install-security - Install security tools"
	@echo "  make test            - Run tests"
	@echo "  make security        - Run all security checks"
	@echo "  make audit           - Run custom security auditor"
	@echo "  make bandit          - Run Bandit security scan"
	@echo "  make safety          - Run Safety dependency check"
	@echo "  make semgrep         - Run Semgrep analysis"
	@echo "  make precommit       - Install and run pre-commit hooks"
	@echo "  make clean           - Clean generated files"

install:
	pip install -e ".[dev]"

install-security:
	pip install bandit safety semgrep pre-commit

test:
	pytest tests/ -v

security: audit bandit safety semgrep
	@echo ""
	@echo "✅ All security checks completed"
	@echo "📄 Check generated reports for details"

audit:
	@echo "🔍 Running custom security auditor..."
	python tools/security_auditor.py

bandit:
	@echo "🔍 Running Bandit security scan..."
	bandit -r src/ -f json -o bandit-report.json || true
	bandit -r src/ -ll

safety:
	@echo "🔍 Running Safety dependency check..."
	safety check --json -o safety-report.json || true
	safety check

semgrep:
	@echo "🔍 Running Semgrep analysis..."
	semgrep --config=p/python --config=p/owasp-top-ten src/ --sarif -o semgrep-report.sarif || true

precommit:
	pre-commit install
	pre-commit run --all-files

clean:
	rm -f bandit-report.json
	rm -f safety-report.json
	rm -f semgrep-report.sarif
	rm -f ai-bridge-security-report.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
