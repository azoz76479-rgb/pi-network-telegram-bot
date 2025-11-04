import os
import telebot
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import time
import logging
import requests
from pymongo import MongoClient

# ✅ تفعيل السجلات
logging.basicConfig(level=logging.INFO)
print("🚀 Starting Pi Network Bot...")

# فحص BOT_TOKEN
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found!")
    exit(1)

# 🔗 اتصال MongoDB
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    print("❌ MONGO_URI not found!")
    exit(1)

try:
    client = MongoClient(MONGO_URI)
    db = client['pi_network_bot']
    users_collection = db['users']
    vip_packages_collection = db['vip_packages']
    deposit_requests_collection = db['deposit_requests']
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ MongoDB error: {e}")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# 🔐 إعدادات المشرفين
ADMIN_IDS = [8400225549]
YOUR_USER_ID = 8400225549

# 🔷 إعدادات Pi Network
PI_WALLET = "0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b"
PI_PRICE = 35.50
LAUNCH_DATE = "31/12/2025"

def is_admin(user_id):
    return user_id in ADMIN_IDS

# 🎯 باقات VIP
VIP_PACKAGES = {
    1: {"name": "🟢 الباقة الأساسية", "price": 30, "daily_bonus": 0.25, "duration": 10},
    2: {"name": "🔵 الباقة المتوسطة", "price": 60, "daily_bonus": 0.50, "duration": 10},
    3: {"name": "🟡 الباقة المتقدمة", "price": 90, "daily_bonus": 0.75, "duration": 10},
    4: {"name": "🟣 الباقة الذهبية", "price": 120, "daily_bonus": 1.00, "duration": 10},
    5: {"name": "🔴 الباقة المميزة", "price": 150, "daily_bonus": 1.25, "duration": 10}
}

def get_user(user_id):
    user_id_str = str(user_id)
    try:
        user_data = users_collection.find_one({"user_id": user_id_str})
        if user_data:
            user_data.pop('_id', None)
            return user_data
        else:
            new_user = {
                'user_id': user_id_str,
                'first_name': "", 
                'username': "",
                'balance': 10.0,
                'referral_count': 0, 
                'active_referrals': 0,
                'total_earnings': 10.0,
                'total_deposits': 0.0,
                'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_daily_bonus': None,
                'vip_packages': [],
                'is_banned': False,
                'language': 'ar'
            }
            users_collection.insert_one(new_user)
            send_welcome_message(user_id_str)
            return new_user
    except Exception as e:
        print(f"❌ Error getting user: {e}")
        return None

def update_user(user_id, **kwargs):
    try:
        user_id_str = str(user_id)
        users_collection.update_one({"user_id": user_id_str}, {"$set": kwargs})
        return True
    except Exception as e:
        print(f"❌ Error updating user: {e}")
        return False

def send_welcome_message(user_id):
    welcome_text = """
🎉 **مرحباً بك في مجتمع Pi Network!**

🌐 **ما هي Pi Network؟**
Pi هي عملة رقمية ثورية يمكن تعدينها من هاتفك المحمول دون استهلاك البطارية أو البيانات.

🚀 **لماذا Pi Network؟**
• ✅ **مجانية بالكامل** - لا تطلب أي رسوم
• 📱 **صديقة للبيئة** - لا تستهلك طاقة
• 👥 **مركزية للمجتمع** - توزيع عادل للثروة
• 🔒 **آمنة ومشفرة** - تقنية blockchain متطورة

💎 **قيمة Pi الحالية:**
• **1 Pi = {price} USDT**
• **التداول يبدأ رسمياً في {launch_date}**

🔗 **انضم إلى الثورة الرقمية وكن جزءاً من المستقبل!**
    """.format(price=PI_PRICE, launch_date=LAUNCH_DATE)
    
    try:
        bot.send_message(user_id, welcome_text)
    except Exception as e:
        print(f"❌ Failed to send welcome message: {e}")

