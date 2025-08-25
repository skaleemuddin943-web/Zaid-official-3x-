import logging
import json
import os
from datetime import timedelta, datetime
import random

from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)

COINS_FILE = "coins.json"
BONUS_FILE = "bonus_claims.json"

coin_data = {}
bonus_claims = {}

rules_text = (
    "📜 Group Rules:\n"
    "1. No spam.\n"
    "2. Respect everyone.\n"
    "3. No cheating in games.\n"
    "4. Have fun! 🎉"
)
choices = ['rock', 'paper', 'scissors']
win_map = {'rock': 'scissors', 'scissors': 'paper', 'paper': 'rock'}


# --- Persistence helpers ---
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def load_data():
    global coin_data, bonus_claims
    coin_data = load_json(COINS_FILE)
    bonus_claims = load_json(BONUS_FILE)

def save_coin_data():
    save_json(COINS_FILE, coin_data)

def save_bonus_data():
    save_json(BONUS_FILE, bonus_claims)


# --- Coin management ---
def get_coins(uid):
    return int(coin_data.get(str(uid), 100))  # default 100 coins on first join

def change_coins(uid, amount):
    uid = str(uid)
    coin_data[uid] = get_coins(uid) + amount
    if coin_data[uid] < 0:
        coin_data[uid] = 0
    save_coin_data()

# --- Daily bonus checks ---
def can_claim_bonus(uid):
    uid = str(uid)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return bonus_claims.get(uid) != today

def claim_bonus(uid, amount):
    uid = str(uid)
    bonus_claims[uid] = datetime.utcnow().strftime("%Y-%m-%d")
    change_coins(uid, amount)
    save_bonus_data()


# --- Admin check ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    chat_member = await update.effective_chat.get_member(user)
    return chat_member.status in ["administrator", "creator"]


# ======= Handlers =======

# Welcome new users & show rules
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        uid = member.id
        # Initialize coins for new user
        if str(uid) not in coin_data:
            change_coins(uid, 100)
        await update.message.reply_text(
            f"👋 Welcome, {member.mention_html()}!\n{rules_text}",
            parse_mode='HTML'
        )

# /start command - greet and initialize coins
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if str(uid) not in coin_data:
        change_coins(uid, 100)
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}! You have been credited with 100 starting coins.\n"
        f"Use /help to see all commands."
    )

# /help command listing available commands
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 Bot Commands:\n"
        "/start - Register yourself and get starting coins\n"
        "/rules - Show group rules\n"
        "/stats or /balance - Check your coin balance\n"
        "/bonus - Claim your daily random coin bonus\n"
        "/startgame - Introduction to RPS game\n"
        "/rps <rock|paper|scissors> - Play RPS with the bot (+/- coins)\n"
        "/bet @user <amount> <choice> - Challenge a friend to RPS betting coins\n"
        "/acceptbet <rock|paper|scissors> - Accept a bet challenge\n"
        "/leaderboard - Top coin holders\n"
        "/ping - Check bot responsiveness\n\n"
        "Admin Commands (reply to a user's message):\n"
        "/kick - Remove user from group\n"
        "/ban - Ban user\n"
        "/unban <user_id> - Unban user by ID\n"
        "/mute <seconds> - Mute user temporarily\n"
        "/unmute - Unmute user\n"
    )
    await update.message.reply_text(msg)

# /ping command
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong! ✅ I'm online.")

# Show group rules
async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(rules_text)

# Show coin stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    coins = get_coins(uid)
    await update.message.reply_text(f"{update.effective_user.first_name}, you have {coins} coins.")

# alias for stats
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stats(update, context)

# Give daily bonus, random 10-100 coins
async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if can_claim_bonus(uid):
        amount = random.randint(10, 100)
        claim_bonus(uid, amount)
        await update.message.reply_text(f"🎉 You claimed your daily bonus of {amount} coins!")
    else:
        await update.message.reply_text("You already claimed your bonus today. Come back tomorrow!")

