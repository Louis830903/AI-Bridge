"""AI-Bridge CLI entry point

Uses unified adapter configuration system (dataclass-based)
"""

import asyncio
import argparse
import sys
from aibridge.version import __version__
from aibridge.core.server import AIBridgeServer
from aibridge.core.manager import AdapterManager
from aibridge.core.config import load_config
from aibridge.core.logger import setup_logging, get_logger

# Unified configuration system
from aibridge.core.adapter_config import (
    ChromeConfig, EdgeConfig,
    FeishuConfig, DingtalkConfig, WecomConfig,
    SlackConfig, TeamsConfig, DiscordConfig, GoogleChatConfig,
    TelegramConfig, WhatsAppConfig, MessengerConfig,
    LINEConfig, ViberConfig, KakaoTalkConfig,
    OfficeConfig, WPSConfig, DesktopConfig,
    create_config,
)

# Import all adapters
from aibridge.adapters.browser import ChromeAdapter, EdgeAdapter
from aibridge.adapters.im import (
    # China IM
    FeishuAdapter, DingtalkAdapter, WecomAdapter,
    # Global IM - Enterprise
    SlackAdapter, TeamsAdapter, DiscordAdapter, GoogleChatAdapter,
    # Global IM - Consumer
    TelegramAdapter, WhatsAppAdapter, MessengerAdapter,
    LINEAdapter, ViberAdapter, KakaoTalkAdapter,
)
from aibridge.adapters.office import WordAdapter, ExcelAdapter, PowerPointAdapter
from aibridge.adapters.office import WPSWriterAdapter, WPSSpreadsheetAdapter
from aibridge.adapters.desktop import GenericDesktopAdapter


logger = get_logger("main")


# Adapter registry: maps adapter_id to (AdapterClass, ConfigClass, is_sync)
ADAPTER_REGISTRY = {
    # Browser adapters (async)
    "chrome": (ChromeAdapter, ChromeConfig, False),
    "edge": (EdgeAdapter, EdgeConfig, False),
    # China IM adapters (async)
    "feishu": (FeishuAdapter, FeishuConfig, False),
    "dingtalk": (DingtalkAdapter, DingtalkConfig, False),
    "wecom": (WecomAdapter, WecomConfig, False),
    # Global IM - Enterprise (async)
    "slack": (SlackAdapter, SlackConfig, False),
    "teams": (TeamsAdapter, TeamsConfig, False),
    "discord": (DiscordAdapter, DiscordConfig, False),
    "google_chat": (GoogleChatAdapter, GoogleChatConfig, False),
    # Global IM - Consumer (async)
    "telegram": (TelegramAdapter, TelegramConfig, False),
    "whatsapp": (WhatsAppAdapter, WhatsAppConfig, False),
    "messenger": (MessengerAdapter, MessengerConfig, False),
    "line": (LINEAdapter, LINEConfig, False),
    "viber": (ViberAdapter, ViberConfig, False),
    "kakaotalk": (KakaoTalkAdapter, KakaoTalkConfig, False),
    # Desktop adapter (sync)
    "desktop": (GenericDesktopAdapter, DesktopConfig, True),
}

# Office adapters (grouped, all sync)
OFFICE_ADAPTERS = {
    "office": [
        (WordAdapter, OfficeConfig),
        (ExcelAdapter, OfficeConfig),
        (PowerPointAdapter, OfficeConfig),
    ],
    "wps": [
        (WPSWriterAdapter, WPSConfig),
        (WPSSpreadsheetAdapter, WPSConfig),
    ],
}


def create_server_with_adapters(config) -> AIBridgeServer:
    """
    Create server with configured adapters.
    
    Uses unified dataclass-based configuration system for type safety.
    """
    manager = AdapterManager()
    
    # Register standard adapters from registry
    for adapter_id, (adapter_class, config_class, is_sync) in ADAPTER_REGISTRY.items():
        if config.is_adapter_enabled(adapter_id):
            # Get raw config dict and convert to typed dataclass
            raw_config = config.get_adapter_config(adapter_id)
            typed_config = config_class.from_dict(raw_config) if isinstance(raw_config, dict) else raw_config
            
            adapter = adapter_class(typed_config)
            
            if is_sync:
                manager.register_sync(adapter)
            else:
                manager.register(adapter)
            
            logger.debug(f"Registered adapter: {adapter_id}")
    
    # Register grouped Office adapters
    for group_id, adapters in OFFICE_ADAPTERS.items():
        if config.is_adapter_enabled(group_id):
            raw_config = config.get_adapter_config(group_id)
            
            for adapter_class, config_class in adapters:
                typed_config = config_class.from_dict(raw_config) if isinstance(raw_config, dict) else raw_config
                manager.register_sync(adapter_class(typed_config))
            
            logger.debug(f"Registered {group_id} adapters")
    
    return AIBridgeServer(manager, config)


async def run_server(config):
    """Run the MCP server."""
    server = create_server_with_adapters(config)
    
    logger.info(f"AI-Bridge v{__version__} starting...")
    logger.info(f"Registered adapters: {server.manager.list_adapter_ids()}")
    
    await server.run_stdio()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI-Bridge: Bridge AI Assistants to GUI Applications"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"AI-Bridge {__version__}"
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to configuration file",
        default=None
    )
    parser.add_argument(
        "--log-level",
        help="Log level (DEBUG, INFO, WARNING, ERROR)",
        default="INFO"
    )
    parser.add_argument(
        "--list-adapters",
        action="store_true",
        help="List all available adapters and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Load configuration
    config = load_config(args.config)
    
    # Override log level from config if not specified in args
    if args.log_level == "INFO":
        setup_logging(level=config.server.log_level)
    
    # List adapters mode
    if args.list_adapters:
        server = create_server_with_adapters(config)
        adapters = server.manager.list_adapters()
        print("Available adapters:")
        for adapter in adapters:
            print(f"  - {adapter['id']}: {adapter['name']} ({adapter['type']})")
            print(f"    Actions: {', '.join(adapter['actions'][:5])}...")
        return 0
    
    # Run server
    try:
        asyncio.run(run_server(config))
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