def handle_referral_system(message):
    try:
        user_id = message.from_user.id
        command_parts = message.text.split()
        
        if len(command_parts) > 1 and command_parts[1].startswith('ref'):
            try:
                referrer_id = int(command_parts[1][3:])
                if referrer_id != user_id:
                    referrer = get_user(referrer_id)
                    if referrer and referrer['active_referrals'] < 20:
                        new_balance = referrer['balance'] + 0.50
                        new_active_refs = referrer['active_referrals'] + 1
                        
                        update_user(referrer_id,
                            balance=new_balance,
                            total_earnings=referrer['total_earnings'] + 0.50,
                            referral_count=referrer['referral_count'] + 1,
                            active_referrals=new_active_refs
                        )
                        notify_referral_earned(referrer_id, new_active_refs)
            except ValueError:
                pass
    except Exception as e:
        print(f"❌ Referral error: {e}")

def notify_referral_earned(user_id, referral_count):
    notification = f"""
🎉 **إحالة جديدة!**

👤 تمت إضافة مستخدم جديد عبر رابطك
💰 **المكافأة:** 0.50 Pi
📊 **الإحالة رقم:** {referral_count}/20

💎 **رصيدك الجديد:** {get_user(user_id)['balance']:.2f} Pi
    """
    
    try:
        bot.send_message(user_id, notification)
    except Exception as e:
        print(f"❌ Failed to send referral notification: {e}")

def get_membership_days(user_id):
    user = get_user(user_id)
    if not user: 
        return 0, 10
    
    try:
        reg_date = datetime.strptime(user['registration_date'].split()[0], '%Y-%m-%d')
        days_registered = (datetime.now() - reg_date).days + 1
        return days_registered, 10
    except:
        return 1, 10

def get_total_balance_value(balance):
    return balance * PI_PRICE

def can_withdraw(user_id):
    days_registered, _ = get_membership_days(user_id)
    current_date = datetime.now()
    launch_date = datetime(2025, 12, 31)
    
    return days_registered >= 10 and current_date >= launch_date