# Admin commands

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context):
        if update.message.reply_to_message:
            user = update.message.reply_to_message.from_user
            await update.effective_chat.ban_member(user.id)
            await update.effective_chat.unban_member(user.id)
            await update.message.reply_text(f"{user.full_name} was kicked from the group.")
        else:
            await update.message.reply_text("Please reply to the user you want to kick.")
    else:
        await update.message.reply_text("❌ Only admins can use this command.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context):
        if update.message.reply_to_message:
            user = update.message.reply_to_message.from_user
            await update.effective_chat.ban_member(user.id)
            await update.message.reply_text(f"{user.full_name} was banned from the group.")
        else:
            await update.message.reply_text("Please reply to the user you want to ban.")
    else:
        await update.message.reply_text("❌ Only admins can use this command.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context):
        if context.args:
            try:
                user_id = int(context.args[0])
                await update.effective_chat.unban_member(user_id)
                await update.message.reply_text("User unbanned successfully.")
            except Exception:
                await update.message.reply_text("Please provide a valid user ID: /unban <user_id>")
        else:
            await update.message.reply_text("Usage: /unban <user_id>")
    else:
        await update.message.reply_text("❌ Only admins can use this command.")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context):
        if update.message.reply_to_message and context.args:
            user = update.message.reply_to_message.from_user
            try:
                seconds = int(context.args[0])
            except ValueError:
                await update.message.reply_text("Please provide mute time in seconds.")
                return

            until_date = update.message.date + timedelta(seconds=seconds)
            perms = ChatPermissions(can_send_messages=False)
            await context.bot.restrict_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user.id,
                permissions=perms,
                until_date=until_date
            )
            await update.message.reply_text(f"{user.full_name} muted for {seconds} seconds.")
        else:
            await update.message.reply_text("Reply to a user and specify time in seconds. Usage: /mute <seconds>")
    else:
        await update.message.reply_text("❌ Only admins can use this command.")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context):
        if update.message.reply_to_message:
            user = update.message.reply_to_message.from_user
            perms = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
            await context.bot.restrict_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user.id,
                permissions=perms,
            )
            await update.message.reply_text(f"{user.full_name} has been unmuted.")
        else:
            await update.message.reply_text("Reply to the user whom you want to unmute.")
    else:
        await update.message.reply_text("❌ Only admins can use this command.")


# Game functions

async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Rock, Paper, Scissors!\n"
        "Use /rps <rock|paper|scissors> to play against me.\n"
        "Use /bet @username <amount> <choice> to challenge friends!\n"
        "Use /acceptbet <rock|paper|scissors> to accept a bet."
    )

async def rps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args
    if not args or args[0] not in choices:
        await update.message.reply_text("Usage: /rps <rock|paper|scissors>")
        return
    user_choice = args[0]
    ai_choice = random.choice(choices)
    response = f"You chose {user_choice}, I chose {ai_choice}.\n"
    if user_choice == ai_choice:
        response += "It's a draw!"
    elif win_map[user_choice] == ai_choice:
        change_coins(uid, 10)
        response += "You win! (+10 coins)"
    else:
        change_coins(uid, -10)
        response += "You lose! (-10 coins)"
    await update.message.reply_text(response)


# Betting system
# Store bets as: key = challenged username, value = dict with challenger, amount, challenger_choice
bet_requests = {}

