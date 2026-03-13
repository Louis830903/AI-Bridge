# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- TBD

## [2.6.1] - 2026-03-13

### Added
- Shared LLM Architecture - AI-Bridge can now share LLM resources with the host AI agent
- LLMProvider abstract interface supporting OpenAI, Claude, and local models
- Automatic fallback to rule-based mode when LLM is unavailable

### Fixed
- Target object conversion in ChromeAdapter (now supports both dict and Target objects)
- A11y snapshot element caching issue

## [2.6.0] - 2026-03-12

### Added
- Session Management (SessionManager) - Persistent browser sessions
- Smart Wait/Retry (SmartWait) - Intelligent waiting and retry logic
- Batch Parallel Operations (BatchExecutor) - Execute multiple actions in parallel
- Multi-modal Input/Output (MultiModal) - Support for images, audio, and text
- Security Sandbox (SecurityPolicy) - Permission control and sandboxing
- Intent Recognition Engine - Natural language to action mapping
- O-R-A Loop Orchestrator - Observe-Reason-Action task planning

## [2.5.0] - 2026-03-12

### Added
- MCP Server support - Compatible with Model Context Protocol
- Browser automation task engine
- Universal nurture engine with 15+ platforms semantic matching
- Price tracking automation
- Auto check-in functionality
- Multi-platform publish capability
- Auto-play courses feature

## [2.4.0] - 2026-03-12

### Added
- `extract` action for structured data extraction from web pages
- Support for custom schema extraction
- `multiple` parameter for batch data extraction
- Unified response format: `{success, action, data, summary, metadata}`

## [2.3.2] - 2026-03-12

### Fixed
- `_format_snapshot` recursion issue
- A11y snapshot type safety

## [2.3.1] - 2026-03-12

### Added
- `force` parameter support for hidden element operations
- Fixed A11y snapshot type safety issues

## [2.3.0] - 2026-03-12

### Added
- Multi-strategy element location fallback
- A11y snapshot DOM fallback
- JS execution return value handling
- Baidu search box input/click working with `force=True`
- A11y snapshot returning 32+ elements with UID markers

### Performance
- 3-site navigation in 2.36 seconds (benchmark)

## [2.2.1] - 2026-03-11

### Added
- Base adapter implementation
- ChromeAdapter with Playwright
- Core protocol definitions (Action, Target, Request, Response)
- AdapterManager for unified management
- Initial test suite

---

## Release Notes Format

### Added - New features
### Changed - Changes in existing functionality
### Deprecated - Soon-to-be removed features
### Removed - Now removed features
### Fixed - Bug fixes
### Security - Security improvements
