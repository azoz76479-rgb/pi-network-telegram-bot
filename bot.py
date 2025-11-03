import os
import telebot
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import time
from flask import Flask, request
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
PI_PRICE = 35.50  # سعر Pi مقابل USDT
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
                'balance': 10.0,  # مكافأة التسجيل 10 Pi
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
            
            # إرسال رسالة ترحيب للمستخدم الجديد
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
    """إرسال رسالة ترحيب للمستخدم الجديد"""
    welcome_text = """
🎉 **مرحباً بك في مجتمع Pi Network!**

🌐 **ما هي Pi Network؟**
Pi هي عملة رقمية ثورية يمكن تعدينها من هاتفك المحمول دون استهلاك البطارية أو البيانات. أسسها فريق من خريجي جامعة ستانفورد بهدف جعل التعدين الرقمي في متناول الجميع.

🚀 **لماذا Pi Network؟**
• ✅ **مجانية بالكامل** - لا تطلب أي رسوم
• 📱 **صديقة للبيئة** - لا تستهلك طاقة
• 👥 **مركزية للمجتمع** - توزيع عادل للثروة
• 🔒 **آمنة ومشفرة** - تقنية blockchain متطورة

💎 **قيمة Pi الحالية:**
• **1 Pi = {price} USDT**
• **التداول يبدأ رسمياً في {launch_date}**

📈 **لماذا تستثمر في Pi؟**
- مشروع مدعوم من مجتمع يضم +35 مليون مستخدم
- نمو مستمر وقاعدة مستخدمين نشطة
- إمكانية نمو كبيرة بعد الإطلاق الرسمي

🔗 **انضم إلى الثورة الرقمية وكن جزءاً من المستقبل!**
    """.format(price=PI_PRICE, launch_date=LAUNCH_DATE)
    
    try:
        bot.send_message(user_id, welcome_text)
    except Exception as e:
        print(f"❌ Failed to send welcome message: {e}")

def handle_referral_system(message):
    """نظام الإحالات - 20 إحالة كحد أقصى للمكافآت"""
    try:
        user_id = message.from_user.id
        command_parts = message.text.split()
        
        if len(command_parts) > 1 and command_parts[1].startswith('ref'):
            try:
                referrer_id = int(command_parts[1][3:])
                if referrer_id != user_id:
                    referrer = get_user(referrer_id)
                    if referrer and referrer['active_referrals'] < 20:
                        # منح مكافأة الإحالة
                        new_balance = referrer['balance'] + 0.50
                        new_active_refs = referrer['active_referrals'] + 1
                        
                        update_user(referrer_id,
                            balance=new_balance,
                            total_earnings=referrer['total_earnings'] + 0.50,
                            referral_count=referrer['referral_count'] + 1,
                            active_referrals=new_active_refs
                        )
                        
                        # إرسال إشعار للمستخدم
                        notify_referral_earned(referrer_id, new_active_refs)
            except ValueError:
                pass
    except Exception as e:
        print(f"❌ Referral error: {e}")

def notify_referral_earned(user_id, referral_count):
    """إشعار المستخدم بمكافأة إحالة جديدة"""
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
    """حساب أيام العضوية"""
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
    """حساب القيمة الإجمالية للرصيد"""
    return balance * PI_PRICE

def can_withdraw(user_id):
    """التحقق من إمكانية السحب (10 أيام + بعد تاريخ الإطلاق)"""
    days_registered, _ = get_membership_days(user_id)
    current_date = datetime.now()
    launch_date = datetime(2025, 12, 31)
    
    return days_registered >= 10 and current_date >= launch_date

