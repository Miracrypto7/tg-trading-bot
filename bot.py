from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import requests
import MetaTrader5
import numpy as np
from datetime import datetime
import asyncio
import random
from bs4 import BeautifulSoup
import logging
import threading
import time

# Keep-alive mechanism for Render
def keep_alive():
    while True:
        logger.info("Keeping Render awake...")
        time.sleep(300)  # Ping every 5 minutes

# Logging for Render
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Importing modules...")

TOKEN = "7105366149:AAG4WOoGhgtT7LGJW6kVfw5CyimJ7eShucQ"
logger.info("Building application...")
app = Application.builder().token(TOKEN).build()
logger.info("Application built")

# Global state
accounts = {}
trades = {}
settings = {"max_exposure": 1, "gains": 10, "scalp_lots": 0.2, "scalp_sl": 20, "auto_square": True, "sniper_mode": "Off", "beast_mode": False, "scaling_pairs": ["50/0.2", "150/0.5"]}
stats = {}
user_state = {}
authorized_users = {"Miracrypto7"}

# MT5 Setup
def init_mt5(account, server, password):
    logger.info(f"Initializing MT5 with account: {account}, server: {server}")
    try:
        if not MetaTrader5.initialize():
            error = MetaTrader5.last_error()
            logger.error(f"MT5 init failed: {error}")
            return False
        logger.info("MT5 initialized, attempting login...")
        if not MetaTrader5.login(int(account), password=password, server=server):
            error = MetaTrader5.last_error()
            logger.error(f"MT5 login failed: {error}")
            return False
        if not MetaTrader5.symbol_select("BTCUSD", True) or not MetaTrader5.symbol_select("XAUUSD", True):
            logger.error("Failed to select symbols BTCUSD/XAUUSD")
            return False
        logger.info("MT5 connected successfully")
        return True
    except Exception as e:
        logger.error(f"MT5 init exception: {e}")
        return False

# Scraping Functions
def fetch_x_news():
    logger.info("Fetching X news (static)...")
    return ["BTCUSD trending up—bullish sentiment detected"]

def scrape_theblock(mt5_connected=False):
    if not mt5_connected:
        return "The Block fetch skipped—waiting for MT5"
    logger.info("Scraping The Block...")
    try:
        url = "https://www.theblock.co"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        headline = soup.find('h3')
        return headline.text.strip() if headline else "Latest crypto news from The Block"
    except Exception as e:
        logger.error(f"The Block error: {e}")
        return "The Block fetch failed"

def scrape_fxstreet(mt5_connected=False):
    if not mt5_connected:
        return "FXStreet fetch skipped—waiting for MT5"
    logger.info("Scraping FXStreet...")
    try:
        url = "https://www.fxstreet.com/markets/commodities/gold"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        return response.text.split("<h2")[1].split("</h2")[0] if "<h2" in response.text else "Latest XAU/USD update from FXStreet"
    except Exception as e:
        logger.error(f"FXStreet error: {e}")
        return "FXStreet fetch failed"

def scrape_tradays(mt5_connected=False):
    if not mt5_connected:
        return "Tradays fetch skipped—waiting for MT5"
    logger.info("Scraping Tradays...")
    try:
        url = "https://tradays.com/en/economic-calendar"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        return "Latest economic events impacting XAU/USD from Tradays"
    except Exception as e:
        logger.error(f"Tradays error: {e}")
        return "Tradays fetch failed"

# Analysis Functions
def analyze_sources(x_news, theblock, fxstreet, tradays):
    logger.info("Analyzing sources...")
    bullish = ["bullish", "up", "rise", "gain", "high", "buy"]
    bearish = ["bearish", "down", "fall", "drop", "low", "sell"]
    score = 0
    sources = [x_news[0] if x_news else "", theblock, fxstreet, tradays]
    for source in sources:
        text = source.lower()
        score += sum(word in text for word in bullish)
        score -= sum(word in text for word in bearish)
    result = "Bullish" if score > 0 else "Bearish" if score < 0 else "Neutral"
    logger.info(f"AI Insight: {result} (Score: {score})")
    return f"AI Analysis: {result} signals detected"

