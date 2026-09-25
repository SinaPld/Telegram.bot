import json
import logging
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

# =========================================================
# تنظیمات
# =========================================================

BOT_TOKEN = "8622193446:AAHZXNk91Li0CJUz1E3pfk_2pDLDwkTZ9wA"

# بعد از اجرای /id داخل گروه، عدد ID گروه را اینجا قرار بده.
# مثال: GROUP_ID = -1001234567890
GROUP_ID = -5378431231

# پروکسی HTTP
PROXY_URL = "http://213.111.146.36:18080"

DATA_FILE = Path("data.json")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

data = {"members": [], "blacklist": []}

# =========================================================
# وضعیت فرم عضویت
# =========================================================

JOIN_LEVEL, JOIN_FACTION, JOIN_AGE, JOIN_GAME, JOIN_NAME = range(5)

# پیام‌های پشتیبانی:
# message_id پیام داخل گروه -> user_id
support_messages = {}
pending_applications = {}


# =========================================================
# DATA
# =========================================================

def load_data():
    if not DATA_FILE.exists():
        return {"members": [], "blacklist": []}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            result = json.load(f)

        result.setdefault("members", [])
        result.setdefault("blacklist", [])
        return result

    except (json.JSONDecodeError, OSError):
        return {"members": [], "blacklist": []}


def save_data():
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load_data()


# =========================================================
# MENU
# =========================================================