def show_main_menu(chat_id, message_id=None, user_id=None):
    """عرض الواجهة الرئيسية المختصرة"""
    try:
        if not user_id: 
            return False
            
        user_data = get_user(user_id)
        if not user_data or user_data.get('is_banned', False):
            return False
        
        days_registered, total_days = get_membership_days(user_id)
        
        # حساب القيمة الإجمالية
        total_value = get_total_balance_value(user_data['balance'])
        
        # تحديد العضوية
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
        
        # إرسال طلب الشراء للإدمن
        send_purchase_request(call.from_user.id, package)
        
        bot.answer_callback_query(call.id, f"✅ تم إرسال طلب شراء {package['name']} للمسؤول")
        
    except Exception as e:
        print(f"❌ Buy package error: {e}")

def send_purchase_request(user_id, package):
    """إرسال طلب شراء الباقة للإدمن"""
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

# 💳 نظام الإيداع
@bot.callback_query_handler(func=lambda call: call.data == "deposit")
def handle_deposit(call):
    try:
        deposit_text = f"""
💳 <b>نظام الإيداع</b>

📍 <b>عنوان المحفظة:</b>
<code>{PI_WALLET}</code>

⚠️ <b>تحذير هام:</b>
• تأكد من استخدام شبكة <b>Pi Network</b> فقط
• <b>لا تستخدم شبكة BEP20</b> أو أي شبكة أخرى
• أرسل المبلغ فقط إلى العنوان أعلاه

📋 <b>بعد الإيداع:</b>
1. احفظ صورة التحويل كإثبات
2. تواصل مع الدعم الفني
3. سيتم تفعيل رصيدك خلال 24 ساعة
        """
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📋 نسخ العنوان", callback_data="copy_wallet"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        
        bot.edit_message_text(deposit_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ Deposit error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "copy_wallet")
def handle_copy_wallet(call):
    bot.answer_callback_query(call.id, f"✅ تم نسخ العنوان: {PI_WALLET}")

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

# 🎁 المكافأة اليومية والتعدين
@bot.callback_query_handler(func=lambda call: call.data == "daily_bonus")
def handle_daily_bonus(call):
    try:
        user = get_user(call.from_user.id)
        current_time = datetime.now()
        
        # حساب المكافأة الأساسية
        base_bonus = 0.7  # 0.7 Pi للمستخدمين المجانيين
        
        # إضافة مكافآت الباقات
        package_bonus = 0
        if user.get('vip_packages'):
            for package in user['vip_packages']:
                package_bonus += package.get('daily_bonus', 0)
        
        total_bonus = base_bonus + package_bonus
        
        # التحقق من آخر مكافأة
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
        
        # منح المكافأة
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

# 👥 نظام الإحالات
@bot.callback_query_handler(func=lambda call: call.data == "referral")
def handle_referral(call):
    try:
        user_id = call.from_user.id
        user = get_user(user_id)
        referral_link = f"https://t.me/Usdt_Mini1Bot?start=ref{user_id}"
        
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

