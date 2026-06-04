import os
import json
import logging
import secrets
import aiohttp
import asyncio
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

# --- الإعدادات ---
ADMIN_ID = 5350291623
BOT_TOKEN = "8751349980:AAEUrWiK5CDIwk92yjHx8TI_-iP828vsCDM"
BOT_USERNAME = "AlliFF_Store_Keysbot"
WEBSITE_URL = "http://localhost:7860"
BOT_API_SECRET = "alliff_bot_api_secret_2026"
API_BASE = f"{WEBSITE_URL}/api/bot"

# حالات المحادثة
REG_USERNAME, REG_PASSWORD = range(2)
ADMIN_LINK_POINTS, ADMIN_LINK_LIMIT = range(2, 4)
ADMIN_ADD_PKG_DAYS, ADMIN_ADD_PKG_BOTS, ADMIN_ADD_PKG_PRICE, ADMIN_ADD_PKG_LIMIT = range(4, 8)
ADMIN_EXTERNAL_URL, ADMIN_EXTERNAL_POINTS, ADMIN_EXTERNAL_LIMIT = range(8, 11)
ADMIN_MANAGE_USER_SEARCH, ADMIN_MANAGE_USER_POINTS = range(11, 13)
ADMIN_BROADCAST_TITLE, ADMIN_BROADCAST_MSG = range(13, 15)
ADMIN_SEND_MSG_USER_ID, ADMIN_SEND_MSG_TITLE, ADMIN_SEND_MSG_BODY = range(15, 18)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ===== دوال API =====

async def api_get(endpoint: str) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/{endpoint}", headers={"x-bot-secret": BOT_API_SECRET}, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    try:
                        data = await resp.json()
                        return {"success": False, "error": data.get("error", f"Status {resp.status}")}
                    except:
                        text = await resp.text()
                        return {"success": False, "error": text or f"Status {resp.status}"}
    except Exception as e:
        logger.error(f"API GET Error ({endpoint}): {e}")
        return {"success": False, "error": str(e)}

async def api_post(endpoint: str, data: dict = None) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_BASE}/{endpoint}", json=data or {}, headers={"x-bot-secret": BOT_API_SECRET, "Content-Type": "application/json"}, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    try:
                        data = await resp.json()
                        return {"success": False, "error": data.get("error", f"Status {resp.status}")}
                    except:
                        text = await resp.text()
                        return {"success": False, "error": text or f"Status {resp.status}"}
    except Exception as e:
        logger.error(f"API POST Error ({endpoint}): {e}")
        return {"success": False, "error": str(e)}

async def api_delete(endpoint: str) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{API_BASE}/{endpoint}", headers={"x-bot-secret": BOT_API_SECRET}, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    try:
                        data = await resp.json()
                        return {"success": False, "error": data.get("error", f"Status {resp.status}")}
                    except:
                        text = await resp.text()
                        return {"success": False, "error": text or f"Status {resp.status}"}
    except Exception as e:
        logger.error(f"API DELETE Error ({endpoint}): {e}")
        return {"success": False, "error": str(e)}