async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /bet @username <amount> <choice>")
        return
    username, amount_str, choice = context.args[:3]
    if choice not in choices:
        await update.message.reply_text("Choice must be rock, paper, or scissors.")
        return
    try:
        amount = int(amount_str)
    except ValueError:
        await update.message.reply_text("Please enter a valid amount.")
        return
    if amount <= 0:
        await update.message.reply_text("Amount must be greater than zero.")
        return

    # Ensure challenger has enough coins
    if get_coins(uid) < amount:
        await update.message.reply_text("You don't have enough coins to bet that amount.")
        return

    # Get target user by mention parsing
    if not update.message.entities:
        await update.message.reply_text("You must mention someone to challenge.")
        return

    target_username = None
    for ent in update.message.entities:
        if ent.type == "mention":
            target_username = update.message.text[ent.offset:ent.offset + ent.length]
            break

    if not target_username:
        await update.message.reply_text("You must mention someone to challenge.")
        return

    # Store challenge keyed by target user's username (in lowercase)
    bet_requests[target_username.lower()] = {
        "challenger": uid,
        "amount": amount,
        "challenger_choice": choice
    }

    await update.message.reply_text(
        f"{target_username}, you have been challenged by {update.effective_user.mention_html()} "
        f"to a Rock-Paper-Scissors duel betting {amount} coins on '{choice}'!\n"
        f"Type /acceptbet <rock|paper|scissors> to accept the challenge.",
        parse_mode="HTML"
    )

async def acceptbet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args
    if not args or args[0] not in choices:
        await update.message.reply_text("Usage: /acceptbet <rock|paper|scissors>")
        return

    if not update.effective_user.username:
        await update.message.reply_text("You must set a username in Telegram to accept bets.")
        return

    key = f"@{update.effective_user.username}".lower()
    challenge = bet_requests.pop(key, None)

    if not challenge:
        await update.message.reply_text("You have no pending bet challenges.")
        return

    challenger, amount, challenger_choice = (
        challenge['challenger'], 
        challenge['amount'], 
        challenge['challenger_choice']
    )

    # Check if both players have enough coins
    if get_coins(uid) < amount:
        await update.message.reply_text("You don't have enough coins to accept the bet.")
        return
    if get_coins(challenger) < amount:
        await update.message.reply_text("Challenger doesn't have enough coins anymore.")
        return

    user_choice = args[0]
    msg = f"Bet result:\n{update.effective_user.mention_html()} chose {user_choice}, " \
          f"challenger chose {challenger_choice}.\n"

    if user_choice == challenger_choice:
        msg += "It's a draw! No coins exchanged."
    elif win_map[user_choice] == challenger_choice:
        change_coins(uid, amount)
        change_coins(challenger, -amount)
        msg += f"{update.effective_user.mention_html()} wins {amount} coins!"
    else:
        change_coins(uid, -amount)
        change_coins(challenger, amount)
        msg += f"Challenger <code>{challenger}</code> wins {amount} coins!"

    await update.message.reply_text(msg, parse_mode="HTML")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not coin_data:
        await update.message.reply_text("No player data available yet.")
        return

    sorted_coins = sorted(coin_data.items(), key=lambda x: x[1], reverse=True)[:10]
    msg = "🏆 Leaderboard - Top coin holders 🏆\n"
    for rank, (uid, coins) in enumerate(sorted_coins, start=1):
        try:
            user = await context.bot.get_chat_member(update.effective_chat.id, int(uid))
            name = user.user.first_name
        except Exception:
            name = f"User({uid})"
        msg += f"{rank}. {name}: {coins} coins\n"
    await update.message.reply_text(msg)


# Load coins and bonus data on startup
load_data()


# Bot app initialization
app = ApplicationBuilder().token("8433194557:AAFeYUpVejptWUTvFIp5Ir_T4JWgjMJ5NNU").build()

# Event handlers
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))

# Commands
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("ping", ping))
app.add_handler(CommandHandler("rules", show_rules))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("bonus", bonus))

app.add_handler(CommandHandler("kick", kick))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CommandHandler("mute", mute))
app.add_handler(CommandHandler("unmute", unmute))

app.add_handler(CommandHandler("startgame", startgame))
app.add_handler(CommandHandler("rps", rps))
app.add_handler(CommandHandler("bet", bet))
app.add_handler(CommandHandler("acceptbet", acceptbet))
app.add_handler(CommandHandler("leaderboard", leaderboard))


if __name__ == "__main__":
    app.run_polling()

