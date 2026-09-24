from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================
# Nigan Bot Configuration
# =========================

TOKEN = "8767160886:AAETaZwmB_DzPtVkyhtL334XjJlRWyZufAs"

ADMIN_CHAT_ID = -1003981751098

# Telegram IDs of approved family members.
# Add member IDs here, or manage them with /addmember and /removemember in the admin group.
FAMILY_MEMBERS = set()

# HTTP Proxy
PROXY_URL = "http://18.157.123.132:3128"


async def route_special_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # These workflows must be checked before the membership form's generic text handler.
    if await receive_support(update, context):
        return
    if await receive_rankup(update, context):
        return
    await receive_form(update, context)


# =========================
# Main Menu
# =========================

MAIN_MENU = [
    ["📝 درخواست عضویت", "🎧 پشتیبانی"],
    ["⬆️ Rank Up", "📜 قوانین فمیلی"],
    ["📦 باکس فمیلی", "ℹ️ درباره Nigan"],
]

RULES_TEXT = """
📜 قوانین فمیلی Nigan

• احترام به اعضای فمیلی الزامی است.
• توهین و ایجاد حاشیه ممنوع است.
• فعالیت و حضور مناسب در فمیلی الزامی است.
• رعایت قوانین سرور و فمیلی الزامی است.
• اطلاعات داخلی فمیلی نباید منتشر شود.
• تصمیمات مدیریت فمیلی باید رعایت شود.
"""

ABOUT_TEXT = """
ℹ️ درباره Nigan

Nigan یک فمیلی RolePlay است که بر پایه نظم،
فعالیت، احترام و همکاری اعضا فعالیت می‌کند.
"""

SUPPORT_TEXT = """
🎧 پشتیبانی

برای ارتباط با مدیریت فمیلی،
پیام خود را ارسال کنید تا بررسی شود.
"""

RANK_TEXT = """
⬆️ Rank Up

برای درخواست Rank Up، میزان فعالیت و عملکرد
شما توسط مدیریت فمیلی بررسی می‌شود.
"""

BOX_TEXT = """
📦 باکس فمیلی

باکس فمیلی شامل امکانات و جوایز مربوط به
اعضای فمیلی است.
"""


# =========================
# Admin Telegram ID
# =========================

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 Telegram ID شما:\n{update.effective_user.id}"
    )


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 Chat ID این چت:\n{update.effective_chat.id}"
    )

# =========================
# Start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = ReplyKeyboardMarkup(
        MAIN_MENU,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "سلام 👋\n"
        "به بات رسمی Nigan خوش آمدید.\n\n"
        "از منوی زیر گزینه موردنظر خود را انتخاب کنید:",
        reply_markup=keyboard
    )


# =========================
# Membership
# =========================

async def start_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["step"] = "rules"

    keyboard = ReplyKeyboardMarkup(
        [["✅ قوانین را می‌پذیرم", "❌ لغو"]],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "📝 درخواست عضویت Nigan\n\n"
        "قبل از ثبت درخواست، قوانین فمیلی را مطالعه کنید:\n\n"
        f"{RULES_TEXT}\n"
        "در صورت قبول قوانین، گزینه «قوانین را می‌پذیرم» را بزنید.",
        reply_markup=keyboard
    )


async def accept_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["step"] = "name"

    await update.message.reply_text(
        "🎮 نام شما در بازی چیست؟"
    )


async def receive_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = context.user_data.get("step")

    if step == "name":
        context.user_data["name"] = text
        context.user_data["step"] = "level"

        await update.message.reply_text(
            "📊 لول شما در سرور چند است؟"
        )
        return

    if step == "level":
        context.user_data["level"] = text
        context.user_data["step"] = "age"

        await update.message.reply_text(
            "🎂 سن شما چند سال است؟"
        )
        return

    if step == "age":
        context.user_data["age"] = text
        context.user_data["step"] = "government"

        await update.message.reply_text(
            "🏛️ آیا سابقه فعالیت در سازمان‌های دولتی سرور را دارید؟\n\n"
            "مثال: بله / خیر"
        )
        return

    if step == "government":
        context.user_data["government"] = text
        context.user_data["step"] = "confirm"

        name = context.user_data.get("name", "-")
        level = context.user_data.get("level", "-")
        age = context.user_data.get("age", "-")
        government = context.user_data.get("government", "-")

        keyboard = ReplyKeyboardMarkup(
            [["✅ تأیید درخواست", "❌ لغو"]],
            resize_keyboard=True
        )

        await update.message.reply_text(
            "📋 خلاصه درخواست عضویت\n\n"
            f"🎮 نام بازی: {name}\n"
            f"📊 لول: {level}\n"
            f"🎂 سن: {age}\n"
            f"🏛️ سابقه سازمان دولتی: {government}\n\n"
            "اطلاعات را بررسی کنید و در صورت صحیح بودن، "
            "«تأیید درخواست» را بزنید.",
            reply_markup=keyboard
        )
        return


