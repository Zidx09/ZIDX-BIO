import telebot
from telebot import types
import requests
import json
import os
import random
import time
import uuid
import glob 

# --- CONFIGURATION --- #
BOT_TOKEN = 'YOUR_BOT_TOKEN'
ADMIN_ID = YOURCHATID
bot = telebot.TeleBot(BOT_TOKEN)

# Global Files
KEYS_FILE = 'keys.json'
USERS_FILE = 'activated_users.json'

# --- API ENDPOINTS --- #
URL_ACCOUNT_CHECK = "https://www.sheinindia.in/api/auth/accountCheck"
URL_OTP = "https://www.sheinindia.in/api/auth/generateLoginOTP"
URL_LOGIN = "https://www.sheinindia.in/api/auth/login"

# --- 1. FILE & SESSION HELPERS (DEFINED AT TOP TO FIX ERROR) --- #
def get_session_file(user_id):
    # Creates unique file for each user: 12345_session.json
    return f"{user_id}_session.json"

def get_userid_file(user_id):
    # Creates unique file for each user: 12345_userid.json
    return f"{user_id}_userid.json"

def save_session(user_id, session_obj):
    # This function saves the cookies to the specific user's file
    filename = get_session_file(user_id)
    with open(filename, 'w') as f:
        json.dump(session_obj.cookies.get_dict(), f)

def save_userid_raw(user_id, uid_string):
    # This function saves the UserID to the specific user's file
    filename = get_userid_file(user_id)
    with open(filename, 'w') as f:
        json.dump(uid_string, f)

def load_json(filename, default=None):
    if default is None: default = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# --- 2. RANDOMIZATION UTILS --- #
def get_headers():
    models = ['SM-G960F', 'SM-A505F', 'SM-G991B', 'KB2001', 'GM1901', 'SM-G610F']
    chrome_versions = ['138.0.7204.179', '120.0.6099.144']
    model = random.choice(models)
    chrome = random.choice(chrome_versions)
    user_agent = f"Mozilla/5.0 (Linux; Android 10; {model}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome} Mobile Safari/537.36"
    
    headers = {
        "Host": "www.sheinindia.in",
        "content-type": "application/json",
        "x-tenant-id": "SHEIN",
        "sec-ch-ua-platform": '"Android"',
        "user-agent": user_agent,
        "accept": "application/json",
        "x-requested-with": "mark.via.gp",
        "sec-ch-ua-mobile": "?1",
        "origin": "https://www.sheinindia.in",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://www.sheinindia.in/login",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8"
    }
    return headers

# --- 3. KEY & LICENSE SYSTEM --- #
def generate_key(hours):
    key = f"KEY-{uuid.uuid4().hex[:8].upper()}-{hours}H"
    if hours == 99999:
        key = f"KEY-LIFE-{uuid.uuid4().hex[:8].upper()}"
    
    keys = load_json(KEYS_FILE)
    keys[key] = {
        "hours": hours,
        "generated_at": time.time(),
        "used_by": None,
        "status": "active"
    }
    save_json(KEYS_FILE, keys)
    return key

def check_user_access(user_id):
    users = load_json(USERS_FILE)
    str_uid = str(user_id)
    if str_uid in users:
        expiry = users[str_uid]['expiry']
        if expiry > time.time():
            return True, expiry
        else:
            del users[str_uid]
            save_json(USERS_FILE, users)
    return False, 0

def redeem_key(user_id, key_text):
    keys = load_json(KEYS_FILE)
    users = load_json(USERS_FILE)
    
    if key_text in keys and keys[key_text]['status'] == 'active':
        duration_hours = keys[key_text]['hours']
        if duration_hours == 99999:
             duration_seconds = 315360000 
        else:
             duration_seconds = duration_hours * 3600
        
        current_time = time.time()
        expiry_time = current_time + duration_seconds
        
        users[str(user_id)] = {
            "expiry": expiry_time,
            "key_used": key_text
        }
        
        keys[key_text]['status'] = 'used'
        keys[key_text]['used_by'] = user_id
        keys[key_text]['used_at'] = current_time
        
        save_json(KEYS_FILE, keys)
        save_json(USERS_FILE, users)
        return True, duration_hours
    return False, 0