def main_menu():
    keyboard = [
        [KeyboardButton("🏛 درخواست عضویت در شعبه ۱ (دولت)")],
        [KeyboardButton("🔒 درخواست شعبه ۲ (گتو) — بسته")],
        [KeyboardButton("👥 اعضای خانواده")],
        [KeyboardButton("⬆️ Rank Up")],
        [KeyboardButton("🆘 پشتیبانی")],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


# =========================================================
# /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user

    if user and user.id in data["blacklist"]:
        await update.message.reply_text("⛔ شما در لیست سیاه قرار دارید.")
        return

    context.user_data.clear()

    await update.message.reply_text(
        "سلام 👋\n\n"
        "به ربات خوش آمدید.\n"
        "گزینه موردنظر را انتخاب کنید:",
        reply_markup=main_menu(),
    )


# =========================================================
# /ID
# =========================================================

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if not chat:
        return

    await update.message.reply_text(
        f"🆔 Chat ID:\n\n`{chat.id}`",
        parse_mode="Markdown",
    )


# =========================================================
# ابزارهای ادمین و درخواست عضویت
# =========================================================

async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or GROUP_ID == 0:
        return False
    try:
        member = await context.bot.get_chat_member(GROUP_ID, update.effective_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def notify_application_result(context, user_id, approved):
    try:
        if approved:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ درخواست عضویت شما تأیید شد.\nبه خانواده خوش آمدید! 🎉",
                reply_markup=main_menu(),
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ درخواست عضویت شما رد شد.\nدر صورت نیاز می‌توانید از پشتیبانی پیام دهید.",
                reply_markup=main_menu(),
            )
    except Exception:
        logger.exception("خطا در اطلاع‌رسانی نتیجه درخواست")


async def application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if query.message is None or query.message.chat.id != GROUP_ID:
        return

    if not await is_group_admin(update, context):
        await query.answer("⛔ فقط ادمین‌های گروه می‌توانند این کار را انجام دهند.", show_alert=True)
        return

    action, raw_id = query.data.split(":", 1)
    try:
        application_id = int(raw_id)
    except ValueError:
        return

    application = pending_applications.pop(application_id, None)
    if not application:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.answer("این درخواست قبلاً بررسی شده است.", show_alert=True)
        return

    user_id = application["user_id"]

    if action == "approve":
        if not any(
            (m.get("user_id") == user_id if isinstance(m, dict) else False)
            for m in data.get("members", [])
        ):
            data["members"].append({
                "user_id": user_id,
                "name": application["name"],
                "rank": "Member",
            })
            save_data()

        await notify_application_result(context, user_id, True)
        result_text = "✅ این درخواست توسط ادمین تأیید شد."
    else:
        await notify_application_result(context, user_id, False)
        result_text = "❌ این درخواست توسط ادمین رد شد."

    try:
        await query.edit_message_text(
            text=query.message.text + "\n\n" + result_text
        )
    except Exception:
        pass


# =========================================================
# BLACKLIST
# =========================================================

async def blacklist_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID or not await is_group_admin(update, context):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("استفاده صحیح:\n/blacklist USER_ID")
        return

    user_id = int(context.args[0])

    if user_id not in data["blacklist"]:
        data["blacklist"].append(user_id)
        save_data()

    pending_applications.pop(user_id, None)
    await update.message.reply_text(f"🚫 کاربر `{user_id}` به بلک‌لیست اضافه شد.", parse_mode="Markdown")


async def unblacklist_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID or not await is_group_admin(update, context):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("استفاده صحیح:\n/unblacklist USER_ID")
        return

    user_id = int(context.args[0])

    if user_id in data["blacklist"]:
        data["blacklist"].remove(user_id)
        save_data()
        await update.message.reply_text(f"✅ کاربر `{user_id}` از بلک‌لیست خارج شد.", parse_mode="Markdown")
    else:
        await update.message.reply_text("ℹ️ این کاربر در بلک‌لیست نیست.")


async def blacklist_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID or not await is_group_admin(update, context):
        return

    blacklist = data.get("blacklist", [])
    if not blacklist:
        await update.message.reply_text("🚫 لیست بلک‌لیست خالی است.")
        return

    text = "🚫 کاربران بلک‌لیست‌شده:\n\n"
    text += "\n".join(f"• `{uid}`" for uid in blacklist)
    await update.message.reply_text(text, parse_mode="Markdown")


# =========================================================
# بررسی گروه مقصد
# =========================================================

async def send_to_group(context: ContextTypes.DEFAULT_TYPE, text: str):
    if GROUP_ID == 0:
        logger.warning("GROUP_ID هنوز تنظیم نشده است.")
        return None

    return await context.bot.send_message(
        chat_id=GROUP_ID,
        text=text,
    )


# =========================================================
# عضویت شعبه ۱
# =========================================================

async def branch1_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return ConversationHandler.END

    user = update.effective_user

    if user and user.id in data["blacklist"]:
        await update.message.reply_text("⛔ شما در لیست سیاه قرار دارید.")
        return ConversationHandler.END

    context.user_data.clear()

    await update.message.reply_text(
        "🏛 درخواست عضویت در شعبه ۱ (دولت)\n\n"
        "مرحله ۱ از ۵\n\n"
        "🎖 لول شما چنده؟"
    )

    return JOIN_LEVEL


async def join_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["level"] = update.message.text.strip()

    await update.message.reply_text(
        "مرحله ۲ از ۵\n\n"
        "🏴 در کدام فکشن هستید؟"
    )

    return JOIN_FACTION


async def join_faction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["faction"] = update.message.text.strip()

    await update.message.reply_text(
        "مرحله ۳ از ۵\n\n"
        "🎂 سن شما چنده؟"
    )

    return JOIN_AGE


async def join_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    age = update.message.text.strip()

    if not age.isdigit():
        await update.message.reply_text(
            "⚠️ لطفاً سن را به صورت عدد وارد کنید.\n"
            "مثال: 18"
        )
        return JOIN_AGE

    context.user_data["age"] = age

    await update.message.reply_text(
        "مرحله ۴ از ۵\n\n"
        "🎮 اسم گیم شما چیه؟"
    )

    return JOIN_GAME


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["game"] = update.message.text.strip()

    await update.message.reply_text(
        "مرحله ۵ از ۵\n\n"
        "👤 اسم و نام خانوادگی خود را وارد کنید:"
    )

    return JOIN_NAME


async def join_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    name = update.message.text.strip()
    level = context.user_data.get("level", "-")
    faction = context.user_data.get("faction", "-")
    age = context.user_data.get("age", "-")
    game = context.user_data.get("game", "-")

    user_id = user.id if user else "-"
    username = f"@{user.username}" if user and user.username else "ندارد"

    application_text = (
        "🏛 درخواست عضویت جدید — شعبه ۱ (دولت)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 اسم: {name}\n"
        f"🎖 لول: {level}\n"
        f"🏴 فکشن: {faction}\n"
        f"🎂 سن: {age}\n"
        f"🎮 اسم گیم: {game}\n"
        f"🔗 Username: {username}\n"
        f"🆔 User ID: {user_id}\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    if GROUP_ID == 0:
        await update.message.reply_text(
            "⚠️ گروه مقصد هنوز تنظیم نشده است.\n"
            "ادمین باید داخل گروه /id را بزند و ID گروه را در bot.py قرار دهد."
        )
        context.user_data.clear()
        return ConversationHandler.END

    try:
        sent = await send_to_group(context, application_text)

        if sent:
            pending_applications[sent.message_id] = {
                "user_id": user_id,
                "name": name,
            }
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ تأیید درخواست", callback_data=f"approve:{sent.message_id}"),
                    InlineKeyboardButton("❌ رد درخواست", callback_data=f"reject:{sent.message_id}"),
                ]
            ])
            await context.bot.edit_message_reply_markup(
                chat_id=GROUP_ID,
                message_id=sent.message_id,
                reply_markup=keyboard,
            )

        await update.message.reply_text(
            "✅ درخواست عضویت شما ثبت شد.\n"
            "درخواست برای گروه بررسی ارسال شد.",
            reply_markup=main_menu(),
        )

    except Exception:
        logger.exception("خطا در ارسال درخواست عضویت")
        await update.message.reply_text(
            "❌ ارسال درخواست انجام نشد. لطفاً بعداً دوباره امتحان کنید."
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "❌ عملیات لغو شد.",
        reply_markup=main_menu(),
    )

    return ConversationHandler.END