# 🎨 نظام إرسال العروض المصممة مع أزرار
@bot.message_handler(commands=['send_design'])
def handle_send_design(message):
    """أمر للإدمن لإرسال عروض مصممة للجميع"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ <b>ليس لديك صلاحية!</b>")
        return
    
    try:
        # طلب تأكيد الإرسال للجميع
        confirm_keyboard = InlineKeyboardMarkup()
        confirm_keyboard.add(
            InlineKeyboardButton("✅ نعم، أرسل للجميع", callback_data="design_confirm_all"),
            InlineKeyboardButton("📱 اختبار للإدمن فقط", callback_data="design_test_only")
        )
        
        total_users = users_collection.count_documents({})
        
        bot.reply_to(message, 
                    f"🖼️ <b>نظام إرسال التصاميم</b>\n\n"
                    f"👥 <b>عدد المستخدمين:</b> {total_users}\n\n"
                    f"📝 <b>اختر طريقة الإرسال:</b>\n"
                    f"• ✅ للجميع - يرسل لجميع المستخدمين\n"
                    f"• 📱 اختبار - يعرض لك المعاينة فقط\n\n"
                    f"🖼️ <b>بعد الموافقة أرسل الصورة</b>",
                    reply_markup=confirm_keyboard)
        
    except Exception as e:
        bot.reply_to(message, f"❌ <b>خطأ:</b> {e}")

@bot.callback_query_handler(func=lambda call: call.data == "design_confirm_all")
def handle_design_confirm_all(call):
    """تأكيد الإرسال للجميع"""
    try:
        bot.answer_callback_query(call.id, "📤 جاهز لاستقبال الصورة للإرسال الجماعي...")
        bot.edit_message_text("🖼️ <b>الإرسال للجميع ✓</b>\n\nأرسل الصورة الآن...", 
                            call.message.chat.id, 
                            call.message.message_id)
        
        # تسجيل أن الإرسال للجميع
        bot.register_next_step_handler(call.message, process_design_image, send_to_all=True)
        
    except Exception as e:
        bot.reply_to(call.message, f"❌ <b>خطأ:</b> {e}")

@bot.callback_query_handler(func=lambda call: call.data == "design_test_only")
def handle_design_test_only(call):
    """الإرسال للإدمن فقط (معاينة)"""
    try:
        bot.answer_callback_query(call.id, "📱 وضع المعاينة - للإدمن فقط")
        bot.edit_message_text("🖼️ <b>وضع المعاينة ✓</b>\n\nأرسل الصورة للعرض الخاص بك...", 
                            call.message.chat.id, 
                            call.message.message_id)
        
        # تسجيل أن الإرسال للإدمن فقط
        bot.register_next_step_handler(call.message, process_design_image, send_to_all=False)
        
    except Exception as e:
        bot.reply_to(call.message, f"❌ <b>خطأ:</b> {e}")

def process_design_image(message, send_to_all=False):
    """معالجة الصورة المرسلة من الإدمن"""
    try:
        if not message.photo:
            bot.reply_to(message, "❌ <b>لم ترسل صورة! أعد استخدام الأمر /send_design</b>")
            return
        
        # حفظ file_id للصورة
        file_id = message.photo[-1].file_id
        
        bot.reply_to(message, "📝 <b>الآن أرسل النص التحتي للصورة</b>")
        bot.register_next_step_handler(message, process_design_text, file_id, send_to_all)
        
    except Exception as e:
        bot.reply_to(message, f"❌ <b>خطأ في معالجة الصورة:</b> {e}")

def process_design_text(message, file_id, send_to_all=False):
    """معالجة النص وإرسال العرض"""
    try:
        caption_text = message.text or "عرض حصري! 🎯"
        
        # إنشاء الأزرار
        markup = InlineKeyboardMarkup()
        btn_deposit = InlineKeyboardButton("💳 إيداع الآن", callback_data="deposit")
        btn_packages = InlineKeyboardButton("💎 شراء باقة", callback_data="vip_packages")
        markup.add(btn_deposit, btn_packages)
        
        if send_to_all:
            # 🔥 الإرسال للجميع
            all_users = list(users_collection.find({}, {'user_id': 1}))
            total_users = len(all_users)
            successful_sends = 0
            
            # إرسال للجميع
            for user in all_users:
                try:
                    bot.send_photo(
                        user['user_id'],
                        photo=file_id,
                        caption=caption_text,
                        reply_markup=markup,
                        parse_mode="HTML"
                    )
                    successful_sends += 1
                    time.sleep(0.1)  # تجنب rate limits
                except Exception as e:
                    print(f"❌ فشل الإرسال للمستخدم {user['user_id']}: {e}")
            
            # تقرير النتيجة للإدمن
            success_rate = (successful_sends / total_users) * 100 if total_users > 0 else 0
            report_msg = f"""🎉 <b>تم الإرسال الجماعي بنجاح!</b>