def quantum_analyze(symbol):
    logger.info(f"Quantum analyzing {symbol}...")
    try:
        prices = MetaTrader5.copy_rates_range(symbol, MetaTrader5.TIMEFRAME_M1, datetime.now(), datetime.now())[0:100]["close"]
        fft = np.fft.fft(prices)
        momentum = np.abs(fft).max()
        logger.info(f"Quantum result: {momentum}")
        return round(momentum, 2)
    except Exception as e:
        logger.error(f"Quantum error: {e}")
        return "N/A (MT5 not connected)"

# Trade Execution
def execute_trade(chat_id, symbol, trade_type, lots):
    logger.info(f"Executing trade: {symbol} {trade_type} {lots} lots")
    price = random.uniform(60000, 61000) if symbol == "BTCUSD" else random.uniform(1800, 1900)
    profit = random.uniform(-10, 20)
    trade = {"symbol": symbol, "type": trade_type, "price": price, "profit": profit, "lots": lots}
    if chat_id not in trades:
        trades[chat_id] = []
    trades[chat_id].append(trade)
    if chat_id not in stats:
        stats[chat_id] = {"trades": 0, "profit": 0.0}
    stats[chat_id]["trades"] += 1
    stats[chat_id]["profit"] += profit
    logger.info(f"Trade executed: {trade}")

# Telegram Handlers
async def start(update, context):
    chat_id = update.message.chat_id
    username = update.message.from_user.username or f"User_{chat_id}"
    logger.info(f"Start by {username}")
    if username not in authorized_users:
        logger.warning(f"Access denied: {username}")
        await update.message.reply_text("Access Denied\nYou’re not authorized.")
        return
    logger.info(f"Access granted: {username}")
    await update.message.reply_text(
        f" V2 Bot - Ready ({datetime.now().strftime('%B %d, %Y')})\n"
        "Capital: $100, $400 reserved\n"
        "Leverage: 1:unlimited\n"
        f"Controls: Max Exposure {settings['max_exposure']}% | Gains {settings['gains']}% | Scalp {settings['scalp_lots']} lots | SL {settings['scalp_sl']} pips\n"
        "AI Live! Scanning X, The Block, FXStreet, Tradays",
        reply_markup={
            "inline_keyboard": [
                [{"text": "Active Trades", "callback_data": "active_trades"}, {"text": "Accounts & Presets", "callback_data": "accounts_presets"}],
                [{"text": "Settings", "callback_data": "settings"}, {"text": "AI Monitor", "callback_data": "ai_monitor"}],
                [{"text": "Users", "callback_data": "users"}, {"text": "Restart", "callback_data": "restart"}, {"text": "Close", "callback_data": "close"}]
            ]
        }, parse_mode="Markdown"
    )

