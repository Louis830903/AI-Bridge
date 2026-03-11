"""IM adapters module."""

# China IM platforms
from aibridge.adapters.im.feishu import FeishuAdapter
from aibridge.adapters.im.dingtalk import DingtalkAdapter
from aibridge.adapters.im.wecom import WecomAdapter

# Global IM platforms - Enterprise
from aibridge.adapters.im.slack import SlackAdapter
from aibridge.adapters.im.teams import TeamsAdapter
from aibridge.adapters.im.discord import DiscordAdapter
from aibridge.adapters.im.google_chat import GoogleChatAdapter

# Global IM platforms - Consumer
from aibridge.adapters.im.telegram import TelegramAdapter
from aibridge.adapters.im.whatsapp import WhatsAppAdapter
from aibridge.adapters.im.messenger import MessengerAdapter
from aibridge.adapters.im.line import LINEAdapter
from aibridge.adapters.im.viber import ViberAdapter
from aibridge.adapters.im.kakaotalk import KakaoTalkAdapter

__all__ = [
    # China
    "FeishuAdapter",
    "DingtalkAdapter", 
    "WecomAdapter",
    # Global - Enterprise
    "SlackAdapter",
    "TeamsAdapter",
    "DiscordAdapter",
    "GoogleChatAdapter",
    # Global - Consumer
    "TelegramAdapter",
    "WhatsAppAdapter",
    "MessengerAdapter",
    "LINEAdapter",
    "ViberAdapter",
    "KakaoTalkAdapter",
]