async def send_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("step") != "confirm":
        await update.message.reply_text(
            "ابتدا از منوی اصلی درخواست عضویت را شروع کنید."
        )
        return

    name = context.user_data.get("name", "-")
    level = context.user_data.get("level", "-")
    age = context.user_data.get("age", "-")
    government = context.user_data.get("government", "-")
    user = update.effective_user

    # Unique request id for the current user/message.
    request_id = update.message.message_id

    application_text = (
        "📝 درخواست عضویت جدید Nigan\n\n"
        f"🔢 شماره درخواست: {request_id}\n"
        f"👤 نام تلگرام: {user.full_name}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"🎮 نام بازی: {name}\n"
        f"📊 لول: {level}\n"
        f"🎂 سن: {age}\n"
        f"🏛️ سابقه سازمان دولتی: {government}\n\n"
        "⏳ وضعیت: در انتظار بررسی مدیریت"
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تأیید", callback_data=f"approve:{request_id}"),
        InlineKeyboardButton("❌ رد", callback_data=f"reject:{request_id}"),
    ]])

    try:
        sent = await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=application_text,
            reply_markup=keyboard,
        )

        requests = context.application.bot_data.setdefault("requests", {})
        requests[request_id] = {
            "user_id": user.id,
            "admin_message_id": sent.message_id,
            "name": name,
            "status": "pending",
        }

        context.user_data.clear()

        await update.message.reply_text(
            "✅ درخواست عضویت شما با موفقیت ثبت شد.\n\n"
            "⏳ درخواست برای مدیریت ارسال شد؛ نتیجه بعد از بررسی اعلام می‌شود.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ ارسال درخواست به گروه مدیریت انجام نشد.\n"
            f"کد خطا: {type(e).__name__}",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
        )


async def handle_application_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.message.chat.id != ADMIN_CHAT_ID:
        await query.answer("⛔ این دکمه فقط در گروه مدیریت قابل استفاده است.", show_alert=True)
        return

    action, raw_id = query.data.split(":", 1)
    request_id = int(raw_id)
    requests = context.application.bot_data.setdefault("requests", {})
    request = requests.get(request_id)

    if not request or request.get("status") != "pending":
        await query.answer("⚠️ این درخواست قبلاً بررسی شده یا در حافظه بات نیست.", show_alert=True)
        return

    if action == "approve":
        request["status"] = "approved"
        FAMILY_MEMBERS.add(request["user_id"])
        status = "✅ وضعیت: تأیید شد"
        user_message = "🎉 درخواست عضویت شما در Nigan تأیید شد.\n\n به فمیلی خوش آمدید جهت عضویت به پیوی مراجعه کنید 
        @Pv_SinaS❤️"
    elif action == "reject":
        request["status"] = "rejected"
        status = "❌ وضعیت: رد شد"
        user_message = "❌ درخواست عضویت شما در Nigan رد شد.\n\nبرای پیگیری با پشتیبانی در ارتباط باشید."
    else:
        return

    text = query.message.text.replace(
        "⏳ وضعیت: در انتظار بررسی مدیریت", status
    )
    await query.edit_message_text(text=text, reply_markup=None)

    try:
        await context.bot.send_message(
            chat_id=request["user_id"],
            text=user_message,
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
        )
    except Exception:
        pass

    await query.answer("انجام شد.")


# =========================
# Support
# =========================

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["step"] = "support"
    await update.message.reply_text(
        "🎧 پشتیبانی\n\n"
        "پیام خود را بنویسید؛ پیام شما مستقیماً برای گروه مدیریت ارسال می‌شود."
    )