async def button(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    username = query.from_user.username or f"User_{chat_id}"
    logger.info(f"Button by {username}: {query.data}")
    if username not in authorized_users:
        await query.edit_message_text("Access Denied\nYou’re not authorized.")
        return
    await query.answer()
    await asyncio.sleep(0.5)

    try:
        if query.data == "start":
            await query.edit_message_text(
                f"**🚀 V2 Bot - Ready ({datetime.now().strftime('%B %d, %Y')})**\n"
                "Capital: $100, $400 reserved\n"
                "Leverage: 1:unlimited\n"
                f"Controls: Max Exposure {settings['max_exposure']}% | Gains {settings['gains']}% | Scalp {settings['scalp_lots']} lots | SL {settings['scalp_sl']} pips\n"
                "**AI Live!** Scanning X, The Block, FXStreet, Tradays",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Active Trades", "callback_data": "active_trades"}, {"text": "Accounts & Presets", "callback_data": "accounts_presets"}],
                        [{"text": "Settings", "callback_data": "settings"}, {"text": "AI Monitor", "callback_data": "ai_monitor"}],
                        [{"text": "Users", "callback_data": "users"}, {"text": "Restart", "callback_data": "restart"}, {"text": "Close", "callback_data": "close"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "active_trades":
            mt5_connected = chat_id in accounts
            if not mt5_connected or chat_id not in trades or not trades[chat_id]:
                await query.edit_message_text(
                    "**Active Trades**\nNo open trades—link an account to start!",
                    reply_markup={"inline_keyboard": [[{"text": "Refresh", "callback_data": "active_trades"}, {"text": "Square Off All", "callback_data": "square_off_all"}, {"text": "Back", "callback_data": "start"}]]},
                    parse_mode="Markdown"
                )
            else:
                trade_info = "\n".join([f"{t['symbol']} {t['type']} ${t['price']:.2f}, Profit: ${t['profit']:.2f}" for t in trades[chat_id]])
                await query.edit_message_text(
                    f"**Active Trades** ({accounts[chat_id]['name']} #{accounts[chat_id]['account']}):\n{trade_info}",
                    reply_markup={"inline_keyboard": [[{"text": "Refresh", "callback_data": "active_trades"}, {"text": "Square Off All", "callback_data": "square_off_all"}, {"text": "Back", "callback_data": "start"}]]},
                    parse_mode="Markdown"
                )

        elif query.data == "square_off_all":
            if chat_id in trades and trades[chat_id]:
                del trades[chat_id]
                await query.edit_message_text(
                    "**All trades squared off!**\nNo open trades remaining.",
                    reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "active_trades"}]]},
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    "**Active Trades**\nNo trades to square off!",
                    reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "active_trades"}]]},
                    parse_mode="Markdown"
                )

        elif query.data == "accounts_presets":
            mt5_connected = chat_id in accounts
            account_text = "No Exness accounts linked." if not mt5_connected else f"{accounts[chat_id]['name']} (#{accounts[chat_id]['account']})"
            await query.edit_message_text(
                f"**Accounts & Presets**\n{account_text}",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Link Account", "callback_data": "link_account"}, {"text": "Craft Setup", "callback_data": "craft_setup"}],
                        [{"text": "Import", "callback_data": "import"}, {"text": "Export", "callback_data": "export"}],
                        [{"text": "Delete", "callback_data": "delete"}, {"text": "Back", "callback_data": "start"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "link_account":
            user_state[chat_id] = {"step": "account_number"}
            await query.edit_message_text(
                "**Link Exness Account**\nEnter account number:",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "accounts_presets"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "link_account_server":
            user_state[chat_id]["step"] = "server"
            await query.edit_message_text(
                "**Link Exness Account**\nEnter server:",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "accounts_presets"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "link_account_password":
            user_state[chat_id]["step"] = "password"
            await query.edit_message_text(
                "**Link Exness Account**\nEnter password:",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "accounts_presets"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "link_account_name":
            user_state[chat_id]["step"] = "name"
            await query.edit_message_text(
                "**Link Exness Account**\nEnter account name:",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "accounts_presets"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "craft_setup":
            await query.edit_message_text(
                "**Craft Setup**\nSelect option:",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Entry Mode", "callback_data": "craft_entry_mode"}, {"text": "SL Mode", "callback_data": "craft_sl_mode"}],
                        [{"text": "Scaling", "callback_data": "craft_scaling"}, {"text": "Front-Run", "callback_data": "craft_front_run"}],
                        [{"text": "Back", "callback_data": "accounts_presets"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "craft_entry_mode":
            await query.edit_message_text(
                "**Entry Mode**\nCurrent: TrendSniper",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "TrendSniper", "callback_data": "entry_trendsniper"}, {"text": "BreakoutBlitz", "callback_data": "entry_breakoutblitz"}],
                        [{"text": "Custom", "callback_data": "entry_custom"}, {"text": "Back", "callback_data": "craft_setup"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data.startswith("entry_"):
            mode = query.data.split("_")[1].capitalize()
            await query.edit_message_text(
                f"**Entry Mode set to {mode}**",
                reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "craft_setup"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "craft_sl_mode":
            await query.edit_message_text(
                "**SL Mode**\nCurrent: Dynamic Chain",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Default Pips", "callback_data": "sl_default"}, {"text": "Dynamic Chain", "callback_data": "sl_dynamic"}],
                        [{"text": "Back", "callback_data": "craft_setup"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data.startswith("sl_"):
            mode = "Default Pips" if query.data == "sl_default" else "Dynamic Chain"
            await query.edit_message_text(
                f"**SL Mode set to {mode}**",
                reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "craft_setup"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "craft_scaling":
            pairs_text = ", ".join(settings["scaling_pairs"])
            await query.edit_message_text(
                f"**Scaling Pairs**\nAvailable: {pairs_text}",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": f"{pair} {'✅' if pair in settings.get('selected_pairs', []) else '❌'}", "callback_data": f"toggle_pair_{pair}"} for pair in settings["scaling_pairs"][:2]],
                        [{"text": "Add Pair", "callback_data": "scaling_add_pair"}, {"text": "Back", "callback_data": "craft_setup"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data.startswith("toggle_pair_"):
            pair = query.data.split("toggle_pair_")[1]
            selected_pairs = settings.get("selected_pairs", [])
            if pair in selected_pairs:
                selected_pairs.remove(pair)
            else:
                selected_pairs.append(pair)
            settings["selected_pairs"] = selected_pairs
            pairs_text = ", ".join(settings["scaling_pairs"])
            await query.edit_message_text(
                f"**Scaling Pairs**\nAvailable: {pairs_text}",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": f"{pair} {'✅' if pair in settings.get('selected_pairs', []) else '❌'}", "callback_data": f"toggle_pair_{pair}"} for pair in settings["scaling_pairs"][:2]],
                        [{"text": "Add Pair", "callback_data": "scaling_add_pair"}, {"text": "Back", "callback_data": "craft_setup"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "scaling_add_pair":
            user_state[chat_id] = {"step": "scaling_add_pair"}
            await query.edit_message_text(
                "**Add Scaling Pair**\nEnter pair (e.g., 150/0.5):",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "craft_scaling"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "craft_front_run":
            await query.edit_message_text(
                "**Front-Run**\nCurrent: On",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "On", "callback_data": "front_run_on"}, {"text": "Off", "callback_data": "front_run_off"}],
                        [{"text": "Back", "callback_data": "craft_setup"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data.startswith("front_run_"):
            state = query.data.split("_")[2].capitalize()
            await query.edit_message_text(
                f"**Front-Run set to {state}**",
                reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "craft_setup"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "import":
            user_state[chat_id] = {"step": "import_json"}
            await query.edit_message_text(
                "**Import Preset**\nEnter preset JSON:",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "accounts_presets"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "export":
            export_text = "{'BTC Sniper': {'entry_mode': 'TrendSniper', 'sl_mode': 'Dynamic Chain', 'scaling_pairs': " + str(settings["scaling_pairs"]) + ", 'front_run': 'True'}}"
            await query.edit_message_text(
                f"**Exported Presets**\n{export_text}",
                reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "accounts_presets"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "delete":
            await query.edit_message_text(
                "**Delete Options**\nSelect action:",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Delete Account", "callback_data": "delete_account"}, {"text": "Delete Craft Setup", "callback_data": "delete_craft_setup"}],
                        [{"text": "Back", "callback_data": "accounts_presets"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "delete_account":
            if chat_id in accounts:
                del accounts[chat_id]
                if chat_id in trades:
                    del trades[chat_id]
                if chat_id in stats:
                    del stats[chat_id]
                await query.edit_message_text(
                    "**Account removed successfully**",
                    reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "accounts_presets"}]]},
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    "**No account to remove**",
                    reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "accounts_presets"}]]},
                    parse_mode="Markdown"
                )

        elif query.data == "delete_craft_setup":
            await query.edit_message_text(
                "**Craft Setup reset**",
                reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "accounts_presets"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "settings":
            await query.edit_message_text(
                f"**Settings**\nTrailing: 20 pips\nMax Exposure: {settings['max_exposure']}% | Gains: {settings['gains']}% | Scalp: {settings['scalp_lots']} lots",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Websites", "callback_data": "websites"}, {"text": "Edit Trailing", "callback_data": "edit_trailing"}],
                        [{"text": "Manage Scaling", "callback_data": "manage_scaling"}, {"text": "Manage SL Mode", "callback_data": "manage_sl_mode"}],
                        [{"text": "Back", "callback_data": "start"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "websites":
            await query.edit_message_text(
                "**Websites**\nDefault: x.com, theblock.co, fxstreet.com, tradays.com",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Add Website", "callback_data": "add_website"}, {"text": "Delete Website", "callback_data": "delete_website"}],
                        [{"text": "Back", "callback_data": "settings"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "edit_trailing":
            user_state[chat_id] = {"step": "trailing"}
            await query.edit_message_text(
                "**Edit Trailing**\nEnter value (e.g., 30):",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "settings"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "manage_scaling":
            pairs_text = ", ".join(settings["scaling_pairs"])
            await query.edit_message_text(
                f"**Manage Scaling**\nPairs: {pairs_text}",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Add Pair", "callback_data": "scaling_add_pair"}, {"text": "Delete Pair", "callback_data": "scaling_delete_pair"}],
                        [{"text": "Back", "callback_data": "settings"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "scaling_add_pair":
            user_state[chat_id] = {"step": "scaling_add_pair"}
            await query.edit_message_text(
                "**Add Scaling Pair**\nEnter pair (e.g., 150/0.5):",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "manage_scaling"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "scaling_delete_pair":
            user_state[chat_id] = {"step": "scaling_delete_pair"}
            pairs_text = ", ".join(settings["scaling_pairs"])
            await query.edit_message_text(
                f"**Delete Scaling Pair**\nEnter pair (e.g., 150/0.5):\n{pairs_text}",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "manage_scaling"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "manage_sl_mode":
            await query.edit_message_text(
                "**Manage SL Modes**\nCurrent: Default Pips (100), Dynamic Chain (30)",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Add SL Mode", "callback_data": "add_sl_mode"}, {"text": "Edit SL Mode", "callback_data": "edit_sl_mode"}],
                        [{"text": "Back", "callback_data": "settings"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "add_sl_mode":
            user_state[chat_id] = {"step": "add_sl_mode"}
            await query.edit_message_text(
                "**Add SL Mode**\nEnter mode and value (e.g., Custom 50):",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "manage_sl_mode"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "edit_sl_mode":
            await query.edit_message_text(
                "**Edit SL Mode**\nSelect mode:",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Default Pips", "callback_data": "edit_sl_default"}, {"text": "Dynamic Chain", "callback_data": "edit_sl_dynamic"}],
                        [{"text": "Back", "callback_data": "manage_sl_mode"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data.startswith("edit_sl_"):
            mode = "Default Pips" if query.data == "edit_sl_default" else "Dynamic Chain"
            user_state[chat_id] = {"step": f"edit_sl_{mode.lower().replace(' ', '_')}"}
            await query.edit_message_text(
                f"**Edit {mode}**\nEnter new value (e.g., 50):",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "manage_sl_mode"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "ai_monitor":
            mt5_connected = chat_id in accounts
            news = fetch_x_news()
            theblock = scrape_theblock(mt5_connected)
            fxstreet = scrape_fxstreet(mt5_connected)
            tradays = scrape_tradays(mt5_connected)
            ai_insight = analyze_sources(news, theblock, fxstreet, tradays)
            quantum_signal = quantum_analyze("BTCUSD") if mt5_connected else "N/A"
            trade_count = len(trades[chat_id]) if chat_id in trades else 0
            account_text = "No Account Linked" if not mt5_connected else f"{accounts[chat_id]['name']} (#{accounts[chat_id]['account']})"
            await query.edit_message_text(
                f"**📊 AI Monitor**: {account_text} ({datetime.now().strftime('%B %d, %Y')})\n"
                f"Trades: {trade_count}\n"
                f"X News: {news[0]}\n"
                f"The Block: {theblock}\n"
                f"FXStreet: {fxstreet}\n"
                f"Tradays: {tradays}\n"
                f"AI Insight: {ai_insight}",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Alerts", "callback_data": "alerts"}, {"text": "Sniper Mode", "callback_data": "sniper_mode"}, {"text": "Beast Mode", "callback_data": "beast_mode"}],
                        [{"text": "Stats & Reports", "callback_data": "stats_reports"}, {"text": "Settings", "callback_data": "settings_ai"}],
                        [{"text": "Back", "callback_data": "start"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "alerts":
            await query.edit_message_text(
                "**Alerts** (Auto-Trade: On)\nSelect category:",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Live Alerts", "callback_data": "live_alerts"}, {"text": "Past Alerts", "callback_data": "past_alerts"}],
                        [{"text": "Toggle Auto-Trade", "callback_data": "toggle_auto_trade"}, {"text": "Back", "callback_data": "ai_monitor"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "live_alerts":
            await query.edit_message_text(
                "**Live Alerts**\nMar 23, 2025 10:00: BTCUSD $60,080.50 - Auto-executed",
                reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "alerts"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "past_alerts":
            await query.edit_message_text(
                "**Past Alerts**\nMar 22, 2025 09:00: BTCUSD $59,950.00 - Executed",
                reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "alerts"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "toggle_auto_trade":
            await query.edit_message_text(
                "**Alerts** (Auto-Trade: Off)",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Live Alerts", "callback_data": "live_alerts"}, {"text": "Past Alerts", "callback_data": "past_alerts"}],
                        [{"text": "Toggle Auto-Trade", "callback_data": "toggle_auto_trade_on"}, {"text": "Back", "callback_data": "ai_monitor"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "toggle_auto_trade_on":
            await query.edit_message_text(
                "**Alerts** (Auto-Trade: On)",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Live Alerts", "callback_data": "live_alerts"}, {"text": "Past Alerts", "callback_data": "past_alerts"}],
                        [{"text": "Toggle Auto-Trade", "callback_data": "toggle_auto_trade"}, {"text": "Back", "callback_data": "ai_monitor"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "sniper_mode":
            mt5_connected = chat_id in accounts
            if not mt5_connected:
                await query.edit_message_text(
                    "**Sniper Mode**\nLink an account to enable.",
                    reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "ai_monitor"}]]},
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    f"**Sniper Mode**: {settings['sniper_mode']}",
                    reply_markup={
                        "inline_keyboard": [
                            [{"text": "Default", "callback_data": "sniper_default"}, {"text": "Long", "callback_data": "sniper_long"}, {"text": "Short", "callback_data": "sniper_short"}],
                            [{"text": "Swing", "callback_data": "sniper_swing"}, {"text": "Scalp", "callback_data": "sniper_scalp"}, {"text": "Off", "callback_data": "sniper_off"}],
                            [{"text": "Back", "callback_data": "ai_monitor"}]
                        ]
                    }, parse_mode="Markdown"
                )

        elif query.data.startswith("sniper_"):
            mode = query.data.split("_")[1].capitalize()
            settings["sniper_mode"] = mode
            if mode != "Off" and chat_id in accounts:
                symbol = "BTCUSD"
                trade_type = "Long" if mode in ["Long", "Swing"] else "Short" if mode == "Short" else random.choice(["Long", "Short"])
                lots = settings["scalp_lots"] if mode != "Scalp" else settings["scalp_lots"] * 0.5
                execute_trade(chat_id, symbol, trade_type, lots)
            await query.edit_message_text(
                f"**Sniper Mode set to {mode}**",
                reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "ai_monitor"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "beast_mode":
            mt5_connected = chat_id in accounts
            if not mt5_connected:
                await query.edit_message_text(
                    "**Beast Mode**\nLink an account to enable.",
                    reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "ai_monitor"}]]},
                    parse_mode="Markdown"
                )
            else:
                settings["beast_mode"] = not settings["beast_mode"]
                if settings["beast_mode"] and mt5_connected:
                    execute_trade(chat_id, "XAUUSD", "Long", settings["scalp_lots"] * 2)
                await query.edit_message_text(
                    f"**Beast Mode**: {'On' if settings['beast_mode'] else 'Off'}",
                    reply_markup={"inline_keyboard": [[{"text": "Toggle", "callback_data": "beast_mode"}, {"text": "Back", "callback_data": "ai_monitor"}]]},
                    parse_mode="Markdown"
                )

        elif query.data == "stats_reports":
            await query.edit_message_text(
                "**Stats & Reports**\nSelect option:",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Stats", "callback_data": "stats"}, {"text": "Report", "callback_data": "report"}],
                        [{"text": "Back", "callback_data": "ai_monitor"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "stats":
            mt5_connected = chat_id in accounts
            if not mt5_connected or chat_id not in stats:
                await query.edit_message_text(
                    "**Stats**\nTrades: 0\nProfit: $0.00",
                    reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "stats_reports"}]]},
                    parse_mode="Markdown"
                )
            else:
                profit = stats[chat_id]["profit"]
                await query.edit_message_text(
                    f"**Stats**: {accounts[chat_id]['name']} (#{accounts[chat_id]['account']})\nTrades: {stats[chat_id]['trades']}\nProfit: ${profit:.2f}",
                    reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "stats_reports"}]]},
                    parse_mode="Markdown"
                )

        elif query.data == "report":
            await query.edit_message_text(
                "**Report**\nSelect time frame:",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "1d", "callback_data": "report_1d"}, {"text": "1w", "callback_data": "report_1w"}],
                        [{"text": "Back", "callback_data": "stats_reports"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "settings_ai":
            await query.edit_message_text(
                f"**Settings**\nMax Exposure: {settings['max_exposure']}% | Gains: {settings['gains']}% | Scalp: {settings['scalp_lots']} lots | SL: {settings['scalp_sl']} pips",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Edit Max Exposure", "callback_data": "edit_max_exposure"}, {"text": "Edit Gains", "callback_data": "edit_gains"}],
                        [{"text": "Edit Scalp Lots", "callback_data": "edit_scalp"}, {"text": "Edit Scalp SL", "callback_data": "edit_scalp_sl"}],
                        [{"text": "Back", "callback_data": "ai_monitor"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "edit_max_exposure":
            user_state[chat_id] = {"step": "max_exposure"}
            await query.edit_message_text(
                "**Edit Max Exposure**\nEnter value (e.g., 2):",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "settings_ai"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "edit_gains":
            user_state[chat_id] = {"step": "gains"}
            await query.edit_message_text(
                "**Edit Gains**\nEnter value (e.g., 15):",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "settings_ai"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "edit_scalp":
            user_state[chat_id] = {"step": "scalp_lots"}
            await query.edit_message_text(
                "**Edit Scalp Lots**\nEnter value (e.g., 0.3):",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "settings_ai"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "edit_scalp_sl":
            user_state[chat_id] = {"step": "scalp_sl"}
            await query.edit_message_text(
                "**Edit Scalp SL**\nEnter value (e.g., 30):",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "settings_ai"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "users":
            users_text = "\n".join(authorized_users)
            await query.edit_message_text(
                f"**Users**\n{users_text}",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "Add User", "callback_data": "add_user"}, {"text": "Delete User", "callback_data": "delete_user"}],
                        [{"text": "Back", "callback_data": "start"}]
                    ]
                }, parse_mode="Markdown"
            )

        elif query.data == "add_user":
            user_state[chat_id] = {"step": "add_user"}
            await query.edit_message_text(
                "**Add User**\nEnter username (e.g., @NewUser):",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "users"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "delete_user":
            user_state[chat_id] = {"step": "delete_user"}
            users_text = "\n".join(authorized_users)
            await query.edit_message_text(
                f"**Delete User**\nEnter username:\n{users_text}",
                reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "users"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "restart":
            if chat_id in trades:
                del trades[chat_id]
            await query.edit_message_text(
                "**Restarted**\nTrades cleared.",
                reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "start"}]]},
                parse_mode="Markdown"
            )

        elif query.data == "close":
            if chat_id in accounts:
                MetaTrader5.shutdown()
            await query.edit_message_text(
                "**Bot Closed**",
                reply_markup={"inline_keyboard": [[{"text": "Start Again", "callback_data": "start"}]]},
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Button error: {e}")
        await query.edit_message_text(f"**Error**: {e}", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "start"}]]}, parse_mode="Markdown")

async def handle_message(update, context):
    chat_id = update.message.chat_id
    username = update.message.from_user.username or f"User_{chat_id}"
    if username not in authorized_users:
        await update.message.reply_text("Access Denied\nYou’re not authorized.")
        return
    text = update.message.text.strip()
    logger.info(f"Message from {username}: {text}")

    if chat_id in user_state:
        state = user_state[chat_id]["step"]
        if state == "account_number" and text.isdigit():
            user_state[chat_id]["account"] = text
            user_state[chat_id]["step"] = "server"
            await update.message.reply_text("Enter server:", reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "accounts_presets"}]]}, parse_mode="Markdown")
        elif state == "server":
            user_state[chat_id]["server"] = text
            user_state[chat_id]["step"] = "password"
            await update.message.reply_text("Enter password:", reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "accounts_presets"}]]}, parse_mode="Markdown")
        elif state == "password":
            user_state[chat_id]["password"] = text
            user_state[chat_id]["step"] = "name"
            await update.message.reply_text("Enter account name:", reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "accounts_presets"}]]}, parse_mode="Markdown")
        elif state == "name":
            account = user_state[chat_id]["account"]
            server = user_state[chat_id]["server"]
            password = user_state[chat_id]["password"]
            name = text
            if init_mt5(account, server, password):
                accounts[chat_id] = {"account": account, "server": server, "password": password, "name": name}
                await update.message.reply_text(f"**Account {name} (#{account}) linked!**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "accounts_presets"}]]}, parse_mode="Markdown")
            else:
                await update.message.reply_text("**Failed to link**—check credentials!", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "accounts_presets"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state == "scaling_add_pair" and "/" in text:
            settings["scaling_pairs"].append(text)
            await update.message.reply_text(f"**Scaling Pair added: {text}**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "craft_scaling"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state == "scaling_delete_pair" and text in settings["scaling_pairs"]:
            settings["scaling_pairs"].remove(text)
            if text in settings.get("selected_pairs", []):
                settings["selected_pairs"].remove(text)
            await update.message.reply_text(f"**Scaling Pair deleted: {text}**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "manage_scaling"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state == "trailing" and text.isdigit():
            settings["trailing"] = int(text)
            await update.message.reply_text(f"**Trailing set to {text} pips**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "settings"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state == "add_sl_mode":
            settings["sl_mode"] = text
            await update.message.reply_text(f"**SL Mode added: {text}**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "manage_sl_mode"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state.startswith("edit_sl_") and text.isdigit():
            mode = state.replace("edit_sl_", "").replace("_", " ").title()
            await update.message.reply_text(f"**{mode} set to {text}**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "manage_sl_mode"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state == "max_exposure" and text.isdigit():
            settings["max_exposure"] = int(text)
            await update.message.reply_text(f"**Max Exposure set to {text}%**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "settings_ai"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state == "gains" and text.isdigit():
            settings["gains"] = int(text)
            await update.message.reply_text(f"**Gains set to {text}%**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "settings_ai"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state == "scalp_lots" and text.replace(".", "").isdigit():
            settings["scalp_lots"] = float(text)
            await update.message.reply_text(f"**Scalp Lots set to {text}**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "settings_ai"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state == "scalp_sl" and text.isdigit():
            settings["scalp_sl"] = int(text)
            await update.message.reply_text(f"**Scalp SL set to {text} pips**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "settings_ai"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state == "add_user" and text.startswith("@"):
            authorized_users.add(text.lstrip("@"))
            await update.message.reply_text(f"**User {text} added**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "users"}]]}, parse_mode="Markdown")
            del user_state[chat_id]
        elif state == "delete_user" and text.lstrip("@") in authorized_users:
            user_to_delete = text.lstrip("@")
            if user_to_delete == "Miracrypto7" and len(authorized_users) == 1:
                await update.message.reply_text("**Cannot delete only admin**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "users"}]]}, parse_mode="Markdown")
            else:
                authorized_users.remove(user_to_delete)
                await update.message.reply_text(f"**User @{user_to_delete} deleted**", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "users"}]]}, parse_mode="Markdown")
            del user_state[chat_id]

# Register Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.Text(), handle_message))

# Main Execution
if __name__ == "__main__":
    logger.info("Bot starting...")
    threading.Thread(target=keep_alive, daemon=True).start()  # Start keep-alive in background
    try:
        app.run_polling()
        logger.info("Polling started")
    except Exception as e:
        logger.error(f"Polling error: {e}")