# =========================================================
# شعبه ۲
# =========================================================

async def branch2_closed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    await update.message.reply_text(
        "🔒 درخواست شعبه ۲ (گتو)\n\n"
        "در حال حاضر ثبت درخواست برای این شعبه بسته است."
    )


# =========================================================
# اعضای خانواده
# =========================================================

async def family_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    members = data.get("members", [])

    if not members:
        await update.message.reply_text("👥 هنوز عضوی ثبت نشده است.")
        return

    text = "👥 اعضای خانواده:\n\n"

    for i, member in enumerate(members, 1):
        if isinstance(member, dict):
            name = member.get("name", "بدون نام")
            rank = member.get("rank", "بدون رتبه")
            text += f"{i}. {name} — {rank}\n"
        else:
            text += f"{i}. {member}\n"

    await update.message.reply_text(text)


# =========================================================
# RANK UP
# =========================================================

async def rank_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    await update.message.reply_text(
        "⬆️ Rank Up\n\n"
        "برای درخواست ارتقای رتبه، از بخش 🆘 پشتیبانی پیام بفرستید."
    )


# =========================================================
# SUPPORT
# =========================================================

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    context.user_data["support_mode"] = True

    await update.message.reply_text(
        "🆘 پشتیبانی فعال شد.\n\n"
        "پیام خود را ارسال کنید.\n"
        "پیام شما داخل گروه پشتیبانی ارسال می‌شود و ادمین می‌تواند "
        "با Reply پاسخ دهد."
    )


async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    if not context.user_data.get("support_mode"):
        return

    user = update.effective_user

    if not user or not update.message:
        return

    if user.id in data.get("blacklist", []):
        await update.message.reply_text("⛔ شما در لیست سیاه قرار دارید و امکان استفاده از پشتیبانی را ندارید.")
        context.user_data["support_mode"] = False
        return

    if GROUP_ID == 0:
        await update.message.reply_text(
            "⚠️ گروه مقصد هنوز تنظیم نشده است."
        )
        return

    username = f"@{user.username}" if user.username else "بدون username"
    name = user.full_name or "بدون نام"
    message_text = update.message.text or ""

    group_text = (
        "🆘 درخواست پشتیبانی جدید\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 نام: {name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 User ID: {user.id}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💬 پیام:\n{message_text}\n\n"
        "↩️ برای پاسخ به کاربر، روی همین پیام Reply کنید."
    )

    try:
        sent = await send_to_group(context, group_text)

        if sent:
            support_messages[sent.message_id] = user.id

        context.user_data["support_mode"] = False

        await update.message.reply_text(
            "✅ پیام شما برای پشتیبانی ارسال شد.\n"
            "منتظر پاسخ ادمین باشید.",
            reply_markup=main_menu(),
        )

    except Exception:
        logger.exception("خطا در ارسال پشتیبانی")

        await update.message.reply_text(
            "❌ ارسال پیام پشتیبانی انجام نشد."
        )


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return

    if not update.message:
        return

    if not await is_group_admin(update, context):
        return

    if not update.message.reply_to_message:
        return

    replied_id = update.message.reply_to_message.message_id
    user_id = support_messages.get(replied_id)

    if user_id is None:
        return

    reply_text = update.message.text or ""

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🆘 پاسخ پشتیبانی:\n\n{reply_text}",
        )

        await update.message.reply_text(
            "✅ پاسخ برای کاربر ارسال شد."
        )

    except Exception:
        logger.exception("خطا در ارسال پاسخ پشتیبانی")

        await update.message.reply_text(
            "❌ ارسال پاسخ برای کاربر انجام نشد."
        )


