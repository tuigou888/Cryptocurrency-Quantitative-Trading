import requests
from config.settings import settings
from utils.logger import logger


class Notifier:
    def __init__(self):
        notif_config = settings.notification
        self.enabled = notif_config.get("enabled", False)
        self._telegram_config = notif_config.get("telegram", {})

    def send(self, message: str, level: str = "info"):
        logger.log(
            {"info": 20, "warning": 30, "error": 40, "critical": 50}.get(level, 20),
            f"[NOTIFY] {message}",
        )

        if not self.enabled:
            return

        self._send_telegram(message)

    def _send_telegram(self, message: str):
        token = self._telegram_config.get("bot_token", "")
        chat_id = self._telegram_config.get("chat_id", "")

        if not token or not chat_id:
            logger.debug("Telegram not configured, skipping notification")
            return

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.debug("Telegram notification sent")
            else:
                logger.warning(f"Telegram notification failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"Telegram notification error: {e}")

    def notify_trade(self, side: str, symbol: str, amount: float, price: float, pnl: float = None):
        emoji = "🟢" if side == "buy" else "🔴"
        msg = f"{emoji} <b>Trade Executed</b>\n"
        msg += f"Side: {side.upper()}\n"
        msg += f"Symbol: {symbol}\n"
        msg += f"Amount: {amount}\n"
        msg += f"Price: {price:.2f}\n"
        if pnl is not None:
            msg += f"PnL: {pnl:.2f}\n"
        self.send(msg)

    def notify_risk_alert(self, reason: str, level: str = "warning"):
        emoji = "⚠️" if level == "warning" else "🚨"
        msg = f"{emoji} <b>Risk Alert</b>\n{reason}"
        self.send(msg, level=level)

    def notify_strategy_signal(self, strategy_name: str, signal_type: str, symbol: str, reason: str):
        emoji = "📊"
        msg = f"{emoji} <b>Strategy Signal</b>\n"
        msg += f"Strategy: {strategy_name}\n"
        msg += f"Signal: {signal_type}\n"
        msg += f"Symbol: {symbol}\n"
        msg += f"Reason: {reason}"
        self.send(msg)