📊 <b>الإحصائيات:</b>
👥 <b>إجمالي المستخدمين:</b> {total_users}
✅ <b>تم الإرسال بنجاح:</b> {successful_sends}
❌ <b>فشل في الإرسال:</b> {total_users - successful_sends}
📈 <b>نسبة النجاح:</b> {success_rate:.1f}%"""

            bot.send_message(message.chat.id, report_msg)
            
        else:
            # 📱 الإرسال للإدمن فقط (معاينة)
            bot.send_photo(
                message.chat.id,
                photo=file_id,
                caption=caption_text,
                reply_markup=markup,
                parse_mode="HTML"
            )
            bot.reply_to(message, "✅ <b>تم عرض المعاينة بنجاح!</b>\n\nاستخدم /send_design للإرسال للجميع")
        
    except Exception as e:
        bot.reply_to(message, f"❌ <b>خطأ في إرسال العرض:</b> {e}")

# =============================================
# 🔧 نظام السيرفر والويب هوك مع Keep Alive
# =============================================

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    """استقبال الرسائل من تليجرام"""
    try:
        json_data = request.get_json()
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return 'OK'
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return 'OK'

@app.route('/')
def home():
    return "🤖 Pi Network Bot شغال - " + time.strftime("%Y-%m-%d %H:%M:%S")

@app.route('/health')
def health():
    return "✅ البوت بصحة جيدة"

@app.route('/ping')
def ping():
    return "🏓 Pong - " + time.strftime("%H:%M:%S")

@app.route('/set_webhook', methods=['GET'])
def set_webhook_manual():
    """تعيين الويب هوك يدوياً"""
    try:
        bot.remove_webhook()
        time.sleep(2)
        webhook_url = "https://your-app-name.onrender.com/webhook"
        result = bot.set_webhook(url=webhook_url)
        return f"✅ تم تعيين الويب هوك!<br>الرابط: {webhook_url}<br>النتيجة: {result}"
    except Exception as e:
        return f"❌ خطأ: {str(e)}"

@app.route('/test')
def test():
    return "✅ البوت شغال تمام! - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 🔄 نظام الإبقاء على الخدمة نشطة - محسّن
def keep_alive():
    """نظام Keep Alive لمنع البوت من النوم"""
    while True:
        try:
            # إرسال طلب ping للموقع نفسه
            response = requests.get('https://your-app-name.onrender.com/ping', timeout=10)
            if response.status_code == 200:
                print(f"✅ Keep-alive - {time.strftime('%H:%M:%S')}")
            else:
                print(f"⚠️ Keep-alive status: {response.status_code}")
        except Exception as e:
            print(f"❌ Keep-alive failed: {e}")
        
        # الانتظار 5 دقائق بين كل طلب
        time.sleep(300)

# 🔄 إعداد الويب هوك تلقائياً - محسّن
def setup_webhook():
    """إعداد الويب هوك تلقائياً مع إعادة المحاولة"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            time.sleep(15)  # انتظر 15 ثانية للتأكد من تشغيل السيرفر
            print(f"🔄 جاري تعيين الويب هوك (المحاولة {attempt + 1})...")
            
            bot.remove_webhook()
            time.sleep(2)
            
            webhook_url = "https://your-app-name.onrender.com/webhook"
            result = bot.set_webhook(url=webhook_url)
            
            # تحقق من الويب هوك
            webhook_info = bot.get_webhook_info()
            print(f"✅ تم تعيين الويب هوك: {webhook_url}")
            print(f"📊 معلومات الويب هوك: {webhook_info}")
            return True
            
        except Exception as e:
            print(f"❌ فشل تعيين الويب هوك (المحاولة {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(10)  # انتظر قبل إعادة المحاولة
    return False

if __name__ == '__main__':
    print("🚀 بدء تشغيل Pi Network Bot...")
    
    # تشغيل نظام الإبقاء النشط
    keep_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_thread.start()
    
    # محاولة إعداد الويب هوك تلقائياً
    webhook_success = setup_webhook()
    if not webhook_success:
        print("⚠️ تشغيل بدون ويب هوك - استخدام polling")
        bot.remove_webhook()
        time.sleep(2)
        bot.polling(none_stop=True)
    else:
        # تشغيل الخادم
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port, debug=False)