def show_main_menu(chat_id, message_id=None, user_id=None):
    try:
        if not user_id: 
            return False
            
        user_data = get_user(user_id)
        if not user_data or user_data.get('is_banned', False):
            return False
        
        days_registered, total_days = get_membership_days(user_id)
        total_value = get_total_balance_value(user_data['balance'])
        membership = "🟢 مجاني"
        if user_data.get('vip_packages'):
            membership = "💎 VIP"
        
        profile_text = f"""
💰 <b>الرصيد:</b> {user_data['balance']:.2f} Pi
👑 <b>العضوية:</b> {membership}
📅 <b>الأيام:</b> {days_registered}/10 يوم
🚀 <b>الإطلاق:</b> {LAUNCH_DATE}

💵 <b>السعر الحالي:</b> 1 Pi = {PI_PRICE} USDT
📈 <b>القيمة الإجمالية:</b> {total_value:,.2f} USDT
        """
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎁 المكافأة اليومية", callback_data="daily_bonus"),
            InlineKeyboardButton("⛏️ التعدين", callback_data="mining")
        )
        keyboard.add(
            InlineKeyboardButton("💎 الباقات", callback_data="vip_packages"),
            InlineKeyboardButton("👥 الإحالات", callback_data="referral")
        )
        keyboard.add(
            InlineKeyboardButton("💳 الإيداع", callback_data="deposit"),
            InlineKeyboardButton("💰 السحب", callback_data="withdraw")
        )
        
        if message_id:
            bot.edit_message_text(profile_text, chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
        else:
            bot.send_message(chat_id, profile_text, reply_markup=keyboard)
        return True
        
    except Exception as e:
        print(f"❌ Menu error: {e}")
        return False

# 🎯 الأوامر الأساسية
@bot.message_handler(commands=['start', 'profile'])
def handle_start(message):
    try:
        user_id = message.from_user.id
        handle_referral_system(message)
        update_user(user_id, 
                   first_name=message.from_user.first_name or "", 
                   username=message.from_user.username or "", 
                   last_activity=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        show_main_menu(message.chat.id, user_id=user_id)
    except Exception as e:
        print(f"❌ Start error: {e}")

# 💎 نظام الباقات VIP
@bot.callback_query_handler(func=lambda call: call.data == "vip_packages")
def show_vip_packages(call):
    try:
        packages_text = """
💎 <b>باقات VIP المتاحة:</b>

🟢 <b>الباقة الأساسية - 30 Pi</b>
• مكافأة يومية: 0.25 Pi
• مدة: 10 أيام

🔵 <b>الباقة المتوسطة - 60 Pi</b>  
• مكافأة يومية: 0.50 Pi
• مدة: 10 أيام

🟡 <b>الباقة المتقدمة - 90 Pi</b>
• مكافأة يومية: 0.75 Pi  
• مدة: 10 أيام

🟣 <b>الباقة الذهبية - 120 Pi</b>
• مكافأة يومية: 1.00 Pi
• مدة: 10 أيام

🔴 <b>الباقة المميزة - 150 Pi</b>
• مكافأة يومية: 1.25 Pi
• مدة: 10 أيام
        """
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        for package_id, package in VIP_PACKAGES.items():
            keyboard.add(InlineKeyboardButton(
                f"{package['name']} - {package['price']} Pi", 
                callback_data=f"buy_package_{package_id}"
            ))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        
        bot.edit_message_text(packages_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ VIP packages error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_package_'))
def handle_buy_package(call):
    try:
        package_id = int(call.data.replace('buy_package_', ''))
        package = VIP_PACKAGES.get(package_id)
        
        if not package:
            bot.answer_callback_query(call.id, "❌ الباقة غير متاحة!")
            return
        
        user = get_user(call.from_user.id)
        if user['balance'] < package['price']:
            bot.answer_callback_query(call.id, f"❌ رصيدك غير كافي! تحتاج {package['price']} Pi")
            return
        
        send_purchase_request(call.from_user.id, package)
        bot.answer_callback_query(call.id, f"✅ تم إرسال طلب شراء {package['name']} للمسؤول")
        
    except Exception as e:
        print(f"❌ Buy package error: {e}")

def send_purchase_request(user_id, package):
    user = get_user(user_id)
    user_link = f"<a href='tg://user?id={user_id}'>{user['first_name'] or 'مستخدم'}</a>"
    
    request_text = f"""
🆕 <b>طلب شراء باقة جديدة</b>

👤 <b>المستخدم:</b> {user_link}
🆔 <b>الآيدي:</b> <code>{user_id}</code>
📞 <b>رابط التواصل:</b> <a href='tg://user?id={user_id}'>اضغط للتواصل</a>

💎 <b>الباقة:</b> {package['name']}
💰 <b>السعر:</b> {package['price']} Pi
🎁 <b>المكافأة اليومية:</b> {package['daily_bonus']} Pi
📅 <b>المدة:</b> {package['duration']} أيام

💵 <b>رصيده الحالي:</b> {user['balance']:.2f} Pi
👥 <b>إحالاته:</b> {user['referral_count']}
    """
    
    try:
        bot.send_message(YOUR_USER_ID, request_text)
    except Exception as e:
        print(f"❌ Failed to send purchase request: {e}")

# 💳 نظام الإيداع - معدل لـ BEP20
@bot.callback_query_handler(func=lambda call: call.data == "deposit")
def handle_deposit(call):
    try:
        deposit_text = f"""
💳 <b>نظام الإيداع</b>

📍 <b>عنوان المحفظة (BEP20):</b>
<code>{PI_WALLET}</code>

✅ <b>تعليمات الإيداع:</b>
• استخدم شبكة <b>BEP20 فقط</b>
• تأكد من إرسال USDT فقط
• الحد الأدنى: 10 USDT

📋 <b>بعد الإيداع:</b>
1. أرسل صورة إثبات التحويل
2. انتظر موافقة المسؤول
3. سيتم إضافة الرصيد خلال ساعة

📸 <b>لإرسال صورة الإيداع:</b>
استخدم الأمر /deposit_proof
        """
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📋 نسخ العنوان", callback_data="copy_wallet"))
        keyboard.add(InlineKeyboardButton("📸 إرسال إثبات الإيداع", callback_data="send_deposit_proof"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        
        bot.edit_message_text(deposit_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ Deposit error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "copy_wallet")
def handle_copy_wallet(call):
    bot.answer_callback_query(call.id, f"✅ تم نسخ العنوان: {PI_WALLET}")

@bot.callback_query_handler(func=lambda call: call.data == "send_deposit_proof")
def handle_send_deposit_proof(call):
    try:
        bot.answer_callback_query(call.id, "📸 أرسل صورة إثبات الإيداع الآن")
        bot.send_message(call.message.chat.id, "📸 <b>أرسل صورة إثبات الإيداع الآن</b>\n\nاستخدم الأمر /deposit_proof أو أرسل الصورة مباشرة")
    except Exception as e:
        print(f"❌ Send deposit proof error: {e}")

# 📸 نظام إرسال إثباتات الإيداع
@bot.message_handler(commands=['deposit_proof'])
def handle_deposit_proof_command(message):
    try:
        bot.reply_to(message, "📸 <b>أرسل صورة إثبات الإيداع الآن</b>\n\nسأقوم بإرسالها للمسؤول للموافقة")
        bot.register_next_step_handler(message, process_deposit_proof)
    except Exception as e:
        print(f"❌ Deposit proof command error: {e}")

def process_deposit_proof(message):
    try:
        if message.photo:
            # حفظ طلب الإيداع في قاعدة البيانات
            deposit_request = {
                'user_id': str(message.from_user.id),
                'first_name': message.from_user.first_name or "",
                'username': message.from_user.username or "",
                'photo_file_id': message.photo[-1].file_id,
                'status': 'pending',
                'submission_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'admin_action': None,
                'action_date': None
            }
            
            deposit_requests_collection.insert_one(deposit_request)
            
            # إرسال للإدمن للموافقة
            send_deposit_for_approval(message.from_user.id, message.photo[-1].file_id)
            
            bot.reply_to(message, "✅ <b>تم إرسال طلب الإيداع للمسؤول</b>\n\nسيتم مراجعة طلبك والرد عليك خلال 24 ساعة")
            
        else:
            bot.reply_to(message, "❌ <b>لم ترسل صورة!</b>\n\nأرسل صورة إثبات الإيداع")
            bot.register_next_step_handler(message, process_deposit_proof)
            
    except Exception as e:
        print(f"❌ Process deposit proof error: {e}")
        bot.reply_to(message, "❌ حدث خطأ أثناء معالجة الطلب")

def send_deposit_for_approval(user_id, file_id):
    """إرسال طلب الإيداع للإدمن للموافقة"""
    try:
        user = get_user(user_id)
        user_link = f"<a href='tg://user?id={user_id}'>{user['first_name'] or 'مستخدم'}</a>"
        
        approval_text = f"""
🆕 <b>طلب إيداع جديد</b>

👤 <b>المستخدم:</b> {user_link}
🆔 <b>الآيدي:</b> <code>{user_id}</code>
📅 <b>وقت الطلب:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💵 <b>رصيده الحالي:</b> {user['balance']:.2f} Pi
👥 <b>إحالاته:</b> {user['referral_count']}

📝 <b>اختر الإجراء:</b>
        """
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("✅ الموافقة على الإيداع", callback_data=f"approve_deposit_{user_id}"),
            InlineKeyboardButton("❌ رفض الإيداع", callback_data=f"reject_deposit_{user_id}")
        )
        
        # إرسال الصورة مع النص
        bot.send_photo(
            YOUR_USER_ID,
            photo=file_id,
            caption=approval_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"❌ Send deposit for approval error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_deposit_'))
def handle_approve_deposit(call):
    try:
        user_id = int(call.data.replace('approve_deposit_', ''))
        
        # تحديث حالة الطلب في قاعدة البيانات
        deposit_requests_collection.update_one(
            {'user_id': str(user_id), 'status': 'pending'},
            {'$set': {
                'status': 'approved',
                'admin_action': 'approved',
                'action_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }}
        )
        
        # إرسال إشعار للمستخدم
        bot.send_message(user_id, "✅ <b>تمت الموافقة على إيداعك!</b>\n\nتم إضافة الرصيد إلى حسابك بنجاح")
        
        # الرد على الإدمن
        bot.answer_callback_query(call.id, "✅ تمت الموافقة على الإيداع")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, f"✅ <b>تمت الموافقة على إيداع المستخدم</b> {user_id}")
        
    except Exception as e:
        print(f"❌ Approve deposit error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_deposit_'))
def handle_reject_deposit(call):
    try:
        user_id = int(call.data.replace('reject_deposit_', ''))
        
        # تحديث حالة الطلب في قاعدة البيانات
        deposit_requests_collection.update_one(
            {'user_id': str(user_id), 'status': 'pending'},
            {'$set': {
                'status': 'rejected',
                'admin_action': 'rejected',
                'action_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }}
        )
        
        # إرسال إشعار للمستخدم
        bot.send_message(user_id, "❌ <b>تم رفض طلب الإيداع</b>\n\nيرجى التحقق من صحة المعلومات والمحاولة مرة أخرى")
        
        # الرد على الإدمن
        bot.answer_callback_query(call.id, "❌ تم رفض الإيداع")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, f"❌ <b>تم رفض إيداع المستخدم</b> {user_id}")
        
    except Exception as e:
        print(f"❌ Reject deposit error: {e}")

# 💰 نظام السحب
@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def handle_withdraw(call):
    try:
        user_id = call.from_user.id
        user = get_user(user_id)
        days_registered, _ = get_membership_days(user_id)
        
        if not can_withdraw(user_id):
            withdraw_text = f"""
💰 <b>نظام السحب</b>

❌ <b>غير متاح حالياً</b>

📅 <b>شروط السحب:</b>
• 10 أيام عضوية ({days_registered}/10)
• بعد تاريخ الإطلاق ({LAUNCH_DATE})

💡 <b>معلومات مهمة:</b>
• السحب سيكون متاحاً بعد الإطلاق الرسمي
• استمر في جمع Pi لزيادة أرباحك
• ترقب الإعلانات الرسمية
            """
        else:
            withdraw_text = f"""
💰 <b>نظام السحب</b>

✅ <b>متاح الآن!</b>

💵 <b>رصيدك:</b> {user['balance']:.2f} Pi
💎 <b>قيمته:</b> {get_total_balance_value(user['balance']):,.2f} USDT

📝 <b>للسحب:</b>
1. اختر المبلغ أدناه
2. سيتم التواصل معك
3. استلم أموالك خلال 24 ساعة
            """
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        if can_withdraw(user_id):
            keyboard.add(
                InlineKeyboardButton("💰 سحب 50 Pi", callback_data="withdraw_50"),
                InlineKeyboardButton("💰 سحب 100 Pi", callback_data="withdraw_100"),
                InlineKeyboardButton("💰 سحب كل الرصيد", callback_data="withdraw_all")
            )
        
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        
        bot.edit_message_text(withdraw_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
        
    except Exception as e:
        print(f"❌ Withdraw error: {e}")

# 👥 نظام الإحالات - معدل مع رابط البوت الجديد
@bot.callback_query_handler(func=lambda call: call.data == "referral")
def handle_referral(call):
    try:
        user_id = call.from_user.id
        user = get_user(user_id)
        referral_link = f"https://t.me/pi_network_1bot?start=ref{user_id}"
        
        referral_text = f"""
👥 <b>نظام الإحالات</b>

🔗 <b>رابط الدعوة:</b>
<code>{referral_link}</code>

📊 <b>إحصائياتك:</b>
• إجمالي الإحالات: {user['referral_count']}
• الإحالات النشطة: {user['active_referrals']}/20
• إجمالي الأرباح: {user['active_referrals'] * 0.50:.2f} Pi

💰 <b>مكافآت الإحالات:</b>
• 0.50 Pi لكل إحالة جديدة
• حتى 20 إحالة فقط
• دخل إضافي مستمر

🎯 <b>شارك الرابط واكسب المزيد!</b>
        """
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={referral_link}"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        
        bot.edit_message_text(referral_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
        
    except Exception as e:
        print(f"❌ Referral error: {e}")

# 🔄 زر الرجوع
@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    show_main_menu(call.message.chat.id, call.message.message_id, call.from_user.id)

# 🛠️ أوامر الإدمن
@bot.message_handler(commands=['admin'])
def handle_admin(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ إيداع رصيد", callback_data="admin_deposit"),
        InlineKeyboardButton("➖ سحب رصيد", callback_data="admin_withdraw")
    )
    keyboard.add(
        InlineKeyboardButton("💎 إضافة باقة", callback_data="admin_add_package"),
        InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban_user")
    )
    keyboard.add(
        InlineKeyboardButton("✅ فك حظر", callback_data="admin_unban_user"),
        InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")
    )
    
    bot.reply_to(message, "🛠️ <b>لوحة تحكم الإدمن</b>", reply_markup=keyboard)

@bot.message_handler(commands=['addbalance'])
def handle_addbalance(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "📝 استخدام: /addbalance [user_id] [amount]")
            return
        
        target_user_id, amount = parts[1], float(parts[2])
        user = get_user(target_user_id)
        
        if not user:
            bot.reply_to(message, "❌ المستخدم غير موجود!")
            return
        
        new_balance = user['balance'] + amount
        update_user(target_user_id, balance=new_balance, total_earnings=user['total_earnings'] + amount)
        
        bot.reply_to(message, f"✅ تم إضافة {amount} Pi للمستخدم {target_user_id}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['ban'])
def handle_ban(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "📝 استخدام: /ban [user_id]")
            return
        
        target_user_id = parts[1]
        user = get_user(target_user_id)
        
        if not user:
            bot.reply_to(message, "❌ المستخدم غير موجود!")
            return
        
        update_user(target_user_id, is_banned=True)
        bot.reply_to(message, f"✅ تم حظر المستخدم {target_user_id}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['unban'])
def handle_unban(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "📝 استخدام: /unban [user_id]")
            return
        
        target_user_id = parts[1]
        user = get_user(target_user_id)
        
        if not user:
            bot.reply_to(message, "❌ المستخدم غير موجود!")
            return
        
        update_user(target_user_id, is_banned=False)
        bot.reply_to(message, f"✅ تم فك حظر المستخدم {target_user_id}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 🎁 المكافأة اليومية والتعدين
@bot.callback_query_handler(func=lambda call: call.data == "daily_bonus")
def handle_daily_bonus(call):
    try:
        user = get_user(call.from_user.id)
        current_time = datetime.now()
        
        base_bonus = 0.7
        package_bonus = 0
        if user.get('vip_packages'):
            for package in user['vip_packages']:
                package_bonus += package.get('daily_bonus', 0)
        
        total_bonus = base_bonus + package_bonus
        
        if user.get('last_daily_bonus'):
            last_bonus = datetime.strptime(user['last_daily_bonus'], '%Y-%m-%d %H:%M:%S')
            if (current_time - last_bonus).total_seconds() < 24 * 3600:
                next_bonus = last_bonus + timedelta(hours=24)
                time_left = next_bonus - current_time
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                
                bot.answer_callback_query(
                    call.id, 
                    f"⏳ انتظر {hours:02d}:{minutes:02d} للمكافأة التالية", 
                    show_alert=True
                )
                return
        
        new_balance = user['balance'] + total_bonus
        update_user(
            call.from_user.id,
            balance=new_balance,
            total_earnings=user['total_earnings'] + total_bonus,
            last_daily_bonus=current_time.strftime('%Y-%m-%d %H:%M:%S')
        )
        
        bonus_text = f"""
🎁 <b>المكافأة اليومية!</b>

💰 <b>المكافأة الأساسية:</b> 0.70 Pi
💎 <b>مكافأة الباقات:</b> +{package_bonus:.2f} Pi
💰 <b>الإجمالي:</b> {total_bonus:.2f} Pi

💵 <b>رصيدك الجديد:</b> {new_balance:.2f} Pi
📈 <b>قيمته:</b> {get_total_balance_value(new_balance):,.2f} USDT

🕒 <b>عد للمكافأة التالية بعد 24 ساعة</b>
        """
        
        bot.answer_callback_query(call.id, f"🎉 تم استلام {total_bonus:.2f} Pi!")
        bot.edit_message_text(bonus_text, call.message.chat.id, call.message.message_id)
        
    except Exception as e:
        print(f"❌ Daily bonus error: {e}")

# 🔄 نظام Keep Alive
def keep_alive():
    while True:
        try:
            print(f"✅ Bot is alive - {time.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"❌ Keep-alive failed: {e}")
        time.sleep(300)

# 🚀 تشغيل البوت
print("🚀 Starting Pi Network Bot with Polling...")
keep_thread = threading.Thread(target=keep_alive, daemon=True)
keep_thread.start()

try:
    bot.remove_webhook()
    time.sleep(2)
    bot.polling(none_stop=True, timeout=60)
except Exception as e:
    print(f"❌ Bot polling error: {e}")
    time.sleep(30)