# =========================================================
# پیام‌های عادی
# =========================================================

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    # وقتی کاربر در حالت پشتیبانی است، پیام او فقط توسط support_message
    # پردازش می‌شود و این هندلر نباید جواب اضافی بدهد.
    if context.user_data.get("support_mode"):
        return

    await update.message.reply_text(
        "لطفاً یکی از گزینه‌های منو را انتخاب کنید.",
        reply_markup=main_menu(),
    )


# =========================================================
# BUILD APP
# =========================================================

def build_app():
    request = HTTPXRequest(
        proxy=PROXY_URL,
        connect_timeout=60,
        read_timeout=60,
        write_timeout=60,
        pool_timeout=60,
    )

    get_updates_request = HTTPXRequest(
        proxy=PROXY_URL,
        connect_timeout=60,
        read_timeout=60,
        write_timeout=60,
        pool_timeout=60,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(get_updates_request)
        .build()
    )

    # /start
    app.add_handler(CommandHandler("start", start))

    # /id
    # هم در گروه و هم در PV کار می‌کند.
    app.add_handler(CommandHandler("id", get_id))

    # مدیریت درخواست‌ها و بلک‌لیست
    app.add_handler(CallbackQueryHandler(application_callback))
    app.add_handler(CommandHandler("blacklist", blacklist_user))
    app.add_handler(CommandHandler("unblacklist", unblacklist_user))
    app.add_handler(CommandHandler("blacklistlist", blacklist_list))

    # فرم عضویت شعبه ۱
    branch1_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(r"^🏛 درخواست عضویت در شعبه ۱ \(دولت\)$"),
                branch1_start,
            )
        ],
        states={
            JOIN_LEVEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, join_level)
            ],
            JOIN_FACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, join_faction)
            ],
            JOIN_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, join_age)
            ],
            JOIN_GAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, join_game)
            ],
            JOIN_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, join_name)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
    )

    app.add_handler(branch1_conversation)

    # شعبه ۲
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^🔒 درخواست شعبه ۲ \(گتو\) — بسته$"),
            branch2_closed,
        )
    )

    # اعضای خانواده
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^👥 اعضای خانواده$"),
            family_members,
        )
    )

    # Rank Up
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^⬆️ Rank Up$"),
            rank_up,
        )
    )

    # Support button
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^🆘 پشتیبانی$"),
            support,
        )
    )

    # Reply ادمین در گروه
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.REPLY & ~filters.COMMAND,
            admin_reply,
        ),
        group=1,
    )

    # پیام پشتیبانی کاربر
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            support_message,
        ),
        group=1,
    )

    # پیام‌های عادی کاربر
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            unknown_message,
        ),
        group=0,
    )

    return app


# =========================================================
# MAIN
# =========================================================

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        raise RuntimeError(
            "❌ BOT_TOKEN را داخل bot.py قرار دهید."
        )

    if GROUP_ID == 0:
        print("⚠️ GROUP_ID هنوز تنظیم نشده.")
        print("ربات را داخل گروه اضافه کنید و /id را بزنید.")
        print("سپس عدد ID گروه را داخل GROUP_ID قرار دهید.")

    app = build_app()

    print("================================")
    print("🤖 Bot is running...")
    print("🏛 Branch 1: Open")
    print("🔒 Branch 2: Closed")
    print("🆘 Support: Group + Reply")
    print("🆔 /id enabled")
    print("================================")

    app.run_polling()


if __name__ == "__main__":
    main()