# ===== أوامر المستخدم =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # معالجة روابط النقاط
    if context.args and context.args[0].startswith("points_"):
        link_id = context.args[0].replace("points_", "")
        user_res = await api_get(f"user/{user_id}")
        if not user_res.get("success"):
            await update.message.reply_text("❌ يجب عليك إنشاء حساب أولاً عبر البوت قبل استخدام الروابط.\nأرسل /start للبدء.")
            return ConversationHandler.END
        result = await api_post(f"links/{link_id}/claim", {"telegram_id": user_id})
        if (result.get("success")):
            await update.message.reply_text(f"✅ تم الحصول على {result.get('points_added', 0)} نقطة!\nرصيدك الحالي: {result.get('new_balance', 0)} نقطة.")
        else:
            err = result.get('error', '')
            if "تم الاستخدام مسبقاً" in err:
                msg = "❌ عذراً ولاكنك قمت بلحصول على النقاط من هذا الرابط يرجى تجربت رابط غيره"
            elif "انتهى الحد" in err:
                msg = "⚠️ عذراً هذا الرابط وصل لحده الاقصى"
            else:
                msg = f"❌ فشل: {err or 'خطأ غير معروف'}"
            await update.message.reply_text(msg)
        return ConversationHandler.END

    user_res = await api_get(f"user/{user_id}")
    if user_res.get("success"):
        user = user_res.get("user")
        keyboard = [
            [InlineKeyboardButton("🌐 دخول الموقع", url=WEBSITE_URL)],
            [InlineKeyboardButton("👤 حسابي", callback_data="show_account")],
            [InlineKeyboardButton("🎁 العروض المتاحة", callback_data="list_packages_user")]
        ]
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="admin_panel")])
        
        text = (
            f"أهلاً بك {user.get('username')}! 👋\n"
            f"رصيدك الحالي: {user.get('points', 0)} نقطة.\n"
            f"معرفك في الموقع: `{user.get('userId', 'غير متوفر')}`"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END
    else:
        await update.message.reply_text("مرحباً بك في AlliFF Store! 🚀\nللبدء، أرسل اسم المستخدم الذي تريده (بالإنجليزي، 3 أحرف على الأقل):")
        return REG_USERNAME

async def register_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lower()
    if len(username) < 3 or not username.isalnum():
        await update.message.reply_text("❌ اسم مستخدم غير صالح (أحرف وأرقام فقط)، حاول مرة أخرى:")
        return REG_USERNAME
    context.user_data['reg_username'] = username
    await update.message.reply_text(f"✅ اسم المستخدم: `{username}`\nأرسل كلمة السر (6 أحرف على الأقل):", parse_mode="Markdown")
    return REG_PASSWORD

async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    if len(password) < 6:
        await update.message.reply_text("❌ كلمة سر قصيرة، حاول مرة أخرى:")
        return REG_PASSWORD
    username = context.user_data.get('reg_username')
    user_id = update.effective_user.id
    result = await api_post("register", {"username": username, "password": password, "telegram_id": user_id})
    if result.get("success"):
        await update.message.reply_text(f"✅ تم إنشاء حسابك بنجاح!\n👤 المستخدم: `{username}`\n🔑 السر: `{password}`\n\nاستخدم هذه البيانات في الموقع.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 دخول الموقع", url=WEBSITE_URL)]]))
    else:
        await update.message.reply_text(f"❌ فشل: {result.get('error')}")
    context.user_data.clear()
    return ConversationHandler.END