async def receive_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("step") != "support":
        return False

    user = update.effective_user
    text = update.message.text.strip()

    support_text = (
        "🎧 پیام پشتیبانی جدید\n\n"
        f"👤 نام: {user.full_name}\n"
        f"🆔 Telegram ID: {user.id}\n\n"
        f"💬 پیام:\n{text}"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=support_text)
        context.user_data.clear()
        await update.message.reply_text(
            "✅ پیام شما برای مدیریت ارسال شد.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
        )
    except Exception:
        await update.message.reply_text(
            "❌ ارسال پیام پشتیبانی انجام نشد.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
        )
    return True


# =========================
# Family members / Rank Up
# =========================

async def family_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ این دستور فقط در گروه مدیریت قابل استفاده است.")
        return

    if not FAMILY_MEMBERS:
        await update.message.reply_text("👥 فعلاً عضوی در لیست فمیلی ثبت نشده است.")
        return

    lines = ["👥 اعضای فمیلی:"]
    for i, member_id in enumerate(sorted(FAMILY_MEMBERS), 1):
        lines.append(f"{i}. Telegram ID: {member_id}")
    await update.message.reply_text("\n".join(lines))


async def add_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    if not context.args:
        await update.message.reply_text("استفاده: /addmember TELEGRAM_ID")
        return
    try:
        member_id = int(context.args[0])
        FAMILY_MEMBERS.add(member_id)
        await update.message.reply_text(f"✅ عضو اضافه شد: {member_id}")
    except ValueError:
        await update.message.reply_text("❌ Telegram ID باید عدد باشد.")


async def remove_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    if not context.args:
        await update.message.reply_text("استفاده: /removemember TELEGRAM_ID")
        return
    try:
        member_id = int(context.args[0])
        FAMILY_MEMBERS.discard(member_id)
        await update.message.reply_text(f"✅ عضو حذف شد: {member_id}")
    except ValueError:
        await update.message.reply_text("❌ Telegram ID باید عدد باشد.")


async def rank_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in FAMILY_MEMBERS:
        await update.message.reply_text(
            "⛔ Rank Up فقط برای اعضای فمیلی فعال است."
        )
        return

    context.user_data["step"] = "rankup"
    await update.message.reply_text(
        "⬆️ Rank Up\n\n"
        "درخواست Rank Up خود را بنویسید؛ برای مدیریت ارسال می‌شود."
    )


async def receive_rankup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("step") != "rankup":
        return False

    user = update.effective_user
    text = update.message.text.strip()

    msg = (
        "⬆️ درخواست Rank Up جدید\n\n"
        f"👤 نام: {user.full_name}\n"
        f"🆔 Telegram ID: {user.id}\n\n"
        f"💬 درخواست:\n{text}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)
        context.user_data.clear()
        await update.message.reply_text(
            "✅ درخواست Rank Up برای مدیریت ارسال شد.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
        )
    except Exception:
        await update.message.reply_text(
            "❌ ارسال درخواست Rank Up انجام نشد.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
        )
    return True


# =========================
# Other Menu Buttons
# =========================

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(SUPPORT_TEXT)


async def rank_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RANK_TEXT)


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_TEXT)


async def family_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(BOX_TEXT)


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ABOUT_TEXT)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = ReplyKeyboardMarkup(
        MAIN_MENU,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "❌ عملیات لغو شد.",
        reply_markup=keyboard
    )


# =========================
# Main
# =========================

def main():
    print("Nigan Bot is starting...")

    app = (
        Application.builder()
        .token(TOKEN)
        .proxy(PROXY_URL)
        .get_updates_proxy(PROXY_URL)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", my_id))
    app.add_handler(CommandHandler("id", chat_id))
    app.add_handler(CommandHandler("members", family_members))
    app.add_handler(CommandHandler("addmember", add_member))
    app.add_handler(CommandHandler("removemember", remove_member))
    app.add_handler(CallbackQueryHandler(
        handle_application_decision,
        pattern=r"^(approve|reject):\d+$",
    ))


    app.add_handler(
        MessageHandler(
            filters.Regex("^📝 درخواست عضویت$"),
            start_membership
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex("^🎧 پشتیبانی$"),
            support
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex("^⬆️ Rank Up$"),
            rank_up
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex("^📜 قوانین فمیلی$"),
            rules
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex("^📦 باکس فمیلی$"),
            family_box
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex("^ℹ️ درباره Nigan$"),
            about
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex("^✅ قوانین را می‌پذیرم$"),
            accept_rules
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex("^✅ تأیید درخواست$"),
            send_application
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex("^❌ لغو$"),
            cancel
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            route_special_messages
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