# --- 4. MENUS --- #
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    is_admin = user_id == ADMIN_ID
    has_access, expiry = check_user_access(user_id)
    
    if has_access or is_admin:
        markup.add("Login 🔐", "Status 📊")
        markup.add("Logout 🚪")
        if is_admin:
            markup.add("👑 ADMIN PANEL")
    else:
        markup.add("🔑 Enter Key", "Buy Key 🛒")
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Gen 24 Hour ⏳", "Gen 168 Hours ⏳")
    markup.add("Gen 48 Hours ⏳", "Gen Lifetime ♾️")
    markup.add("View Keys 📜", "Revoke Key 🚫")
    markup.add("☠️ ALLOUT")
    markup.add("🔙 Back to Main")
    return markup

# --- 5. BOT HANDLERS --- #
user_state = {}
temp_data = {}

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.chat.id
    markup = main_menu(uid)
    bot.reply_to(m, f"👋 **Welcome to Shein Auto Order Login Bot! Made With ❤️ by @iSadatAlam**\n🆔 Your ID: `{uid}`", reply_markup=markup, parse_mode="Markdown")

# --- ADMIN PANEL HANDLERS --- #
@bot.message_handler(func=lambda m: m.text == "👑 ADMIN PANEL" and m.chat.id == ADMIN_ID)
def admin_panel_handler(m):
    bot.reply_to(m, "Welcome @isadatalam ! Select an action:", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Back to Main")
def back_main(m):
    bot.reply_to(m, "Main Menu", reply_markup=main_menu(m.chat.id))

@bot.message_handler(func=lambda m: m.text.startswith("Gen ") and m.chat.id == ADMIN_ID)
def generate_key_handler(m):
    hours = 0
    label = ""
    if "24 Hour" in m.text: hours = 24; label = "24 Hour"
    elif "48 Hours" in m.text: hours = 48; label = "48 Hours"
    elif "168 Hours" in m.text: hours = 168; label = "168 Hours"
    elif "Lifetime" in m.text: hours = 99999; label = "Lifetime"
    
    if hours > 0:
        k = generate_key(hours)
        bot.reply_to(m, f"✅ **Key Generated ({label})**\nCopy below:\n`{k}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "View Keys 📜" and m.chat.id == ADMIN_ID)
def view_keys(m):
    keys = load_json(KEYS_FILE)
    if not keys:
        bot.reply_to(m, "No keys found.")
        return
    
    msg = "📜 **Recent Keys:**\n"
    items = list(keys.items())[-10:]
    if not items: msg = "No keys created yet."
    
    for k, v in items:
        status_icon = "🟢" if v['status'] == 'active' else "🔴"
        if v['status'] == 'revoked': status_icon = "🚫"
        
        hours_lbl = "Life" if v['hours'] == 99999 else f"{v['hours']}h"
        msg += f"{status_icon} `{k}` ({hours_lbl})\n"
        
    bot.reply_to(m, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "Revoke Key 🚫" and m.chat.id == ADMIN_ID)
def revoke_key_start(m):
    user_state[m.chat.id] = 'admin_revoke'
    bot.reply_to(m, "Paste the Key to revoke:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == 'admin_revoke')
def revoke_key_process(m):
    key = m.text.strip()
    keys = load_json(KEYS_FILE)
    users = load_json(USERS_FILE)
    
    if key in keys:
        # Mark Key as Revoked
        keys[key]['status'] = 'revoked'
        
        # Kill User Session
        used_by = keys[key].get('used_by')
        if used_by:
            str_uid = str(used_by)
            if str_uid in users:
                del users[str_uid]
                save_json(USERS_FILE, users)
                try: bot.send_message(used_by, "🚫 **Your Key has been Revoked.**")
                except: pass
        
        save_json(KEYS_FILE, keys)
        bot.reply_to(m, f"🚫 Key `{key}` revoked & user kicked.", parse_mode="Markdown", reply_markup=admin_menu())
    else:
        bot.reply_to(m, "❌ Key not found.", reply_markup=admin_menu())
    user_state[m.chat.id] = None

@bot.message_handler(func=lambda m: m.text == "☠️ ALLOUT" and m.chat.id == ADMIN_ID)
def allout_handler(m):
    # 1. Delete all session files
    session_files = glob.glob("*_session.json")
    for f in session_files:
        try: os.remove(f)
        except: pass
        
    # 2. Delete all userid files
    userid_files = glob.glob("*_userid.json")
    for f in userid_files:
        try: os.remove(f)
        except: pass
        
    bot.reply_to(m, f"☠️ **ALLOUT EXECUTED**\nDeleted {len(session_files)} sessions & {len(userid_files)} user IDs.\nEveryone must login again.", parse_mode="Markdown")

# --- USER HANDLERS --- #
@bot.message_handler(func=lambda m: m.text == "Buy Key 🛒")
def buy_key_info(m):
    bot.reply_to(m, "To purchase an activation key, please contact the Admin:\n👉 @isadatalam", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔑 Enter Key")
def enter_key_start(m):
    user_state[m.chat.id] = 'awaiting_key'
    bot.reply_to(m, "👇 **Please paste your activation key:**", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == 'awaiting_key')
def process_key(m):
    key = m.text.strip()
    success, hours = redeem_key(m.chat.id, key)
    
    if success:
        user_state[m.chat.id] = None
        dur_text = "Lifetime" if hours > 80000 else f"{hours} Hours"
        bot.reply_to(m, f"🎉 **Activation Successful!**\n💎 Plan: {dur_text}", reply_markup=main_menu(m.chat.id), parse_mode="Markdown")
    else:
        bot.reply_to(m, "❌ **Invalid or Used Key.**", parse_mode="Markdown", reply_markup=main_menu(m.chat.id))
        user_state[m.chat.id] = None

# --- LOGIN FLOW --- #
@bot.message_handler(func=lambda m: m.text == "Login 🔐")
def login_start(m):
    has_access, _ = check_user_access(m.chat.id)
    if not has_access and m.chat.id != ADMIN_ID:
        bot.reply_to(m, "⛔ **Access Denied**\nPlease activate a key first.", parse_mode="Markdown", reply_markup=main_menu(m.chat.id))
        return

    user_state[m.chat.id] = 'mobile'
    bot.reply_to(m, "📱 **Enter Mobile Number:**", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == 'mobile')
def login_otp(m):
    mobile = m.text.strip()
    session = requests.Session()
    session.headers.update(get_headers())
    
    try:
        msg = bot.send_message(m.chat.id, "🔄 Server is Connected with SHEIN...")
        session.post(URL_ACCOUNT_CHECK, json={"mobileNumber": mobile})
        r2 = session.post(URL_OTP, json={"mobileNumber": mobile})
        
        if r2.status_code in [200, 201]:
            temp_data[m.chat.id] = {'mobile': mobile, 'headers': session.headers}
            user_state[m.chat.id] = 'otp'
            bot.delete_message(m.chat.id, msg.message_id)
            bot.reply_to(m, f"✅ OTP Sent to {mobile}\n👇 **Enter OTP:**", parse_mode="Markdown")
        else:
            bot.reply_to(m, f"❌ Failed to send OTP.\nStatus: {r2.status_code}", reply_markup=main_menu(m.chat.id))
            user_state[m.chat.id] = None
            
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {e}", reply_markup=main_menu(m.chat.id))
        user_state[m.chat.id] = None

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == 'otp')
def login_verify(m):
    otp = m.text.strip()
    data = temp_data.get(m.chat.id)
    if not data: return
    
    session = requests.Session()
    session.headers.update(data['headers'])
    
    try:
        r = session.post(URL_LOGIN, json={"username": data['mobile'], "otp": otp})
        
        if r.status_code == 200:
            # THIS CALL CAUSED YOUR ERROR BEFORE. NOW IT IS FIXED.
            save_session(m.chat.id, session) 
            
            c = session.cookies.get_dict()
            extracted_uid = c.get('CI', None)
            
            if extracted_uid:
                save_userid_raw(m.chat.id, extracted_uid)
                success_msg = (
                    f"✅ **Login Successful !**\n"
                    f"👤 UserID: `{extracted_uid}`\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"🚀 **NEXT STEP:**\n"
                    f"abb dusre bot pe jao and join this group for more scripts @sheinlootlink to use the **SheinIndia Auto Order Bot** now!"
                )
                bot.send_message(m.chat.id, success_msg, parse_mode="Markdown", reply_markup=main_menu(m.chat.id))
            else:
                bot.send_message(m.chat.id, "⚠️ Login success, but 'CI' UserID not found.", reply_markup=main_menu(m.chat.id))
        else:
            bot.reply_to(m, f"❌ Login Failed.\nResp: {r.text}", reply_markup=main_menu(m.chat.id))
            
    except Exception as e:
        bot.reply_to(m, f"Error: {e}", reply_markup=main_menu(m.chat.id))
    
    user_state[m.chat.id] = None
    if m.chat.id in temp_data: del temp_data[m.chat.id]

# --- 6. STATUS & LOGOUT HANDLERS --- #
@bot.message_handler(func=lambda m: m.text == "Status 📊")
def status(m):
    has_access, expiry = check_user_access(m.chat.id)
    is_admin = m.chat.id == ADMIN_ID
    
    if not has_access and not is_admin:
        bot.reply_to(m, "⛔ **Access Denied.**\nYour key may have expired or been revoked.", reply_markup=main_menu(m.chat.id))
        return

    u_session_file = get_session_file(m.chat.id)
    
    msg = "📊 **Bot Status @isadatalam**\n━━━━━━━━━━━━━━\n"
    
    if is_admin: msg += "💎 Plan: **ADMIN**\n"
    elif has_access:
        time_left_secs = expiry - time.time()
        if time_left_secs > 31536000: msg += "✅ License: Lifetime\n"
        else: msg += f"✅ License: Active ({int(time_left_secs / 3600)}h remaining)\n"

    msg += "━━━━━━━━━━━━━━\n"

    if os.path.exists(u_session_file):
        try:
            with open(u_session_file, 'r') as f:
                _sess_data = json.load(f)
            
            user_email = _sess_data.get("U", "N/A").replace("%40", "@") 
            user_mobile = _sess_data.get("MN", "N/A")
            user_id = _sess_data.get("CI", "N/A")

            msg += "✅ **SESSION: CONNECTED**\n"
            msg += f"👤 **UserID:** `{user_id}`\n"
            msg += f"📱 **Mobile:** `{user_mobile}`\n"
            msg += f"📧 **Email:** `{user_email}`\n"
        except:
            msg += "⚠️ **Session Error:** File Corrupted\n"
    else:
        msg += "❌ **Session:** Not Connected\n"
        
    bot.reply_to(m, msg, parse_mode="Markdown", reply_markup=main_menu(m.chat.id))

@bot.message_handler(func=lambda m: m.text == "Logout 🚪")
def logout(m):
    u_session_file = get_session_file(m.chat.id)
    u_userid_file = get_userid_file(m.chat.id)
    
    if not os.path.exists(u_session_file):
        bot.reply_to(m, "⚠️ **Error:** You are not logged in!", reply_markup=main_menu(m.chat.id))
        return

    if os.path.exists(u_session_file): os.remove(u_session_file)
    if os.path.exists(u_userid_file): os.remove(u_userid_file)
    
    bot.reply_to(m, "🗑️ **Logged Out Successfully.**", parse_mode="Markdown", reply_markup=main_menu(m.chat.id))

print("@isadatalam SHEIN Bot Running...")
bot.polling()