# ===== لوحة الإدارة =====

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    user_id = query.from_user.id if query else update.effective_user.id
    if user_id != ADMIN_ID: return

    stats_res = await api_get("stats")
    stats = stats_res.get("stats", {})
    
    keyboard = [
        [InlineKeyboardButton("✨ إنشاء رابط نقاط", callback_data="admin_add_link"), InlineKeyboardButton("🌐 رفع رابط للموقع", callback_data="admin_add_external")],
        [InlineKeyboardButton("🌐 عرض روابط الموقع", callback_data="admin_list_links"), InlineKeyboardButton("✨ عرض روابط النقاط", callback_data="admin_list_points")],
        [InlineKeyboardButton("🎁 إضافة عرض مفاتيح", callback_data="admin_add_pkg"), InlineKeyboardButton("📦 عرض العروض", callback_data="admin_list_pkg")],
        [InlineKeyboardButton("👤 إدارة المستخدمين", callback_data="admin_manage_users"), InlineKeyboardButton("👥 عرض المستخدمين", callback_data="admin_list_users")],
        [InlineKeyboardButton("💬 إرسال رسالة", callback_data="admin_send_msg"), InlineKeyboardButton("📢 إذاعة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 تحديث الإحصائيات", callback_data="admin_panel")]
    ]
    
    text = (
        f"🛠️ **لوحة تحكم الآدمن:**\n\n"
        f"👥 المستخدمين: {stats.get('total_users', 0)}\n\n"
        f"🌐 **روابط الموقع:**\n"
        f"   • الإجمالي: {stats.get('website_links', 0)}\n"
        f"   • النشطة: {stats.get('website_links_active', 0)}\n\n"
        f"✨ **روابط النقاط:**\n"
        f"   • الإجمالي: {stats.get('point_links', 0)}\n"
        f"   • النشطة: {stats.get('point_links_active', 0)}\n\n"
        f"📦 العروض: {stats.get('total_packages', 0)}\n\n"
        f"اختر من الخيارات أدناه:"
    )
    
    if query: await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    # أزرار المستخدم العام (تعمل للكل بما فيهم الآدمن)
    if query.data == "show_account":
        u = await api_get(f"user/{user_id}")
        if u.get("success"):
            user = u.get("user")
            text = f"👤 **بيانات حسابك:**\n\nالمستخدم: `{user.get('username')}`\nالنقاط: {user.get('points')}\nمعرف الموقع: `{user.get('userId', 'غير متوفر')}`"
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="start_back")]]))
        return
    elif query.data == "list_packages_user":
        res = await api_get("packages")
        pkgs = res.get("packages", [])
        active_pkgs = [p for p in pkgs if p.get('isActive')]
        if not active_pkgs: await query.edit_message_text("لا توجد عروض حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="start_back")]])); return
        text = "🎁 **العروض المتاحة:**\n\n"
        for p in active_pkgs:
            name = p.get('name')
            is_special = p.get('maxUsers') != -1
            display_name = f"🔥 عرض خاص: {name}" if is_special else name
            text += f"• {display_name} | {p.get('points_price')} نقطة\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="start_back")]]))
        return
    elif query.data == "start_back":
        await start(update, context)
        return

    # أزرار الآدمن فقط
    if user_id != ADMIN_ID: return
    
    if query.data == "admin_panel": return await admin_panel(update, context)
    elif query.data == "admin_add_link": await query.edit_message_text("كم عدد النقاط لكل شخص؟"); return ADMIN_LINK_POINTS
    elif query.data == "admin_add_external": await query.edit_message_text("أرسل الرابط الذي تريد رفعه على الموقع:"); return ADMIN_EXTERNAL_URL
    elif query.data == "admin_add_pkg": await query.edit_message_text("كم عدد الأيام للمفتاح؟"); return ADMIN_ADD_PKG_DAYS
    elif query.data == "admin_manage_users": await query.edit_message_text("أرسل اسم المستخدم أو الآيدي (مثال: 10000001) للبحث عنه وإدارته:"); return ADMIN_MANAGE_USER_SEARCH
    elif query.data == "admin_broadcast": await query.edit_message_text("أرسل عنوان الرسالة (الإذاعة):"); return ADMIN_BROADCAST_TITLE
    elif query.data == "admin_send_msg": await query.edit_message_text("أرسل الـ ID الخاص بالمستخدم في الموقع:"); return ADMIN_SEND_MSG_USER_ID
    
    elif query.data == "admin_list_links":
        try:
            res = await api_get("links")
            links = res.get("links", [])
            # تصفية الروابط التي تحتوي على رابط خارجي فقط (الروابط المرفوعة للموقع)
            external_links = [l for l in links if l.get('externalUrl')]
            if not external_links:
                await query.edit_message_text("لا توجد روابط مرفوعة للموقع حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="admin_panel")]]))
                return
            
            text = "🌐 *روابط الموقع المرفوعة:*\n\n"
            keyboard = []
            for l in external_links[:15]:
                l_id, pts, used, mx, ext = l.get('linkId'), l.get('pointsPerUse'), l.get('usedCount'), l.get('maxUsers'), l.get('externalUrl')
                # تنظيف الرابط من الرموز التي قد تسبب خطأ في MarkdownV2
                safe_ext = ext.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
                info = f"{pts}نق | {used}/{mx}"
                text += f"• {info}\n🔗 {safe_ext}\n\n"
                keyboard.append([InlineKeyboardButton(f"❌ حذف ({info})", callback_data=f"del_link_{l_id}")])
            
            keyboard.append([InlineKeyboardButton("🔙 عودة", callback_data="admin_panel")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2", disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Error in admin_list_links: {e}")
            await query.answer("حدث خطأ في جلب الروابط", show_alert=True)

    elif query.data == "admin_list_points":
        try:
            res = await api_get("links")
            links = res.get("links", [])
            # تصفية الروابط التي لا تحتوي على رابط خارجي (روابط النقاط الداخلية)
            point_links = [l for l in links if not l.get('externalUrl')]
            if not point_links:
                await query.edit_message_text("لا توجد روابط نقاط حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="admin_panel")]]))
                return
            
            text = "✨ **روابط النقاط الداخلية:**\n\n"
            keyboard = []
            for l in point_links[:15]:
                l_id, pts, used, mx = l.get('linkId'), l.get('pointsPerUse'), l.get('usedCount'), l.get('maxUsers')
                info = f"{pts}نق | {used}/{mx}"
                text += f"• {info}\n🔗 `https://t.me/{BOT_USERNAME}?start=points_{l_id}`\n\n"
                keyboard.append([InlineKeyboardButton(f"❌ حذف ({info})", callback_data=f"del_link_{l_id}")])
            
            keyboard.append([InlineKeyboardButton("🔙 عودة", callback_data="admin_panel")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception as e:
            print(f"Error in admin_list_points: {e}")
            await query.answer("حدث خطأ", show_alert=True)
        
    elif query.data == "admin_list_pkg":
        res = await api_get("packages")
        pkgs = res.get("packages", [])
        if not pkgs:
            await query.edit_message_text("لا توجد عروض حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="admin_panel")]]))
            return
            
        text = "📦 **العروض الحالية:**\n\n"
        keyboard = []
        for p in pkgs:
            name = p.get('name')
            is_special = p.get('maxUsers') != -1
            display_name = f"🔥 عرض خاص: {name}" if is_special else name
            text += f"• {display_name} | {p.get('points_price')}نق\n"
            keyboard.append([InlineKeyboardButton(f"❌ حذف {display_name}", callback_data=f"del_pkg_{p.get('id')}")])
            
        keyboard.append([InlineKeyboardButton("🔙 عودة", callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "admin_list_users":
        res = await api_get("users")
        users = res.get("users", [])
        if not users: await query.edit_message_text("لا يوجد مستخدمين حالياً."); return
        text = "👥 **قائمة المستخدمين:**\n\n"
        for u in users[:30]:
            text += f"• {u.get('username')} | ID: `{u.get('userId')}` | {u.get('points')}نق\n"
        if len(users) > 30: text += f"\n... وأكثر ({len(users)} إجمالي)"
        keyboard = [[InlineKeyboardButton("🔙 عودة", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("del_link_"):
        await api_delete(f"links/{query.data.replace('del_link_', '')}")
        await query.edit_message_text("✅ تم الحذف.")
        await asyncio.sleep(1)
        return await admin_panel(update, context)
        
    elif query.data.startswith("del_pkg_"):
        await api_delete(f"packages/{query.data.replace('del_pkg_', '')}")
        await query.edit_message_text("✅ تم الحذف.")
        await asyncio.sleep(1)
        return await admin_panel(update, context)
        
    elif query.data.startswith("user_pts_"):
        u_id = query.data.replace("user_pts_", "")
        context.user_data['edit_user_id'] = u_id
        await query.edit_message_text("أرسل عدد النقاط الجديد للمستخدم:")
        return ADMIN_MANAGE_USER_POINTS

# --- منطق الإدخال للإدارة ---

async def admin_get_link_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: context.user_data['pts'] = int(update.message.text)
    except: await update.message.reply_text("أرسل رقم صحيح:"); return ADMIN_LINK_POINTS
    await update.message.reply_text("الرابط لكم شخص؟")
    return ADMIN_LINK_LIMIT

async def admin_get_link_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: limit = int(update.message.text)
    except: await update.message.reply_text("أرسل رقم صحيح:"); return ADMIN_LINK_LIMIT
    pts = context.user_data.get('pts')
    res = await api_post("links", {"points_per_use": pts, "max_users": limit, "external_url": None})
    if res.get("success"):
        await update.message.reply_text(f"✅ تم إنشاء الرابط:\n`https://t.me/{BOT_USERNAME}?start=points_{res.get('link_id')}`", parse_mode="Markdown")
    else: await update.message.reply_text(f"❌ فشل: {res.get('error')}")
    context.user_data.clear(); return ConversationHandler.END

async def admin_ext_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"): await update.message.reply_text("أرسل رابط صحيح:"); return ADMIN_EXTERNAL_URL
    context.user_data['ext_url'] = url
    await update.message.reply_text("الرابط كم نقطة؟")
    return ADMIN_EXTERNAL_POINTS

async def admin_ext_pts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: context.user_data['ext_pts'] = int(update.message.text)
    except: await update.message.reply_text("أرسل رقم صحيح:"); return ADMIN_EXTERNAL_POINTS
    await update.message.reply_text("الرابط لكم شخص؟")
    return ADMIN_EXTERNAL_LIMIT

async def admin_ext_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: limit = int(update.message.text)
    except: await update.message.reply_text("أرسل رقم صحيح:"); return ADMIN_EXTERNAL_LIMIT
    url, pts = context.user_data.get('ext_url'), context.user_data.get('ext_pts')
    res = await api_post("links", {"points_per_use": pts, "max_users": limit, "external_url": url})
    if res.get("success"):
        await update.message.reply_text(f"✅ تم رفع الرابط للموقع بنجاح!\n🔗 {url}\n💰 {pts}نق | 👥 {limit} شخص")
    else: await update.message.reply_text(f"❌ فشل: {res.get('error')}")
    context.user_data.clear(); return ConversationHandler.END

async def admin_broadcast_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['broadcast_title'] = update.message.text
    await update.message.reply_text("الآن أرسل محتوى الرسالة (الإذاعة):")
    return ADMIN_BROADCAST_MSG

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    title = context.user_data.get('broadcast_title', 'إعلان مهم')
    res = await api_post("broadcast", {"title": title, "message": message_text})
    if res.get("success"): await update.message.reply_text(f"✅ {res.get('message')}")
    else: await update.message.reply_text(f"❌ فشل: {res.get('error')}")
    context.user_data.clear(); return ConversationHandler.END

async def admin_send_msg_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text)
        context.user_data['send_msg_user_id'] = user_id
        await update.message.reply_text("الآن أرسل عنوان الرسالة:")
        return ADMIN_SEND_MSG_TITLE
    except: await update.message.reply_text("أرسل رقم صحيح:"); return ADMIN_SEND_MSG_USER_ID

async def admin_send_msg_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['send_msg_title'] = update.message.text
    await update.message.reply_text("الآن أرسل محتوى الرسالة:")
    return ADMIN_SEND_MSG_BODY

async def admin_send_msg_body(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    user_id = context.user_data.get('send_msg_user_id')
    title = context.user_data.get('send_msg_title')
    res = await api_post(f"users/custom/{user_id}/send-message", {"title": title, "message": message_text})
    if res.get("success"): await update.message.reply_text(f"✅ {res.get('message')}")
    else: await update.message.reply_text(f"❌ فشل: {res.get('error')}")
    context.user_data.clear(); return ConversationHandler.END

# --- وظائف الإدارة الأخرى ---
async def admin_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_term = update.message.text.strip()
    user = None
    
    # محاولة البحث بالآيدي أولاً
    if search_term.isdigit():
        res = await api_get("users")
        users = res.get("users", [])
        user = next((u for u in users if str(u.get('userId')) == search_term), None)
    
    # إذا لم يجد بالآيدي، يبحث بالاسم
    if not user:
        res = await api_get(f"users/search/{search_term.lower()}")
        if res.get("success"):
            user = res.get("user")

    if user:
        u_id = user.get('id')
        text = f"👤 **إدارة المستخدم:**\nالمستخدم: `{user.get('username')}`\nالنقاط: {user.get('points')}\nالمعرف: `{user.get('userId')}`"
        keyboard = [[InlineKeyboardButton("💰 تعديل النقاط", callback_data=f"user_pts_{u_id}")], [InlineKeyboardButton("🔙 عودة", callback_data="admin_panel")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ADMIN_MANAGE_USER_SEARCH # نبقى في حالة البحث للسماح بالضغط على الزر
    else: 
        await update.message.reply_text("❌ لم يتم العثور على المستخدم بالاسم أو الآيدي.")
        return ConversationHandler.END

async def admin_edit_user_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pts = int(update.message.text)
        u_id = context.user_data.get('edit_user_id')
        res = await api_post(f"users/{u_id}/points", {"points": pts})
        if res.get("success"):
            await update.message.reply_text(f"✅ تم تحديث رصيد المستخدم إلى {pts} نقطة.")
        else:
            await update.message.reply_text(f"❌ فشل التحديث: {res.get('error')}")
    except ValueError:
        await update.message.reply_text("❌ يرجى إرسال رقم صحيح:")
        return ADMIN_MANAGE_USER_POINTS
    context.user_data.clear()
    return ConversationHandler.END

async def admin_pkg_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: context.user_data['d'] = int(update.message.text)
    except: return ADMIN_ADD_PKG_DAYS
    await update.message.reply_text("كم بوت؟"); return ADMIN_ADD_PKG_BOTS

async def admin_pkg_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: context.user_data['b'] = int(update.message.text)
    except: return ADMIN_ADD_PKG_BOTS
    await update.message.reply_text("كم السعر؟"); return ADMIN_ADD_PKG_PRICE

async def admin_pkg_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: context.user_data['p'] = int(update.message.text)
    except: return ADMIN_ADD_PKG_PRICE
    await update.message.reply_text("الحد؟ (-1 لغير محدود)"); return ADMIN_ADD_PKG_LIMIT

async def admin_pkg_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: lim = int(update.message.text)
    except: return ADMIN_ADD_PKG_LIMIT
    d, b, p = context.user_data.get('d'), context.user_data.get('b'), context.user_data.get('p')
    await api_post("packages", {"name": f"{d} يوم - {b} بوت", "duration_days": d, "bot_count": b, "points_price": p, "max_users": lim})
    await update.message.reply_text("✅ تم إضافة العرض"); context.user_data.clear(); return ConversationHandler.END

def main():
    # إعدادات الاتصال الآمن
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
    app = Application.builder().token(BOT_TOKEN).request(request).build()
    
    # معالجات المحادثات
    # معالجات الأزرار البسيطة أولاً لضمان الاستجابة السريعة
    app.add_handler(CallbackQueryHandler(start, pattern="^start_back$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(admin_list_links|admin_list_points|admin_list_pkg|admin_list_users|show_account|list_packages_user|del_link_|del_pkg_|user_pts_).*$"))

    # معالجات المحادثات (التي تتطلب إدخال نص)
    app.add_handler(ConversationHandler(entry_points=[CommandHandler('start', start)], states={REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_username)], REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)]}, fallbacks=[CommandHandler('start', start)]))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(admin_callback, pattern="^admin_add_link$")], states={ADMIN_LINK_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_link_points)], ADMIN_LINK_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_link_limit)]}, fallbacks=[CommandHandler('start', start)], per_message=False))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(admin_callback, pattern="^admin_add_external$")], states={ADMIN_EXTERNAL_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ext_url)], ADMIN_EXTERNAL_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ext_pts)], ADMIN_EXTERNAL_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ext_limit)]}, fallbacks=[CommandHandler('start', start)], per_message=False))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(admin_callback, pattern="^admin_add_pkg$")], states={ADMIN_ADD_PKG_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_pkg_days)], ADMIN_ADD_PKG_BOTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_pkg_bots)], ADMIN_ADD_PKG_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_pkg_price)], ADMIN_ADD_PKG_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_pkg_limit)]}, fallbacks=[CommandHandler('start', start)], per_message=False))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(admin_callback, pattern="^admin_broadcast$")], states={ADMIN_BROADCAST_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_title)], ADMIN_BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast)]}, fallbacks=[CommandHandler('start', start)], per_message=False))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(admin_callback, pattern="^admin_send_msg$")], states={ADMIN_SEND_MSG_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_msg_user_id)], ADMIN_SEND_MSG_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_msg_title)], ADMIN_SEND_MSG_BODY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_msg_body)]}, fallbacks=[CommandHandler('start', start)], per_message=False))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(admin_callback, pattern="^admin_manage_users$")], states={ADMIN_MANAGE_USER_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_user_search)], ADMIN_MANAGE_USER_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_user_points)]}, fallbacks=[CommandHandler('start', start)], per_message=False))

    app.add_handler(CommandHandler('admin', admin_panel))
    app.add_handler(CallbackQueryHandler(admin_callback))
    
    logger.info("🚀 Bot is running...")
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"❌ Bot Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__': main()
