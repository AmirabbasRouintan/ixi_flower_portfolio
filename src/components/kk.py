import asyncio
import re
import csv
import os
import time
import httpx
import json
import uuid
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document, Audio, PhotoSize, Video
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode, MessageLimit
from telegram.error import BadRequest

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
import io

# --- Constants and Configuration ---
TARGET_GROUP_ID = -1002763813525
IMAGE_TOPIC_ID = 62
VIDEO_TOPIC_ID = 100
MUSIC_TOPIC_ID = 15
VOICE_TOP_ID = 7

BOT_TOKEN = "7761098777:AAHpfFRjgmYGgnTqMD0NdS1ecS0QzPGm1Go"
ADMIN_CHAT_ID = 2006833036
GEMINI_API_KEY = "AIzaSyC9yKy-QJVAz1aJtrh3ZuDXLLTUyO2TYr8"

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
DEEPSEEK_API_KEY = "sk-b62b9a5c27d94452a42ac985800c1ef6" # DeepSeek API Key
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions" # DeepSeek API URL

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.readonly']
REDIRECT_URI = 'http://localhost' # For local testing

DRIVE_TOKENS_DIR = 'drive_tokens'
V2RAY_FILES_DIR = 'v2ray_files'  # Directory to store V2Ray config files
os.makedirs(DRIVE_TOKENS_DIR, exist_ok=True)
os.makedirs(V2RAY_FILES_DIR, exist_ok=True)  # Create the directory if it doesn't exist

# --- File Paths ---
ENGLISH_ACCESS_LIST_FILE = 'english_access.txt'
FEEDBACK_FILE = 'feedback.csv'
PROXY_BACKUP_FILE = 'proxy.txt'
V2RAY_BACKUP_FILE = 'v2ray.txt'
WHITELIST_FILE = 'whitelist.txt'
BLOCKLIST_FILE = 'blocklist.txt'
BOT_LOCK_FILE = 'bot_lock.txt'
BOT_PASSWORD_FILE = 'bot_password.txt'
GEMINI_ACCESS_LIST_FILE = 'gemini_access.txt'
GEMINI_REQUESTS_FILE = 'gemini_requests.txt'
IXI_FLOWER_ENGLISH_FILE = 'ixi_flower_english.txt'
DEEPSEEK_ACCESS_LIST_FILE = 'deepseek_access.txt'
DEEPSEEK_REQUESTS_FILE = 'deepseek_requests.txt'

VIP_REQUESTS_FILE = 'vip_requests.txt'
VIP_USERS_FILE = 'vip_users.json'
VIP_CONTENT_FILE = 'vip_content.json'

# --- Directories ---
USER_MUSIC_DIR = 'user_music'
USER_TASKS_DIR = 'user_tasks'
VIP_CONTENT_DIR = 'vip_content'
USER_FILES_DIR = 'user_files'

# --- Bot Settings ---
COOLDOWN_SECONDS = 180
ADMIN_RESPONSE_TIMEOUT = 10

# --- Google Drive Functions ---
def get_user_drive_creds_path(user_id: int) -> str:
    return os.path.join(DRIVE_TOKENS_DIR, f'drive_token_{user_id}.json')

def load_user_drive_creds(user_id: int):
    creds_path = get_user_drive_creds_path(user_id)
    if os.path.exists(creds_path):
        return Credentials.from_authorized_user_file(creds_path, SCOPES)
    return None

def save_user_drive_creds(user_id: int, creds):
    creds_path = get_user_drive_creds_path(user_id)
    with open(creds_path, 'w') as token:
        token.write(creds.to_json())

async def get_drive_service_for_user(user_id: int):
    creds = load_user_drive_creds(user_id)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_user_drive_creds(user_id, creds)
            return build('drive', 'v3', credentials=creds)
        else:
            return None # Indicate that a new auth flow is needed
    return build('drive', 'v3', credentials=creds)

async def upload_file_to_drive(service, file_path: str, file_name: str, mime_type: str, caption: str = ""):
    """Uploads a file to Google Drive and returns the file ID."""
    try:
        file_metadata = {'name': file_name}
        if caption:
            file_metadata['description'] = caption
        media = MediaFileUpload(file_path, mimetype=mime_type)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except Exception as e:
        print(f"An error occurred during upload: {e}")
        return None

async def download_file_from_drive(service, file_id: str, file_name: str) -> str:
    """Downloads a file from Google Drive to a local path."""
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.seek(0)
    
    local_file_path = f"downloads/{file_name}"
    with open(local_file_path, 'wb') as f:
        f.write(fh.read())
    return local_file_path

# --- The rest of your code, including the functions you provided, with some key changes. ---

async def call_deepseek_api(prompt: str) -> str:
    headers = {
       "Content-Type": "application/json",
       "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    payload = {
        "model": "deepseek-chat",  # The DeepSeek model to use.
        "messages": [{"role": "user", "content": prompt}]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=40.0)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except httpx.HTTPStatusError as e:
            return f"❌ **API Error:** Server returned an error ({e.response.status_code})."
        except httpx.TimeoutException:
            return "❌ **API Error:** The request to DeepSeek timed out."
        except Exception as e:
            return f"❌ **An Unexpected Error Occurred:**\n`{str(e)}`"

# --- The rest of your existing functions here, untouched ---
def get_user_tasks_path(user_id: int) -> str:
    user_dir = os.path.join(USER_TASKS_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, 'tasks.json')

def read_user_tasks(user_id: int) -> dict:
    path = get_user_tasks_path(user_id)
    if not os.path.exists(path):
        return {"categories": {"General": []}}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "categories" not in data or not isinstance(data["categories"], dict):
                return {"categories": {"General": []}}
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {"categories": {"General": []}}

def save_user_tasks(user_id: int, data: dict):
    path = get_user_tasks_path(user_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


# --- Timer and Job Queue Functions ---
def parse_time_string(time_str: str) -> int:
    seconds = 0
    matches = re.findall(r'(\d+)\s*(h|m|s)', time_str.lower())
    if not matches:
        return -1
    for value, unit in matches:
        value = int(value)
        if unit == 'h':
            seconds += value * 3600
        elif unit == 'm':
            seconds += value * 60
        elif unit == 's':
            seconds += value
    return seconds

async def schedule_message_deletion(bot, chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass # Ignore errors if message is already deleted


async def time_up_callback(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.chat_id
    job_name = job.data.get("job_name")

    if 'timer_control_message_id' in context.user_data:
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=context.user_data['timer_control_message_id'])
        except Exception:
            pass
        del context.user_data['timer_control_message_id']
    
    if not job_name:
        await context.bot.send_message(chat_id=user_id, text="⏰ Time is up!")
        return

    keyboard = [
        [
            InlineKeyboardButton("➕ Add 5 min", callback_data=f'timer_add_5_{job_name}'),
            InlineKeyboardButton("🛑 Stop Timer", callback_data=f'timer_stop_{job_name}')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    sent_message = await context.bot.send_message(
        chat_id=user_id,
        text="⏰ Time is up!",
        reply_markup=reply_markup
    )
    context.user_data['timer_control_message_id'] = sent_message.message_id


def initialize_files():
    files_to_initialize = {
        FEEDBACK_FILE: ['id', 'text', 'likes'],
        WHITELIST_FILE: "# Add one whitelisted user ID per line.\n",
        BLOCKLIST_FILE: "# Add one blocked user ID per line.\n",
        GEMINI_ACCESS_LIST_FILE: "# Add one Gemini-authorized user ID per line.\n",
        GEMINI_REQUESTS_FILE: "# Users who have requested Gemini access.\n",
        BOT_LOCK_FILE: "unlocked",
        BOT_PASSWORD_FILE: "",
        VIP_REQUESTS_FILE: "# Users who have requested VIP access.\n",
        DEEPSEEK_ACCESS_LIST_FILE: "# Add one DeepSeek-authorized user ID per line.\n",
        DEEPSEEK_REQUESTS_FILE: "# Users who have requested DeepSeek access.\n",
        IXI_FLOWER_ENGLISH_FILE: "# English learning conversation history.\n",
        ENGLISH_ACCESS_LIST_FILE: "# Add one English-authorized user ID per line.\n",
    }
    for filename, content in files_to_initialize.items():
        if not os.path.exists(filename):
            if isinstance(content, list):
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(content)
            else:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)

    for filename in [PROXY_BACKUP_FILE, V2RAY_BACKUP_FILE]:
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Placeholder for {filename}.\n")
    
    for directory in [USER_MUSIC_DIR, VIP_CONTENT_DIR, USER_TASKS_DIR, USER_FILES_DIR, DRIVE_TOKENS_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)

def read_vip_content() -> list:
    try:
        with open(VIP_CONTENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def write_vip_content(data: list):
    with open(VIP_CONTENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def read_vip_users_data() -> dict:
    try:
        with open(VIP_USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_vip_users_data(data: dict):
    with open(VIP_USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_user_music_data_path(user_id: int) -> str:
    user_dir = os.path.join(USER_MUSIC_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, 'music_data.json')

def get_user_music_data(user_id: int) -> dict:
    path = get_user_music_data_path(user_id)
    if not os.path.exists(path):
        return {"music": {}, "groups": ["default"], "liked_songs": []}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"music": {}, "groups": ["default"], "liked_songs": []}

def save_user_music_data(user_id: int, data: dict):
    path = get_user_music_data_path(user_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def load_user_list(filename: str) -> set:
    if not os.path.exists(filename):
        return set()
    with open(filename, 'r', encoding='utf-8') as f:
        ids = set()
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    ids.add(int(line))
                except ValueError:
                    pass
        return ids

def remove_user_from_list(user_id: int, filename: str):
    user_list = load_user_list(filename)
    if user_id in user_list:
        user_list.remove(user_id)
        header = ""
        try:
            with open(filename, 'r', encoding='utf-8') as f_read:
                first_line = f_read.readline()
                if first_line.startswith('#'):
                    header = first_line
        except FileNotFoundError:
            pass
        with open(filename, 'w', encoding='utf-8') as f_write:
            if header:
                f_write.write(header)
            if user_list:
                f_write.write("\n".join(map(str, user_list)))
                f_write.write("\n")
            else:
                f_write.write("")
        return True
    return False

def read_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        return []
    with open(FEEDBACK_FILE, mode='r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def write_feedback(feedback_list):
    with open(FEEDBACK_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'text', 'likes'])
        writer.writeheader()
        writer.writerows(feedback_list)

def get_bot_lock_status() -> str:
    if not os.path.exists(BOT_LOCK_FILE): return "unlocked"
    with open(BOT_LOCK_FILE, 'r') as f:
        return f.read().strip()

def set_bot_lock_status(status: str):
    with open(BOT_LOCK_FILE, 'w') as f:
        f.write(status)

def get_bot_password() -> str:
    if not os.path.exists(BOT_PASSWORD_FILE): return ""
    with open(BOT_PASSWORD_FILE, 'r') as f:
        return f.read().strip()

def set_bot_password(password: str):
    with open(BOT_PASSWORD_FILE, 'w') as f:
        f.write(password)


# --- File Management Functions for User Files ---
def get_user_files_path(user_id: int) -> str:
    """Returns the path to the user's files JSON file."""
    user_dir = os.path.join(USER_FILES_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, 'files.json')

def read_user_files(user_id: int) -> dict:
    """Reads a user's file data from a JSON file."""
    path = get_user_files_path(user_id)
    if not os.path.exists(path):
        return {"files": {}}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "files" not in data or not isinstance(data["files"], dict):
                return {"files": {}}
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {"files": {}}

def save_user_files(user_id: int, data: dict):
    """Saves a user's file data to a JSON file."""
    path = get_user_files_path(user_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


# --- Security and Pre-flight Checks ---
async def check_admin_response(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, request_type: str):
    await asyncio.sleep(ADMIN_RESPONSE_TIMEOUT)
    if context.bot_data.get('pending_requests', {}).get(user_id) == request_type:
        del context.bot_data['pending_requests'][user_id]
        file_path = PROXY_BACKUP_FILE if request_type == 'proxy' else V2RAY_BACKUP_FILE
        service_name = "پروکسی" if request_type == 'proxy' else "کانفیگ V2Ray"
        message_text = (
            f"😔 متاسفانه به نظر می‌رسد ادمین در حال حاضر پاسخگو نیست.\n\n"
            f"نگران نباشید! ما برای شما یک فایل بک‌آپ از آخرین {service_name}‌های فعال ارسال کردیم."
        )
        try:
            if os.path.exists(file_path) and os.path.getsize(file_path) > 50:
                await context.bot.send_message(chat_id=chat_id, text=message_text)
                with open(file_path, 'rb') as document:
                    await context.bot.send_document(chat_id=chat_id, document=document)
            else:
                error_text = "متاسفانه فایل بک‌آپ در حال حاضر موجود نیست. لطفاً بعداً دوباره تلاش کنید."
                await context.bot.send_message(chat_id=chat_id, text=error_text)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text="خطایی در ارسال فایل بک‌آپ رخ داد.")

async def pre_flight_checks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if user.id == ADMIN_CHAT_ID:
        return True
    if user.id in load_user_list(BLOCKLIST_FILE):
        return False
    if get_bot_lock_status() == "locked":
        await update.effective_message.reply_text("🤖 ربات در حال حاضر توسط ادمین قفل شده است. لطفاً بعداً دوباره تلاش کنید.")
        return False
    password = get_bot_password()
    if password and not context.user_data.get('authenticated'):
        if update.message and update.message.text == password:
            context.user_data['authenticated'] = True
            await update.message.reply_text("✅ رمز عبور صحیح است! خوش آمدید.")
            await start_command(update, context)
            return True
        else:
            prompt_msg = "🔒 این ربات با رمز عبور محافظت می‌شود. لطفاً رمز را وارد کنید:"
            if update.callback_query:
                await update.callback_query.answer("نیاز به رمز عبور", show_alert=True)
                if update.effective_message.caption is None:
                    await update.effective_message.edit_text(prompt_msg)
                else:
                    await update.effective_message.edit_caption(caption=prompt_msg)
            else:
                await update.effective_message.reply_text(prompt_msg)
            return False
    return True

# --- V2Ray Configuration Validation ---
def is_valid_v2ray_config(config_text: str) -> bool:
    """
    Basic validation to check if the text looks like a valid V2Ray configuration.
    This checks for basic JSON structure and common V2Ray config elements.
    """
    try:
        # Try to parse as JSON
        config = json.loads(config_text)
        
        # Check if it has basic V2Ray config structure
        # V2Ray configs typically have "inbounds" and "outbounds" arrays
        if not isinstance(config, dict):
            return False
            
        # Should have at least inbounds or outbounds
        has_inbounds = "inbounds" in config and isinstance(config["inbounds"], list)
        has_outbounds = "outbounds" in config and isinstance(config["outbounds"], list)
        
        # Valid if it has either inbounds or outbounds
        return has_inbounds or has_outbounds
        
    except json.JSONDecodeError:
        # Not valid JSON
        return False
    except Exception:
        # Any other error
        return False

# --- V2Ray Configuration Management ---
def is_valid_v2ray_config(config_text: str) -> bool:
    """
    Basic validation to check if the text looks like a valid V2Ray configuration.
    This checks for basic JSON structure and common V2Ray config elements.
    """
    try:
        # Try to parse as JSON
        config = json.loads(config_text)
        
        # Check if it has basic V2Ray config structure
        # V2Ray configs typically have "inbounds" and "outbounds" arrays
        if not isinstance(config, dict):
            return False
            
        # Should have at least inbounds or outbounds
        has_inbounds = "inbounds" in config and isinstance(config["inbounds"], list)
        has_outbounds = "outbounds" in config and isinstance(config["outbounds"], list)
        
        # Valid if it has either inbounds or outbounds
        return has_inbounds or has_outbounds
        
    except json.JSONDecodeError:
        # Not valid JSON
        return False
    except Exception:
        # Any other error
        return False

# --- Core Bot Commands and Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await pre_flight_checks(update, context):
        return
    try:
        if update.message: await update.message.delete()
    except Exception:
        pass
    context.user_data['state'] = None
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("📡 پروکسی", callback_data='proxy_request'),
         InlineKeyboardButton("⚡ V2Ray", callback_data='v2ray_request')],
        [InlineKeyboardButton("✨ چت با AI", callback_data='AI_chat')],
        [InlineKeyboardButton("🎬 فیلم", callback_data='movie_request'), InlineKeyboardButton("👑 VIP", callback_data='vip_request')],
        [InlineKeyboardButton("🎵 Find Music", callback_data='music_find_menu'),
         InlineKeyboardButton("💾 My Music", callback_data='music_save_menu')],
        [InlineKeyboardButton("📁 My Files", callback_data='my_files_menu')],
        [InlineKeyboardButton("📝 Tasks & Ideas", callback_data='tasks_menu')],
        [InlineKeyboardButton("⏱️ Timer & Tools", callback_data='timer_menu')],
        [InlineKeyboardButton("🤔 ایده یا نظری داری بگو", callback_data='feedback_menu')]
    ]
    english_users = load_user_list(ENGLISH_ACCESS_LIST_FILE)
    if user.id == ADMIN_CHAT_ID or user.id in english_users:
        keyboard.insert(5, [InlineKeyboardButton("🎓 Learn English", callback_data='learn_english')])
    if user.id == ADMIN_CHAT_ID:
        keyboard.append([InlineKeyboardButton("🔧 Generate V2Ray File", callback_data='generate_v2ray_file')])
        keyboard.append([InlineKeyboardButton("➕ Add V2Ray Config", callback_data='add_v2ray_config')])
        keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data='admin_panel')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = (
        f"سلام، {user.first_name}! 👋 به ربات ما خوش آمدید. 🤖\n"
        "لطفاً یک گزینه را از زیر انتخاب کنید: 👇"
    )
    photo_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQKz4FGW0EPVWP9Ks5hbiHt4Y0R0oWXKhw7Ag&s"
    current_message = update.effective_message
    if current_message and current_message.caption is not None:
        try:
            await current_message.edit_caption(caption=welcome_message, reply_markup=reply_markup)
            return
        except Exception:
            pass
    if update.effective_chat:
        if update.callback_query:
            try:
                await update.callback_query.message.delete()
            except Exception:
                pass
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_url, caption=welcome_message, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await pre_flight_checks(update, context):
        return
    query = update.callback_query
    user = update.effective_user
    await query.answer()
    data = query.data

    if data.startswith('sendto_confirm_'):
        action = data.split('_')[2]
        
        message_with_buttons = query.message
        
        if action == 'no':
            context.user_data.clear()
            await message_with_buttons.edit_text("❌ Operation cancelled.")
            return

        if action == 'yes':
            target_user_id = context.user_data.get('sendto_target_id')
            message_id_to_send = context.user_data.get('sendto_message_id')
            
            if not target_user_id or not message_id_to_send:
                await message_with_buttons.edit_text("❌ Error: Could not find the message or user. Please start over.")
                context.user_data.clear()
                return

            try:
                await context.bot.copy_message(
                    chat_id=target_user_id,
                    from_chat_id=ADMIN_CHAT_ID,
                    message_id=message_id_to_send
                )
                await message_with_buttons.edit_text(f"✅ Message sent successfully to user `{target_user_id}`.", parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                await message_with_buttons.edit_text(f"❌ Failed to send message. Reason: {e}")
            finally:
                context.user_data.clear()
            return

    if data.startswith('sendto_confirm_'):
        action = data.split('_')[2]
        
        message_with_buttons = query.message
        
        if action == 'no':
            context.user_data.clear()
            await message_with_buttons.edit_text("❌ Operation cancelled.")
            return

        if action == 'yes':
            target_user_id = context.user_data.get('sendto_target_id')
            message_id_to_send = context.user_data.get('sendto_message_id')
            
            if not target_user_id or not message_id_to_send:
                await message_with_buttons.edit_text("❌ Error: Could not find the message or user. Please start over.")
                context.user_data.clear()
                return

            try:
                await context.bot.copy_message(
                    chat_id=target_user_id,
                    from_chat_id=ADMIN_CHAT_ID,
                    message_id=message_id_to_send
                )
                await message_with_buttons.edit_text(f"✅ Message sent successfully to user `{target_user_id}`.", parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                await message_with_buttons.edit_text(f"❌ Failed to send message. Reason: {e}")
            finally:
                context.user_data.clear()
            return

    if data.startswith('sendto_confirm_'):
        action = data.split('_')[2]
        
        message_with_buttons = query.message
        
        if action == 'no':
            context.user_data.clear()
            await message_with_buttons.edit_text("❌ Operation cancelled.")
            return

        if action == 'yes':
            target_user_id = context.user_data.get('sendto_target_id')
            message_id_to_send = context.user_data.get('sendto_message_id')
            
            if not target_user_id or not message_id_to_send:
                await message_with_buttons.edit_text("❌ Error: Could not find the message or user. Please start over.")
                context.user_data.clear()
                return

            try:
                await context.bot.copy_message(
                    chat_id=target_user_id,
                    from_chat_id=ADMIN_CHAT_ID,
                    message_id=message_id_to_send
                )
                await message_with_buttons.edit_text(f"✅ Message sent successfully to user `{target_user_id}`.", parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                await message_with_buttons.edit_text(f"❌ Failed to send message. Reason: {e}")
            finally:
                context.user_data.clear()
            return

    if data == 'generate_v2ray_file':
        await query.answer()
        # Send alert message to the specified chat ID with improved format
        alert_message = (
            f"🚨 V2Ray Configuration Request 🚨\n\n"
            f"User: {user.first_name} (@{user.username or 'N/A'})\n"
            f"User ID: {user.id}\n"
            f"Request: V2Ray Configuration File\n\n"
            f"Please send me the v2ray config file /generate-v2ray-file"
        )
        await context.bot.send_message(chat_id=2006833036, text=alert_message)
        
        # Track this request in bot_data
        if 'v2ray_requests' not in context.bot_data:
            context.bot_data['v2ray_requests'] = {}
        context.bot_data['v2ray_requests'][user.id] = {
            'timestamp': time.time(),
            'username': user.username,
            'first_name': user.first_name
        }
        
        # Notify the user
        await query.edit_message_caption(
            caption="Your request has been received. Please wait for the file to be generated.",
            reply_markup=None
        )
        return

    if data == 'add_v2ray_config':
        context.user_data['state'] = 'awaiting_v2ray_config_title'
        await query.edit_message_caption(
            caption="Please enter a title for the V2Ray configuration:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data='back_to_start')]])
        )
        return

    if data == 'v2ray_file_sent':
        # Handle when admin confirms file sent
        await query.edit_message_text(text="✅ V2Ray configuration file has been sent to the user.")
        return

    if data == 'v2ray_request_cancel':
        # Handle when admin cancels the request
        await query.edit_message_text(text="❌ V2Ray file generation request has been cancelled.")
        return

    if data == 'v2ray_file_sent':
        # Handle when admin confirms file sent
        await query.edit_message_text(text="✅ V2Ray configuration file has been sent to the user.")
        return


    if data == 'v2ray_request_cancel':
        # Handle when admin cancels the request
        await query.edit_message_text(text="❌ V2Ray file generation request has been cancelled.")
        return

    if data == 'files_upload_to_drive':
        context.user_data['state'] = 'awaiting_drive_upload_file'
        await query.edit_message_caption(
            caption="Please send the image or video you want to upload to Google Drive.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data='my_files_menu')]])
        )
        return
    
    # --- My Files Menu ---
    if data == 'my_files_menu':
        keyboard = [
            [InlineKeyboardButton("📂 View My Files", callback_data='files_view_all')],
            # Add a new button for Google Drive
            [InlineKeyboardButton("☁️ Upload to Google Drive", callback_data='files_upload_to_drive')],
            [InlineKeyboardButton("« Back", callback_data='back_to_start')]
        ]
        await query.edit_message_caption(caption="📁 Manage your saved files.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == 'files_view_all':
        await query.message.delete()
        user_files = read_user_files(user.id)
        if not user_files.get('files'):
            await context.bot.send_message(user.id, "You have no saved files yet. Just send me a file to get started!")
        else:
            await context.bot.send_message(user.id, "📂 **Your Files**", parse_mode=ParseMode.MARKDOWN)
            for file_unique_id, file_info in user_files['files'].items():
                file_id = file_info.get('file_id')
                file_type = file_info.get('file_type')
                caption = file_info.get('caption', 'No caption')
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Delete", callback_data=f'files_delete_{file_unique_id}')
                ]])
                try:
                    if file_type == 'document':
                        await context.bot.send_document(user.id, document=file_id, caption=caption, reply_markup=keyboard)
                    elif file_type == 'photo':
                        await context.bot.send_photo(user.id, photo=file_id, caption=caption, reply_markup=keyboard)
                    elif file_type == 'video':
                        await context.bot.send_video(user.id, video=file_id, caption=caption, reply_markup=keyboard)
                    elif file_type == 'audio':
                        await context.bot.send_audio(user.id, audio=file_id, caption=caption, reply_markup=keyboard)
                    elif file_type == 'voice':
                        await context.bot.send_voice(user.id, voice=file_id, caption=caption, reply_markup=keyboard)
                except Exception as e:
                    await context.bot.send_message(user.id, f"⚠️ Could not send a file. It might have been deleted from Telegram's servers. Error: {e}")
            
        await context.bot.send_message(user.id, "Send /start to return to the main menu.")
        return

    if data.startswith('files_delete_'):
        file_unique_id = data.replace('files_delete_', '')
        user_files = read_user_files(user.id)
        if file_unique_id in user_files['files']:
            del user_files['files'][file_unique_id]
            save_user_files(user.id, user_files)
            await query.answer("File deleted successfully!", show_alert=True)
            await query.message.delete()
        else:
            await query.answer("File not found.", show_alert=True)
        return

    # --- Timer Menu ---
    if data == 'timer_menu':
        keyboard = [
            [InlineKeyboardButton("⏱️ Set Timer", callback_data='timer_set')],
            [InlineKeyboardButton("🛑 Stop My Timers", callback_data='timer_stop_all')],
            [InlineKeyboardButton("« Back", callback_data='back_to_start')]
        ]
        await query.edit_message_caption(caption="Select a timer tool:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == 'timer_set':
        context.user_data['state'] = 'awaiting_timer_duration'
        await query.edit_message_caption(
            caption="Please send the duration for the timer.\n\nExamples:\n`30s` for 30 seconds\n`10m` for 10 minutes\n`1h 5m 30s` for 1 hour, 5 minutes, and 30 seconds.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data='timer_menu')]]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == 'timer_stop_all':
        jobs = context.job_queue.get_jobs_by_name(f"timer_{user.id}")
        if not jobs:
            await query.answer("You have no active timers.", show_alert=True)
            return
        for job in jobs:
            job.schedule_removal()
        await query.answer(f"Stopped {len(jobs)} active timer(s).", show_alert=True)
        return

    # --- Timer Control Buttons (In-flight) ---
    if data.startswith('timer_add_5_'):
        job_name = data.replace('timer_add_5_', '')
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        if not current_jobs:
            await query.answer("Timer not found or already finished.", show_alert=True)
            return
        
        job = current_jobs[0]
        job.schedule_removal()
        new_run_time = job.next_t - time.time() + 300
        
        context.job_queue.run_once(
            time_up_callback,  # Use the same callback for consistency
            new_run_time,
            chat_id=job.chat_id,
            name=job_name,
            data={"job_name": job_name} # Pass the name along
        )
        
        await query.edit_message_text(f"✅ Timer extended by 5 minutes!")
        await query.answer("+5 minutes added!")
        return

    if data.startswith('timer_stop_'):
        job_name = data.replace('timer_stop_', '')
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        if not current_jobs:
            await query.answer("Timer not found or already finished.", show_alert=True)
            return
        
        for job in current_jobs:
            job.schedule_removal()
        
        await query.edit_message_text("🛑 Timer has been stopped.")
        await query.answer("Timer stopped.")
        return

    # --- Task Menu ---
    if data == 'tasks_menu':
        keyboard = [
            [InlineKeyboardButton("➕ Add Task", callback_data='tasks_add_select_cat')],
            [InlineKeyboardButton("📂 View Tasks", callback_data='tasks_view_select_cat')],
            [InlineKeyboardButton("🗂️ Manage Categories", callback_data='tasks_manage_cat_menu')],
            [InlineKeyboardButton("« Back", callback_data='back_to_start')]
        ]
        await query.edit_message_caption(caption="📝 Manage your tasks and ideas.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
        
    if data == 'tasks_manage_cat_menu':
        tasks_data = read_user_tasks(user.id)
        keyboard = []
        for category in tasks_data.get('categories', {}):
            if category != "General":
                keyboard.append([InlineKeyboardButton(f"🗑️ {category}", callback_data=f'tasks_cat_delete_{category}')])
        keyboard.append([InlineKeyboardButton("➕ Add New Category", callback_data='tasks_cat_add')])
        keyboard.append([InlineKeyboardButton("« Back", callback_data='tasks_menu')])
        await query.edit_message_caption(caption="Select a category to delete, or add a new one.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == 'tasks_cat_add':
        context.user_data['state'] = 'awaiting_category_name'
        await query.edit_message_caption(
            caption="Please send the name for the new category.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data='tasks_manage_cat_menu')]])
        )
        return

    if data.startswith('tasks_cat_delete_'):
        category_to_delete = data.replace('tasks_cat_delete_', '')
        tasks_data = read_user_tasks(user.id)
        if category_to_delete in tasks_data['categories'] and category_to_delete != "General":
            del tasks_data['categories'][category_to_delete]
            save_user_tasks(user.id, tasks_data)
            await query.answer(f"Category '{category_to_delete}' deleted.", show_alert=True)
            # Refresh the menu by simulating a click
            query.data = 'tasks_manage_cat_menu'
            await button_handler(update, context)
        else:
            await query.answer("Cannot delete this category.", show_alert=True)
        return

    if data == 'tasks_add_select_cat' or data == 'tasks_view_select_cat':
        action = 'add' if 'add' in data else 'view'
        tasks_data = read_user_tasks(user.id)
        categories = list(tasks_data.get('categories', {}).keys())
        if not categories:
            tasks_data['categories'] = {'General': []}
            save_user_tasks(user.id, tasks_data)
            categories = ['General']
        
        keyboard = [[InlineKeyboardButton(cat, callback_data=f'tasks_{action}_in_{cat}')] for cat in categories]
        keyboard.append([InlineKeyboardButton("« Back", callback_data='tasks_menu')])
        await query.edit_message_caption(caption=f"Select a category to {action} tasks in:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith('tasks_add_in_'):
        category = data.replace('tasks_add_in_', '')
        context.user_data['state'] = 'awaiting_task_text'
        context.user_data['task_category'] = category
        await query.edit_message_caption(
            caption=f"Enter the new task for the '{category}' category.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data='tasks_menu')]])
        )
        return
        
    if data.startswith('tasks_view_in_'):
        category = data.replace('tasks_view_in_', '')
        tasks_data = read_user_tasks(user.id)
        tasks = tasks_data.get('categories', {}).get(category, [])
        if not tasks:
            await query.answer(f"No tasks in '{category}'.", show_alert=True)
            return
        await query.message.delete()
        await context.bot.send_message(chat_id=user.id, text=f"📂 Tasks in '{category}':")
        for task in tasks:
            status_icon = "✅" if task.get('done') else "⚪️"
            task_text = task.get('text', 'No text')
            task_id = task.get('id')
            keyboard = [[
                InlineKeyboardButton("✅ Done" if not task.get('done') else "↩️ Undone", callback_data=f'task_toggle_{task_id}'),
                InlineKeyboardButton("❌ Delete", callback_data=f'task_delete_{task_id}')
            ]]
            await context.bot.send_message(chat_id=user.id, text=f"{status_icon} {task_text}", reply_markup=InlineKeyboardMarkup(keyboard))
        await context.bot.send_message(user.id, text="Send /start to return to the main menu.")
        return

    if data.startswith('task_toggle_') or data.startswith('task_delete_'):
        action, task_id = data.split('_', 2)[1], data.split('_', 2)[2]
        tasks_data = read_user_tasks(user.id)
        task_found_and_modified = False

        for category, tasks in tasks_data['categories'].items():
            for i, task in enumerate(tasks):
                if task.get('id') == task_id:
                    if action == 'toggle':
                        tasks[i]['done'] = not tasks[i].get('done', False)
                        status_icon = "✅" if tasks[i]['done'] else "⚪️"
                        new_keyboard = [[
                            InlineKeyboardButton("✅ Done" if not tasks[i]['done'] else "↩️ Undone", callback_data=f'task_toggle_{task_id}'),
                            InlineKeyboardButton("❌ Delete", callback_data=f'task_delete_{task_id}')
                        ]]
                        await query.edit_message_text(text=f"{status_icon} {task['text']}", reply_markup=InlineKeyboardMarkup(new_keyboard))
                    elif action == 'delete':
                        del tasks[i]
                        await query.message.delete()
                        await query.answer("Task deleted.", show_alert=False)
                    task_found_and_modified = True
                    break
            if task_found_and_modified:
                break
        
        if task_found_and_modified:
            save_user_tasks(user.id, tasks_data)
        else:
            await query.answer("Task not found.", show_alert=True)
            try:
                await query.message.delete()
            except:
                pass
        return
        
    # --- Group Media Saving ---
    if data.startswith('savegroup_'):
        if data == 'savegroup_cancel':
            await query.message.delete()
            return
        parts = data.split('_')
        if parts[1] == 'final':
            _, _, chat_id, msg_id, topic_name = parts
            chat_id, msg_id = int(chat_id), int(msg_id)
            topic_id_map = {'music': MUSIC_TOPIC_ID, 'voice': VOICE_TOP_ID}
            topic_id = topic_id_map.get(topic_name)
            try:
                await context.bot.copy_message(chat_id=chat_id, from_chat_id=chat_id, message_id=msg_id, message_thread_id=topic_id)
                await query.edit_message_text("✅ Saved successfully!")
            except Exception as e:
                await query.edit_message_text(f"⚠️ Error: Could not save message. Reason: {e}")
            return
        _, chat_id, msg_id, media_type = parts
        chat_id, msg_id = int(chat_id), int(msg_id)
        if media_type in ['audio', 'voice']:
            keyboard = [[
                InlineKeyboardButton("🎵 Music", callback_data=f"savegroup_final_{chat_id}_{msg_id}_music"),
                InlineKeyboardButton("🎤 Voice", callback_data=f"savegroup_final_{chat_id}_{msg_id}_voice")
            ]]
            await query.edit_message_text(text="Where should this be saved?", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        topic_id_map = {'photo': IMAGE_TOPIC_ID, 'video': VIDEO_TOPIC_ID}
        topic_id = topic_id_map.get(media_type)
        if topic_id:
            try:
                await context.bot.copy_message(chat_id=chat_id, from_chat_id=chat_id, message_id=msg_id, message_thread_id=topic_id)
            except Exception as e:
                await query.edit_message_text(f"⚠️ Error: Could not save message. Reason: {e}")
        else:
            await query.edit_message_text("Error: Topic ID not configured for this media type.")
        return

    # --- Navigation and Main Menu ---
    if data == 'back_to_start':
        context.user_data['state'] = None
        await start_command(update, context)
        return

    # --- Admin and Special Feature Handlers ---
    if user.id == ADMIN_CHAT_ID and (data.startswith('admin_') or data.startswith('gemini_') or data.startswith('vip_') or data.startswith('english_')):
        await handle_admin_buttons(update, context)
        return

    if data == 'learn_english':
        await handle_english_learning(update, context)
        return
        
    if data == 'movie_request':
        service_name = "فیلم"
        await query.answer(f"درخواست شما برای {service_name} به ادمین ارسال شد.", show_alert=True)
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❗️درخواست {service_name} جدید\n\n"
                                                                   f"کاربر: @{user.username or 'N/A'} (ID: <code>{user.id}</code>)\n"
                                                                   f"برای پاسخ، روی این پیام ریپلای کنید.",
                                       parse_mode=ParseMode.HTML)
        return
        
    # --- Music Menu ---
    if data == 'music_find_menu':
        auto_find_enabled = context.user_data.get('spotify_auto_find', False)
        auto_find_text = "✅ Auto-Find: ON" if auto_find_enabled else "❌ Auto-Find: OFF"
        music_keyboard = [
            [InlineKeyboardButton(auto_find_text, callback_data='music_toggle_autofind')],
            [InlineKeyboardButton("🎧 Spotify", callback_data='music_source_spotify')],
            [InlineKeyboardButton("☁️ SoundCloud", callback_data='music_source_soundcloud')],
            [InlineKeyboardButton("▶️ YouTube", callback_data='music_source_youtube')],
            [InlineKeyboardButton("« بازگشت", callback_data='back_to_start')]
        ]
        reply_markup = InlineKeyboardMarkup(music_keyboard)
        await query.edit_message_caption(caption="لطفاً سرویس مورد نظر خود را برای یافتن موسیقی انتخاب کنید:", reply_markup=reply_markup)
        return

    if data == 'music_toggle_autofind':
        current_state = context.user_data.get('spotify_auto_find', False)
        new_state = not current_state
        context.user_data['spotify_auto_find'] = new_state
        await query.answer(f"Spotify Auto-Find is now {'ON' if new_state else 'OFF'}", show_alert=True)
        # Refresh the menu by simulating a click
        query.data = 'music_find_menu'
        await button_handler(update, context)
        return

    if data.startswith('music_source_'):
        source = data.split('_')[2]
        if source == 'spotify':
            context.user_data['state'] = 'awaiting_spotify_link'
            await query.edit_message_caption(caption="✅ بسیار خب!\n\n"
                                                     "شما اکنون در حالت دریافت آهنگ از اسپاتیفای هستید. لینک‌های آهنگ مورد نظر خود را یکی پس از دیگری ارسال کنید.\n\n"
                                                     "برای خروج و بازگشت به منوی اصلی، دستور /start را ارسال کنید.",
                                             reply_markup=None)
        else:
            await query.answer(f"{source.capitalize()} به زودی اضافه خواهد شد!", show_alert=True)
        return

    if data == 'music_save_menu':
        keyboard = [
            [InlineKeyboardButton("➕ Add Music", callback_data='music_add')],
            [InlineKeyboardButton("📂 My Music", callback_data='music_view_all')],
            [InlineKeyboardButton("❤️ Liked Music", callback_data='music_liked_view')],
            [InlineKeyboardButton("« Back", callback_data='back_to_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption="💾 Manage your saved music library.", reply_markup=reply_markup)
        return

    if data == 'music_add':
        context.user_data['state'] = 'awaiting_music_file'
        await query.edit_message_caption(caption="🎵 Please send the audio file you want to save.",
                                             reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data='music_save_menu')]]))
        return

    if data == 'music_view_all' or data == 'music_liked_view':
        is_liked_view = data == 'music_liked_view'
        music_data = get_user_music_data(user.id)
        songs_to_show = {}
        if is_liked_view:
            title = "❤️ Your Liked Music"
            liked_song_ids = music_data.get('liked_songs', [])
            songs_to_show = {song_id: music_data['music'][song_id] for song_id in liked_song_ids if song_id in music_data['music']}
        else:
            title = "📂 Your Music Library"
            songs_to_show = music_data.get('music', {})
            
        if not songs_to_show:
            await query.answer("You have no music here yet!", show_alert=True)
            return
            
        await query.message.delete()
        await context.bot.send_message(chat_id=user.id, text=title)
        
        for file_unique_id, song_info in songs_to_show.items():
            song_title = song_info.get('title', 'Unknown Title')
            performer = song_info.get('performer', 'Unknown Artist')
            file_id = song_info.get('file_id')
            is_liked = file_unique_id in music_data.get('liked_songs', [])
            like_icon = "❤️" if is_liked else "🤍"
            keyboard = [[
                InlineKeyboardButton(f"{like_icon} Like", callback_data=f'music_like_{file_unique_id}'),
                InlineKeyboardButton("🗑️ Remove", callback_data=f'music_remove_{file_unique_id}')
            ]]
            caption = f"**{song_title}**\n_{performer}_"
            try:
                await context.bot.send_audio(chat_id=user.id, audio=file_id, caption=caption, parse_mode=ParseMode.MARKDOWN,
                                             reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                await context.bot.send_message(chat_id=user.id, text=f"Could not load song: {song_title}")
        
        await context.bot.send_message(chat_id=user.id, text="Send /start to go back to the main menu.")
        return

    if data.startswith('music_like_'):
        file_unique_id = data.split('_')[2]
        music_data = get_user_music_data(user.id)
        liked_songs = set(music_data.get('liked_songs', []))
        is_currently_liked = file_unique_id in liked_songs
        
        if is_currently_liked:
            liked_songs.remove(file_unique_id)
            await query.answer("Unliked!", show_alert=False)
        else:
            liked_songs.add(file_unique_id)
            await query.answer("Liked! ❤️", show_alert=False)
            
        music_data['liked_songs'] = list(liked_songs)
        save_user_music_data(user.id, music_data)
        
        new_like_icon = "❤️" if not is_currently_liked else "🤍"
        new_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{new_like_icon} Like", callback_data=f'music_like_{file_unique_id}'),
            InlineKeyboardButton("🗑️ Remove", callback_data=f'music_remove_{file_unique_id}')
        ]])
        await query.edit_message_reply_markup(reply_markup=new_keyboard)
        return

    if data.startswith('music_remove_'):
        file_unique_id_to_remove = data.split('_')[2]
        music_data = get_user_music_data(user.id)
        
        if file_unique_id_to_remove in music_data.get('music', {}):
            original_caption = query.message.caption
            del music_data['music'][file_unique_id_to_remove]
            if file_unique_id_to_remove in music_data.get('liked_songs', []):
                music_data['liked_songs'].remove(file_unique_id_to_remove)
            save_user_music_data(user.id, music_data)
            await query.answer("Music removed from your library.", show_alert=True)
            await query.edit_message_caption(caption=f"{original_caption}\n\n---\n🗑️ Removed from library.", reply_markup=None)
        else:
            await query.answer("This music file was already removed.", show_alert=True)
            await query.edit_message_reply_markup(reply_markup=None)
        return

    # --- VIP Menu ---
    if data == 'vip_request':
        vip_users = read_vip_users_data()
        user_vip_data = vip_users.get(str(user.id))
        if user_vip_data and user_vip_data.get("permissions", {}).get("view", False):
            await query.message.delete()
            user_perms = user_vip_data.get("permissions", {})
            keyboard_layout = []
            action_row = []
            if user_perms.get('add', False):
                action_row.append(InlineKeyboardButton("➕ Add Content", callback_data='vip_user_add'))
            if user_perms.get('delete', False):
                action_row.append(InlineKeyboardButton("🗑️ Manage Content", callback_data='vip_user_manage'))
            if action_row:
                keyboard_layout.append(action_row)
            keyboard_layout.append([InlineKeyboardButton("« Back to Main Menu", callback_data='back_to_start')])
            reply_markup = InlineKeyboardMarkup(keyboard_layout)
            await context.bot.send_message(chat_id=user.id, text="👑 Welcome to the VIP Area! 👑", reply_markup=reply_markup)
            
            vip_content = read_vip_content()
            if not vip_content:
                await context.bot.send_message(chat_id=user.id, text="The VIP area is currently empty.")
            else:
                for item in vip_content:
                    try:
                        if item['file_type'] == 'photo':
                            await context.bot.send_photo(chat_id=user.id, photo=item['file_id'], caption=item.get('caption', ''))
                        elif item['file_type'] == 'video':
                            await context.bot.send_video(chat_id=user.id, video=item['file_id'], caption=item.get('caption', ''))
                    except Exception:
                        pass
            return
        else:
            await query.answer("Your VIP access request has been sent to the admin.", show_alert=True)
            request_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Accept", callback_data=f'vip_accept_{user.id}'),
                 InlineKeyboardButton("❌ Ignore", callback_data=f'vip_ignore_{user.id}')]
            ])
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"👑 New VIP Access Request\n\n"
                         f"User: {user.first_name} (@{user.username or 'N/A'}) (ID: <code>{user.id}</code>)\n"
                         f"This user is requesting access to the VIP section.",
                    reply_markup=request_keyboard,
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
            return
            
    if data == 'vip_user_add':
        context.user_data['state'] = 'awaiting_vip_user_media'
        await query.edit_message_text(
            text="Please send the photo or video you want to add to the VIP section.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data='vip_request')]])
        )
        return

    if data == 'vip_user_manage':
        vip_content = read_vip_content()
        if not vip_content:
            await query.answer("There is no VIP content to manage.", show_alert=True)
            return
        await query.message.delete()
        await context.bot.send_message(chat_id=user.id, text="👑 VIP Content Management 👑")
        for item in vip_content:
            keyboard = [[
                InlineKeyboardButton("✏️ Edit Caption", callback_data=f"vip_user_edit_{item['content_id']}"),
                InlineKeyboardButton("❌ Remove", callback_data=f"vip_user_remove_{item['content_id']}")
            ]]
            caption = f"Content ID: `{item['content_id']}`\n\n{item.get('caption', '_No Caption_')}"
            try:
                if item['file_type'] == 'photo':
                    await context.bot.send_photo(chat_id=user.id, photo=item['file_id'], caption=caption,
                                                 reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
                elif item['file_type'] == 'video':
                    await context.bot.send_video(chat_id=user.id, video=item['file_id'], caption=caption,
                                                 reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                await context.bot.send_message(user.id, f"Could not load content {item['content_id']}. Error: {e}")
        await context.bot.send_message(user.id, "Use /start to return to the main menu.")
        return

    if data.startswith('vip_user_edit_'):
        content_id = data.split('_')[3]
        context.user_data['state'] = 'awaiting_vip_user_caption_edit'
        context.user_data['editing_vip_content_id'] = content_id
        await query.message.reply_text(f"Please send the new caption for content ID `{content_id}`.",
                                       parse_mode=ParseMode.MARKDOWN)
        await query.answer()
        return

    if data.startswith('vip_user_remove_'):
        content_id_to_remove = data.split('_')[3]
        vip_users = read_vip_users_data()
        user_vip_data = vip_users.get(str(user.id))
        if not (user_vip_data and user_vip_data.get("permissions", {}).get("delete", False)):
            await query.answer("You do not have permission to remove content.", show_alert=True)
            return
        vip_content = read_vip_content()
        new_content = [item for item in vip_content if item['content_id'] != content_id_to_remove]
        if len(new_content) < len(vip_content):
            write_vip_content(new_content)
            await query.edit_message_caption(caption="✅ Content removed successfully.", reply_markup=None)
            await query.answer("Removed!", show_alert=True)
        else:
            await query.answer("Could not find this item.", show_alert=True)
            await query.edit_message_reply_markup(reply_markup=None)
        return

    if data == 'AI_chat':
        keyboard = [
            [
                InlineKeyboardButton("✨ Gemini", callback_data='gemini_model_select_gemini'),
                InlineKeyboardButton("🧠 DeepSeek", callback_data='gemini_model_select_deepseek'),
            ],
            [
                InlineKeyboardButton("🤖 OpenAI/ChatGPT (Soon)", callback_data='gemini_model_select_openai')
            ],
            [InlineKeyboardButton("« Back", callback_data='back_to_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(
            caption="🤖 Please choose an AI model to chat with:",
            reply_markup=reply_markup
        )
        return

    if data == 'gemini_model_select_gemini':
        gemini_users = load_user_list(GEMINI_ACCESS_LIST_FILE)
        if user.id == ADMIN_CHAT_ID or user.id in gemini_users:
            context.user_data['state'] = 'awaiting_gemini_prompt'
            await query.message.delete()
            await context.bot.send_message(
                chat_id=user.id,
                text="🤖 **Hello there! I'm Gemini.**\n\nI am ready to chat with you. You can ask me anything you want. To exit this mode and return to the main menu, send /start.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data='back_to_start')]])
            )
        else:
            requested_users = load_user_list(GEMINI_REQUESTS_FILE)
            if user.id in requested_users:
                await query.answer("You have already requested access. Please wait for admin approval.", show_alert=True)
            else:
                await query.answer("You need admin approval to use this feature.", show_alert=True)
                request_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Approve Access", callback_data=f'gemini_accept_{user.id}'),
                     InlineKeyboardButton("❌ Deny", callback_data=f'gemini_ignore_{user.id}')]
                ])
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"❗️ Gemini Access Request\n\n"
                         f"User: @{user.username or 'N/A'} (ID: <code>{user.id}</code>)\n"
                         f"This user wants to use Gemini Chat.",
                    reply_markup=request_keyboard,
                    parse_mode=ParseMode.HTML
                )
                with open(GEMINI_REQUESTS_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"\n{user.id}")
                await query.edit_message_caption(
                    caption="⏳ Your request for Gemini access has been sent. Please wait...",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data='back_to_start')]])
                )
        return

    if data == 'gemini_model_select_deepseek':
        deepseek_users = load_user_list(DEEPSEEK_ACCESS_LIST_FILE)
        if user.id == ADMIN_CHAT_ID or user.id in deepseek_users:
            context.user_data['state'] = 'awaiting_deepseek_prompt'
            await query.edit_message_caption(
                caption="✅ You have access to DeepSeek!\n\n"
                        "Send any message you want. To exit this mode and return to the main menu, send /start.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data='back_to_start')]])
            )
        else:
            requested_users = load_user_list(DEEPSEEK_REQUESTS_FILE)
            if user.id in requested_users:
                await query.answer("You have already requested access. Please wait for admin approval.", show_alert=True)
            else:
                await query.answer("You need admin approval to use this feature.", show_alert=True)
                request_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Approve Access", callback_data=f'deepseek_accept_{user.id}'),
                     InlineKeyboardButton("❌ Deny", callback_data=f'deepseek_ignore_{user.id}')]
                ])
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"❗️ DeepSeek Access Request\n\n"
                         f"User: @{user.username or 'N/A'} (ID: <code>{user.id}</code>)\n"
                         f"This user wants to use DeepSeek Chat.",
                    reply_markup=request_keyboard,
                    parse_mode=ParseMode.HTML
                )
                with open(DEEPSEEK_REQUESTS_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"\n{user.id}")
                await query.edit_message_caption(
                    caption="⏳ Your request for DeepSeek access has been sent. Please wait...",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data='back_to_start')]])
                )
        return

    if data in ['gemini_model_select_openai']:
        await query.answer("This AI model will be available soon!", show_alert=True)
        return
        
    # --- Proxy/V2Ray Request Flow ---
    if data in ['proxy_request', 'v2ray_request']:
        service_type = "پروکسی" if data == 'proxy_request' else "کانفیگ V2Ray"
        cb_prefix = "quantity_" + ("proxy" if data == 'proxy_request' else "v2ray")
        keyboard = [[InlineKeyboardButton(str(q), callback_data=f'{cb_prefix}_{q}') for q in [10, 20, 30, 35, 40]],
                    [InlineKeyboardButton("« بازگشت", callback_data='back_to_start')]]
        await query.edit_message_caption(caption=f"چه تعداد {service_type} نیاز دارید؟",
                                             reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith('quantity_'):
        parts = data.split('_')
        req_type, quantity = parts[1], parts[2]
        delivery_keyboard = [
            [InlineKeyboardButton("📝 پیام متنی", callback_data=f'delivery_text_{req_type}_{quantity}')],
            [InlineKeyboardButton("📄 فایل", callback_data=f'delivery_file_{req_type}_{quantity}')],
            [InlineKeyboardButton("« بازگشت", callback_data=f'{req_type}_request')]
        ]
        await query.edit_message_caption(caption="چگونه می‌خواهید کانفیگ‌ها را دریافت کنید؟",
                                             reply_markup=InlineKeyboardMarkup(delivery_keyboard))
    elif data.startswith('delivery_'):
        if user.id not in load_user_list(WHITELIST_FILE):
            current_time = time.time()
            last_request_time = context.user_data.get('last_request_time', 0)
            if current_time - last_request_time < COOLDOWN_SECONDS:
                remaining = int(COOLDOWN_SECONDS - (current_time - last_request_time))
                await query.answer(f"لطفاً {remaining} ثانیه دیگر صبر کنید.", show_alert=True)
                return
        context.user_data['last_request_time'] = time.time()
        await query.edit_message_caption(caption="✅ بسیار خب! درخواست شما در حال ارسال است...", reply_markup=None)
        parts = data.split('_')
        delivery_method, req_type, quantity = parts[1], parts[2], parts[3]
        delivery_preference = "پیام متنی" if delivery_method == "text" else "فایل"
        service_name = "پروکسی" if req_type == "proxy" else "V2Ray"
        
        filename_example = "proxies" if req_type == "proxy" else "v2ray"
        delivery_instruction = f"\n\nTo respond, upload a file named:\n<code>{filename_example}_{user.id}.txt</code>" if delivery_method == 'file' else "\n\nTo respond, reply to this message with the text."

        admin_text = (
            f"User @{user.username or user.id} (ID: {user.id}) has a request.\n\n"
            f"🔹 <b>Service:</b> {service_name}\n"
            f"🔹 <b>Quantity:</b> {quantity}\n"
            f"🔹 <b>Delivery:</b> <b>{delivery_preference}</b>"
            f"{delivery_instruction}"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode='HTML')
        context.bot_data.setdefault('pending_requests', {})[user.id] = req_type
        asyncio.create_task(check_admin_response(context, user.id, update.effective_chat.id, req_type))
        final_caption = f"✅ درخواست شما برای {quantity} عدد {service_name} برای ادمین ارسال شد.\n\nلطفاً منتظر بمانید..."
        await query.edit_message_caption(caption=final_caption)
        await asyncio.sleep(4)
        await start_command(update, context)
        
    # --- Feedback Menu ---
    elif data == 'feedback_menu':
        keyboard = [[InlineKeyboardButton("✍️ ثبت ایده", callback_data='submit_feedback')],
                    [InlineKeyboardButton("👀 مشاهده ایده‌ها", callback_data='view_feedback')],
                    [InlineKeyboardButton("« بازگشت", callback_data='back_to_start')]]
        await query.edit_message_caption(caption="در این بخش می‌توانید ایده‌های خود را ثبت کرده یا ایده‌های دیگران را مشاهده کنید.",
                                             reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == 'submit_feedback':
        context.user_data['state'] = 'awaiting_feedback'
        await query.edit_message_caption(caption="📝 لطفاً ایده یا نظر خود را تایپ و ارسال کنید.",
                                             reply_markup=InlineKeyboardMarkup(
                                                 [[InlineKeyboardButton("« بازگشت", callback_data='feedback_menu')]]))
    elif data == 'view_feedback':
        await query.edit_message_caption(caption="در حال بارگذاری ایده‌ها...")
        feedback_list = read_feedback()
        if not feedback_list:
            await query.edit_message_caption(caption="هنوز ایده‌ای ثبت نشده است.", reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« بازگشت", callback_data='feedback_menu')]]))
        else:
            await query.message.delete()
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"ایده‌های ثبت شده ({len(feedback_list)} عدد):")
            for item in feedback_list:
                like_button = InlineKeyboardButton(f"❤️ لایک ({item['likes']})", callback_data=f"like_{item['id']}")
                await context.bot.send_message(chat_id=query.message.chat_id,
                                                     text=f"💡 ایده شماره {item['id']}:\n\n«{item['text']}»",
                                                     reply_markup=InlineKeyboardMarkup([[like_button]]))
            await context.bot.send_message(chat_id=query.message.chat_id,
                                                 text="برای بازگشت به منوی اصلی، دستور /start را ارسال کنید.")
    elif data.startswith('like_'):
        feedback_id = data.split('_')[1]
        all_feedback = read_feedback()
        liked_posts = context.user_data.get('liked_posts', set())
        if feedback_id in liked_posts:
            await query.answer("شما قبلاً این ایده را لایک کرده‌اید!", show_alert=False)
            return
            
        updated = False
        new_likes = 0
        for item in all_feedback:
            if item['id'] == feedback_id:
                item['likes'] = int(item['likes']) + 1
                new_likes = item['likes']
                updated = True
                break
            
        if updated:
            write_feedback(all_feedback)
            liked_posts.add(feedback_id)
            context.user_data['liked_posts'] = liked_posts
            new_button = InlineKeyboardButton(f"❤️ لایک ({new_likes})", callback_data=f"like_{feedback_id}")
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[new_button]]))
            await query.answer("شما این ایده را لایک کردید! ❤️")

# --- New Function for Saving User Files ---
async def save_user_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    
    file_info = {}
    if message.document:
        file = message.document
        file_info = {'file_id': file.file_id, 'file_unique_id': file.file_unique_id, 'file_type': 'document', 'file_name': file.file_name}
    elif message.photo:
        file = message.photo[-1] # Get the largest photo size
        file_info = {'file_id': file.file_id, 'file_unique_id': file.file_unique_id, 'file_type': 'photo'}
    elif message.video:
        file = message.video
        file_info = {'file_id': file.file_id, 'file_unique_id': file.file_unique_id, 'file_type': 'video'}
    elif message.audio:
        file = message.audio
        file_info = {'file_id': file.file_id, 'file_unique_id': file.file_unique_id, 'file_type': 'audio', 'title': file.title, 'performer': file.performer}
    elif message.voice:
        file = message.voice
        file_info = {'file_id': file.file_id, 'file_unique_id': file.file_unique_id, 'file_type': 'voice'}
    else:
        return

    # Check if the file already exists
    user_files = read_user_files(user.id)
    if file_info['file_unique_id'] in user_files['files']:
        await message.reply_text("This file is already saved in your library.")
        return

    # Store the file info and change state to ask for a caption
    context.user_data['pending_file_info'] = file_info
    context.user_data['state'] = 'awaiting_file_caption'
    
    await message.reply_text("✅ File received. Please send a caption for it, or send `.` if you don't want one.")

async def handle_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await pre_flight_checks(update, context):
        return
    user = update.effective_user
    message = update.message

    # Handle user replies to messages sent by the bot (on behalf of the admin)
    if message.reply_to_message and message.reply_to_message.from_user.is_bot:
        # This indicates a user is replying to a message that the admin sent them via the bot.
        # We should forward this reply back to the admin to continue the conversation.
        admin_alert_text = f"📩 New reply from @{user.username or user.id} (ID: {user.id}).\nReply to this message to respond."
        
        # Send the alert text to the admin
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_alert_text)
        
        # Forward the user's actual message (the reply) to the admin
        await context.bot.forward_message(
            chat_id=ADMIN_CHAT_ID,
            from_chat_id=user.id,
            message_id=message.message_id
        )
        return  # Stop processing here to not treat it as a new conversation

    state = context.user_data.get('state')
    message = update.message

    # --- Handle the OAuth callback first ---
    if message.text and 'code=' in message.text and 'state=' in message.text:
        # This is likely the OAuth callback URL
        if context.user_data.get('oauth_state') != message.text.split('state=')[1].split('&')[0]:
            await message.reply_text("❌ Security check failed. Please try the authorization process again.")
            context.user_data['oauth_state'] = None
            return

        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        try:
            flow.redirect_uri = REDIRECT_URI
            flow.fetch_token(code=message.text.split('code=')[1].split('&')[0])
            save_user_drive_creds(user.id, flow.credentials)
            await message.reply_text("✅ Your Google Drive is now connected! You can now use the upload feature.")
        except Exception as e:
            await message.reply_text(f"❌ An error occurred during authentication: {e}")
        finally:
            context.user_data['oauth_state'] = None
            await start_command(update, context)
        return

    # --- New Handler for incoming media ---
    if not state and (message.document or message.photo or message.video or message.audio or message.voice):
        await save_user_file(update, context)
        return

    # --- Existing state handlers for text inputs ---
    if state == 'awaiting_timer_duration':
        duration_seconds = parse_time_string(message.text)
        if duration_seconds <= 0:
            await message.reply_text("Invalid format. Please use a format like '10m 30s'.")
            return
        job_name = f"initial_timer_{user.id}_{uuid.uuid4()}"
        context.job_queue.run_once(
            time_up_callback, duration_seconds, chat_id=user.id, name=job_name, data={"job_name": job_name}
        )
        keyboard = [[InlineKeyboardButton("➕ Add 5 min", callback_data=f'timer_add_5_{job_name}'), InlineKeyboardButton("🛑 Stop Timer", callback_data=f'timer_stop_{job_name}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        sent_message = await message.reply_text(f"✅ Alarm set for {message.text}.", reply_markup=reply_markup)
        context.user_data['timer_control_message_id'] = sent_message.message_id
        context.user_data['state'] = None
        return

    if state == 'awaiting_drive_upload_file':
        # This handler must be able to handle incoming media messages, not just text.
        file = None
        file_type = None
        
        if message.photo:
            file = message.photo[-1] # Get the largest size
            file_type = 'photo'
        elif message.video:
            file = message.video
            file_type = 'video'
        elif message.document:
            file = message.document
            file_type = 'document'
        else:
            await message.reply_text("Invalid file type. Please send a photo, video, or document.")
            return

        service = await get_drive_service_for_user(user.id)
        if not service:
            await message.reply_text("❌ You are not authorized to use Google Drive. Please try the upload feature again to connect your account.")
            context.user_data['state'] = None
            return

        sent_msg = await message.reply_text("📥 Downloading file from Telegram...")
        file_path = f"{file.file_unique_id}.tmp"
        
        try:
            tg_file = await file.get_file()
            await tg_file.download_to_drive(file_path)
            await sent_msg.edit_text("☁️ Uploading to Google Drive...")
            
            # Determine mime type and filename
            mime_type = message.document.mime_type if message.document else ("image/jpeg" if file_type == 'photo' else "video/mp4")
            file_name = message.document.file_name if message.document else f"{file.file_unique_id}.{mime_type.split('/')[-1]}"
            
            uploaded_file_id = await upload_file_to_drive(service, file_path, file_name, mime_type, caption=message.caption or "")
        except Exception as e:
            await sent_msg.edit_text(f"❌ An error occurred: {e}")
            uploaded_file_id = None
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

        if uploaded_file_id:
            await sent_msg.edit_text(f"✅ File uploaded to Google Drive successfully!\nFile ID: `{uploaded_file_id}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await sent_msg.edit_text("❌ Failed to upload the file to Google Drive. Check the bot's console for errors.")
            
        context.user_data['state'] = None
        return

    if state == 'awaiting_category_name':
        new_category = message.text.strip()
        if not new_category:
            await message.reply_text("Category name cannot be empty.")
            return
        tasks_data = read_user_tasks(user.id)
        if new_category in tasks_data['categories']:
            await message.reply_text("This category already exists.")
            return
        tasks_data['categories'][new_category] = []
        save_user_tasks(user.id, tasks_data)
        await message.reply_text(f"✅ Category '{new_category}' created.")
        context.user_data.clear()
        await start_command(update, context)
        return

    if state == 'awaiting_task_text':
        category = context.user_data.get('task_category')
        task_text = message.text
        if not category:
            await message.reply_text("Error: No category selected. Please start over.")
        else:
            tasks_data = read_user_tasks(user.id)
            new_task = {"id": str(uuid.uuid4()), "text": task_text, "done": False}
            tasks_data['categories'].setdefault(category, []).append(new_task)
            save_user_tasks(user.id, tasks_data)
            await message.reply_text(f"✅ Task added to '{category}'.")
        context.user_data.clear()
        await start_command(update, context)
        return
    
    if state == 'awaiting_file_caption':
        file_info = context.user_data.get('pending_file_info')
        if not file_info:
            await message.reply_text("Error: Could not find the file information. Please start over with /start.")
            return

        user_files = read_user_files(user.id)
        file_unique_id = file_info['file_unique_id']
        file_info['caption'] = message.text if message.text != '.' else ''
        user_files['files'][file_unique_id] = file_info
        save_user_files(user.id, user_files)

        await message.reply_text("✅ File and caption saved successfully!")
        context.user_data.clear()
        return

    if state == 'awaiting_music_file':
        audio = message.audio
        if not audio:
            await message.reply_text("Invalid file type. Please send an audio file or type /start to exit.")
            return
        
        music_data = get_user_music_data(user.id)
        if audio.file_unique_id in music_data['music']:
            await message.reply_text("You have already saved this music file.")
            return
            
        music_data['music'][audio.file_unique_id] = {
            "file_id": audio.file_id, "file_name": audio.file_name,
            "title": audio.title, "performer": audio.performer,
            "duration": audio.duration, "group": "default"
        }
        save_user_music_data(user.id, music_data)
        context.user_data['state'] = None
        await message.reply_text(
            f"✅ Music '{audio.title or audio.file_name}' saved successfully!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Music Menu", callback_data='music_save_menu')]])
        )
        return
        
    if user.id == ADMIN_CHAT_ID and state and (state.startswith('awaiting_') or state.startswith('editing_') or state == 'awaiting_english_input'):
        await handle_admin_state_inputs(update, context)
        return

    if state == 'awaiting_vip_user_media':
        media = message.photo[-1] if message.photo else message.video
        file_type = 'photo' if message.photo else 'video'
        if not media: return
        context.user_data['pending_vip_user_media'] = {'file_id': media.file_id, 'content_id': media.file_unique_id, 'file_type': file_type}
        context.user_data['state'] = 'awaiting_vip_user_caption'
        await message.reply_text("✅ Media received. Now, please send the caption for this content.")
        return

    if state == 'awaiting_vip_user_caption':
        media_info = context.user_data.get('pending_vip_user_media')
        if not media_info:
            await message.reply_text("Error: Could not find the media file. Please start over with /start.")
        else:
            vip_content = read_vip_content()
            vip_content['content'].append({
                "file_id": media_info['file_id'],
                "content_id": media_info['content_id'],
                "file_type": media_info['file_type'],
                "caption": message.text if message.text != '.' else ''
            })
            save_vip_content(vip_content)
            await message.reply_text("✅ Media and caption saved successfully!")
            context.user_data.clear()
            return

    if state == 'awaiting_v2ray_config_title':
        title = message.text.strip()
        if not title:
            await message.reply_text("Title cannot be empty. Please enter a title for the V2Ray configuration:")
            return
            
        context.user_data['v2ray_config_title'] = title
        context.user_data['state'] = 'awaiting_v2ray_config_content'
        await message.reply_text(
            "Please enter the V2Ray configuration content:\n\n"
            "Note: The content should be a valid V2Ray configuration. "
            "Make sure it follows the correct JSON format for V2Ray."
        )
        return

    if state == 'awaiting_v2ray_config_content':
        content = message.text.strip()
        if not content:
            await message.reply_text("V2Ray configuration content cannot be empty. Please enter the configuration:")
            return
            
        # Basic validation to check if it looks like a V2Ray config
        if not is_valid_v2ray_config(content):
            await message.reply_text(
                "The entered text doesn't appear to be a valid V2Ray configuration. "
                "Please make sure you're entering a proper V2Ray JSON configuration.\n\n"
                "Enter the V2Ray configuration again:"
            )
            return
            
        # Save to Django backend
        try:
            title = context.user_data.get('v2ray_config_title', 'Untitled Config')
            django_url = "http://185.92.181.112:8000/tickets/api/config/"
            
            data = {
                "title": title,
                "text": content,
                "status": "off"  # Default to off
            }
            
            response = requests.post(django_url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                await message.reply_text(
                    f"✅ V2Ray configuration successfully added to the database!\n\n"
                    f"Title: {title}\n"
                    f"ID: {result.get('config', {}).get('id', 'N/A')}\n"
                    f"Status: {result.get('config', {}).get('status', 'N/A')}\n\n"
                    f"You can manage this configuration in the admin panel."
                )
            else:
                await message.reply_text(
                    f"⚠️ Failed to add V2Ray configuration to the database.\n"
                    f"Status code: {response.status_code}\n"
                    f"Please try again later."
                )
        except Exception as e:
            await message.reply_text(f"⚠️ Error adding V2Ray configuration to the database: {str(e)}")
            
        # Clear state
        context.user_data['state'] = None
        context.user_data.pop('v2ray_config_title', None)
        return

        vip_content.append({
            "content_id": media_info['content_id'],
            "file_id": media_info['file_id'],
            "file_type": media_info['file_type'],
            "caption": message.text,
            "added_by": user.id
        })
        write_vip_content(vip_content)
        await message.reply_text("✅ VIP content added successfully!")
        context.user_data.clear()
        await start_command(update, context)
        return

    if state == 'awaiting_vip_user_caption_edit':
        content_id = context.user_data.get('editing_vip_content_id')
        vip_users = read_vip_users_data()
        user_vip_data = vip_users.get(str(user.id))
        if not (user_vip_data and user_vip_data.get("permissions", {}).get("delete", False)):
            await message.reply_text("You do not have permission to edit content. Operation cancelled.")
        elif not content_id:
            await message.reply_text("Error: Could not find the content to edit. Operation cancelled.")
            
        # Clear state
        context.user_data['state'] = None
        context.user_data.pop('v2ray_config_title', None)
        return

    if state == 'awaiting_vip_user_caption_edit':
        content_id = context.user_data.get('editing_vip_content_id')
        vip_users = read_vip_users_data()
        user_vip_data = vip_users.get(str(user.id))
        if not (user_vip_data and user_vip_data.get("permissions", {}).get("delete", False)):
            await message.reply_text("You do not have permission to edit content. Operation cancelled.")
        elif not content_id:
            await message.reply_text("Error: Could not find the content to edit. Operation cancelled.")
            
        # Clear state
        context.user_data['state'] = None

        context.user_data.pop('v2ray_config_title', None)
        return

    if state == 'awaiting_vip_user_caption_edit':
        content_id = context.user_data.get('editing_vip_content_id')
        vip_users = read_vip_users_data()
        user_vip_data = vip_users.get(str(user.id))
        if not (user_vip_data and user_vip_data.get("permissions", {}).get("delete", False)):
            await message.reply_text("You do not have permission to edit content. Operation cancelled.")
        elif not content_id:
            await message.reply_text("Error: Could not find the content to edit. Operation cancelled.")
        else:
            vip_content = read_vip_content()
            updated = any(item['content_id'] == content_id for item in vip_content)
            if updated:
                for item in vip_content:
                    if item['content_id'] == content_id:
                        item['caption'] = message.text
                        break
                write_vip_content(vip_content)
                await message.reply_text(f"✅ Caption for content `{content_id}` updated.", parse_mode=ParseMode.MARKDOWN)
            else:
                await message.reply_text(f"❌ Error: Could not find content with ID `{content_id}`.", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        await start_command(update, context)
        return

    if not state and context.user_data.get('spotify_auto_find', False):
        link = message.text
        if link and ('spotify.com' in link or 'sptfy.com' in link) and link.startswith('http'):
            admin_text = (
                f"🎵 [Auto-Find] Request from Spotify\n\n"
                f"User: @{user.username or 'N/A'} (ID: {user.id})\n\n"
                f"To send the song, reply to this message with the audio file.\n\n"
                f"Admin command:\n"
                f"/spotify {link}"
            )
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
            await message.reply_text("✅ Auto-find triggered! Request sent to admin.")
            return

    if state == 'awaiting_spotify_link':
        link = message.text
        if not link or not link.startswith('http') or not ('spotify.com' in link or 'sptfy.com' in link):
            await message.reply_text("Invalid link. Please send a valid link from Spotify.")
            return
        admin_text = (
            f"🎵 New song request from Spotify\n\n"
            f"User: @{user.username or 'N/A'} (ID: {user.id})\n\n"
            f"To send the song, reply to this message with the audio file.\n\n"
            f"Admin command:\n"
            f"/spotify {link}"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
        await message.reply_text("✅ Your request has been sent. You can send the next link or exit with /start.")
        return

    if state == 'awaiting_gemini_prompt':
        prompt = message.text
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        response_text = await call_gemini_api(prompt)
        
        chunks = [response_text[i:i + MessageLimit.MAX_TEXT_LENGTH] for i in range(0, len(response_text), MessageLimit.MAX_TEXT_LENGTH)]
        for chunk in chunks:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN
                )
            except BadRequest:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)
        # Stay in the same state for continuous conversation
        return

    elif state == 'awaiting_deepseek_prompt':
        prompt = message.text
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        response_text = await call_deepseek_api(prompt)
        
        chunks = [response_text[i:i + MessageLimit.MAX_TEXT_LENGTH] for i in range(0, len(response_text), MessageLimit.MAX_TEXT_LENGTH)]
        for chunk in chunks:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN
                )
            except BadRequest:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)
        # Stay in the same state for continuous conversation
        return

    if state == 'awaiting_feedback':
        try:
            await message.delete()
        except:
            pass
        all_feedback = read_feedback()
        new_id = (max([int(f['id']) for f in all_feedback]) + 1) if all_feedback else 1
        all_feedback.append({'id': str(new_id), 'text': message.text, 'likes': 0})
        write_feedback(all_feedback)
        context.user_data['state'] = None
        sent_msg = await context.bot.send_message(chat_id=update.effective_chat.id,
                                                  text="✅ Thank you! Your feedback has been saved.")
        asyncio.create_task(schedule_message_deletion(context.bot, sent_msg.chat_id, sent_msg.message_id, 4))
        await asyncio.sleep(3)
        await start_command(update, context)
    else:
        admin_alert_text = f"📩 New message from @{user.username or user.id} (ID: {user.id}).\nReply to this message to respond."
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_alert_text)
        await context.bot.forward_message(chat_id=ADMIN_CHAT_ID, from_chat_id=update.effective_chat.id,
                                          message_id=message.message_id)


# --- Admin-Specific Functions and Handlers ---
async def get_main_admin_keyboard():
    lock_status = get_bot_lock_status()
    lock_text = "🔒 قفل کردن ربات" if lock_status == "unlocked" else "🔓 باز کردن ربات"
    lock_callback = "admin_lock_bot" if lock_status == "unlocked" else "admin_unlock_bot"
    password_status = "🔑 تنظیم / تغییر رمز" if get_bot_password() else "🔑 تنظیم رمز عبور"
    clear_pass_button = [InlineKeyboardButton("🗑 حذف رمز عبور", callback_data='admin_password_clear')] if get_bot_password() else []
    keyboard = [
        [InlineKeyboardButton("✅ مدیریت لیست سفید", callback_data='admin_whitelist_menu')],
        [InlineKeyboardButton("🚫 مدیریت لیست سیاه", callback_data='admin_blocklist_menu')],
        [InlineKeyboardButton("✨ مدیریت دسترسی Gemini", callback_data='admin_gemini_menu')],
        [InlineKeyboardButton("🎓 Manage English Access", callback_data='admin_english_menu')],
        [InlineKeyboardButton("🤖 Exported Bots", callback_data='admin_exported_bots')],
        [InlineKeyboardButton(lock_text, callback_data=lock_callback)],
        [InlineKeyboardButton(password_status, callback_data='admin_password_set')],
        clear_pass_button,
        [InlineKeyboardButton("« بازگشت به منوی اصلی", callback_data='back_to_start')]
    ]
    return InlineKeyboardMarkup([row for row in keyboard if row])

async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user

    if data.startswith('english_answer_'):
        answer = data.replace('english_answer_', '', 1)
        with open(IXI_FLOWER_ENGLISH_FILE, 'a', encoding='utf-8') as f:
            f.write(f"User: {answer}\n")
        await handle_english_learning(update, context, user_input=answer)
        return

    if data == 'vip_request' and user.id == ADMIN_CHAT_ID: # Admin clicks main VIP button
        keyboard = [
            [InlineKeyboardButton("➕ Add Content", callback_data='vip_admin_add')],
            [InlineKeyboardButton("🗑️ Manage Content", callback_data='vip_admin_manage')],
            [InlineKeyboardButton("👥 Manage Users", callback_data='vip_admin_users')],
            [InlineKeyboardButton("« Back", callback_data='back_to_start')]
        ]
        await query.edit_message_caption(
            caption="👑 **VIP Admin Panel**\n\nSelect an option to manage the VIP section.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith('deepseek_accept_'):
        user_id_to_add = int(data.split('_')[2])
        deepseek_users = load_user_list(DEEPSEEK_ACCESS_LIST_FILE)
        if user_id_to_add not in deepseek_users:
            with open(DEEPSEEK_ACCESS_LIST_FILE, 'a', encoding='utf-8') as f:
                f.write(f"\n{user_id_to_add}")
            await query.answer(f"User {user_id_to_add} added to DeepSeek access list.", show_alert=True)
            try:
                await context.bot.send_message(chat_id=user_id_to_add,
                                               text="✅ Congratulations! The admin has approved your request. You can now use DeepSeek Chat.")
            except Exception as e:
                await query.answer(f"User added, but could not notify them: {e}", show_alert=True)
        else:
            await query.answer("This user already has access.", show_alert=True)
        remove_user_from_list(user_id_to_add, DEEPSEEK_REQUESTS_FILE)
        await query.edit_message_text(text=f"✅ DeepSeek access for user {user_id_to_add} approved.", reply_markup=None)
        return

    if data.startswith('deepseek_ignore_'):
        user_id_to_ignore = int(data.split('_')[2])
        remove_user_from_list(user_id_to_ignore, DEEPSEEK_REQUESTS_FILE)
        await query.answer(f"Request from user {user_id_to_ignore} was ignored.", show_alert=True)
        await query.edit_message_text(text=f"❌ DeepSeek access request for user {user_id_to_ignore} ignored.", reply_markup=None)
        return

    if data == 'vip_admin_add':
        context.user_data['state'] = 'awaiting_vip_media'
        await query.edit_message_caption(
            caption="Please send the photo or video you want to add to the VIP section.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data='vip_request')]])
        )
        return

    if data == 'vip_admin_manage':
        vip_content = read_vip_content()
        if not vip_content:
            await query.answer("There is no VIP content to manage.", show_alert=True)
            return
        await query.message.delete()
        await context.bot.send_message(user.id, text="👑 **VIP Content Management**")
        for item in vip_content:
            keyboard = [[
                InlineKeyboardButton("✏️ Edit Caption", callback_data=f"vip_edit_{item['content_id']}"),
                InlineKeyboardButton("❌ Remove", callback_data=f"vip_remove_{item['content_id']}")
            ]]
            caption = f"Content ID: `{item['content_id']}`\n\n{item.get('caption', '_No Caption_')}"
            try:
                if item['file_type'] == 'photo':
                    await context.bot.send_photo(chat_id=user.id, photo=item['file_id'], caption=caption,
                                                 reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
                elif item['file_type'] == 'video':
                    await context.bot.send_video(chat_id=user.id, video=item['file_id'], caption=caption,
                                                 reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                await context.bot.send_message(user.id, f"Could not load content {item['content_id']}. Error: {e}")
        await context.bot.send_message(user.id, "End of list. Use /start to return to the main menu.")
        return

    if data.startswith('vip_edit_'):
        content_id = data.split('_')[2]
        context.user_data['state'] = 'awaiting_vip_caption_edit'
        context.user_data['editing_vip_content_id'] = content_id
        await query.message.reply_text(f"Please send the new caption for content ID `{content_id}`.",
                                       parse_mode=ParseMode.MARKDOWN)
        await query.answer()
        return

    if data.startswith('vip_remove_'):
        content_id_to_remove = data.split('_')[2]
        vip_content = read_vip_content()
        new_content = [item for item in vip_content if item['content_id'] != content_id_to_remove]
        if len(new_content) < len(vip_content):
            write_vip_content(new_content)
            await query.edit_message_caption(caption="✅ Content removed successfully.", reply_markup=None)
            await query.answer("Removed!", show_alert=True)
        else:
            await query.answer("Could not find this item.", show_alert=True)
            await query.edit_message_reply_markup(reply_markup=None)
        return

    if data == 'vip_admin_users':
        await handle_admin_user_list(update, context, 'vip')
        return

    if data.startswith('admin_vip_manage_'):
        user_id_to_manage = int(data.split('_')[3])
        await manage_specific_vip_menu(update, context, user_id_to_manage)
        return

    if data.startswith('admin_vip_perm_toggle_'):
        parts = data.split('_')
        user_id_to_manage = int(parts[4])
        perm_to_toggle = parts[5]
        await toggle_vip_permission(update, context, user_id_to_manage, perm_to_toggle)
        return

    if data.startswith('vip_accept_'):
        user_id_to_accept = int(data.split('_')[2])
        vip_users_data = read_vip_users_data()
        if str(user_id_to_accept) not in vip_users_data:
            try:
                user_info = await context.bot.get_chat(user_id_to_accept)
                vip_users_data[str(user_id_to_accept)] = {
                    "username": user_info.username or user_info.first_name,
                    "permissions": {"view": True, "add": False, "delete": False, "filter": False}
                }
                save_vip_users_data(vip_users_data)
                await query.answer(f"User {user_id_to_accept} granted VIP access.", show_alert=True)
                await context.bot.send_message(chat_id=user_id_to_accept,
                                               text="👑 Congratulations! You now have access to the VIP section. Click the VIP button on the main menu to see the content.")
            except Exception as e:
                await query.answer(f"Could not add user. Error: {e}", show_alert=True)
        else:
            await query.answer("This user already has VIP access.", show_alert=True)
        await query.edit_message_text(text=f"✅ User {user_id_to_accept} has been added to the VIP list.", reply_markup=None)
        return

    if data.startswith('vip_ignore_'):
        user_id_to_ignore = int(data.split('_')[2])
        try:
            await context.bot.send_message(chat_id=user_id_to_ignore,
                                           text="😔 Unfortunately, your recent VIP request was not approved at this time.")
            await query.answer("User notified of rejection.", show_alert=True)
        except Exception as e:
            await query.answer(f"User rejected, but could not notify them. Error: {e}", show_alert=True)
        await query.edit_message_text(text=f"❌ VIP request from user {user_id_to_ignore} was ignored.", reply_markup=None)
        return

    if data.startswith('gemini_accept_'):
        user_id_to_add = int(data.split('_')[2])
        gemini_users = load_user_list(GEMINI_ACCESS_LIST_FILE)
        if user_id_to_add not in gemini_users:
            with open(GEMINI_ACCESS_LIST_FILE, 'a', encoding='utf-8') as f:
                f.write(f"\n{user_id_to_add}")
            await query.answer(f"User {user_id_to_add} added to Gemini access list.", show_alert=True)
            try:
                await context.bot.send_message(chat_id=user_id_to_add,
                                               text="✅ Congratulations! The admin has approved your request. You can now use Gemini Chat.")
            except Exception as e:
                await query.answer(f"User added, but could not notify them: {e}", show_alert=True)
        else:
            await query.answer("This user already has access.", show_alert=True)
        remove_user_from_list(user_id_to_add, GEMINI_REQUESTS_FILE)
        await query.edit_message_text(text=f"✅ Gemini access for user {user_id_to_add} approved.", reply_markup=None)
        return

    if data.startswith('gemini_ignore_'):
        user_id_to_ignore = int(data.split('_')[2])
        remove_user_from_list(user_id_to_ignore, GEMINI_REQUESTS_FILE)
        await query.answer(f"Request from user {user_id_to_ignore} was ignored.", show_alert=True)
        await query.edit_message_text(text=f"❌ Gemini access request for user {user_id_to_ignore} ignored.", reply_markup=None)
        return

    if data == 'admin_panel':
        admin_photo_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRQoXhnbsSfHV_QgKw9CaAJ2ZuhkF0tyhxsMw&s"
        try:
            await query.message.delete()
        except:
            pass
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=admin_photo_url,
            caption="⚙️ <b>Admin Panel</b>\n\nSelect an option to manage:",
            reply_markup=await get_main_admin_keyboard(),
            parse_mode='HTML'
        )
        return

    if data in ['admin_whitelist_menu', 'admin_blocklist_menu', 'admin_gemini_menu', 'admin_english_menu']:
        list_key = data.split('_')[1]
        await handle_admin_user_list(update, context, list_key)
        return

    if data in ['admin_whitelist_add', 'admin_blocklist_add', 'admin_whitelist_remove', 'admin_blocklist_remove',
                'admin_gemini_add', 'admin_gemini_remove', 'admin_vip_add', 'admin_vip_remove',
                'admin_english_add', 'admin_english_remove']:
        parts = data.split('_')
        list_type, action = parts[1], parts[2]
        back_cb = 'vip_admin_users' if list_type == 'vip' else f'admin_{list_type}_menu'
        action_text = "add to" if action == "add" else "remove from"
        list_name_map = {"whitelist": "Whitelist", "blocklist": "Blocklist", "gemini": "Gemini Access", "vip": "VIP Users", "english": "English Access"}
        list_name = list_name_map[list_type]
        context.user_data['state'] = f'awaiting_{list_type}_{action}_id'
        await query.edit_message_caption(
            caption=f"Please send the numerical user ID to {action_text} the {list_name}.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data=back_cb)]])
        )
        return

    if data in ['admin_lock_bot', 'admin_unlock_bot']:
        new_status = "locked" if data == 'admin_lock_bot' else "unlocked"
        set_bot_lock_status(new_status)
        await query.answer(f"Bot is now {new_status}.", show_alert=True)
        await query.edit_message_reply_markup(reply_markup=await get_main_admin_keyboard())

    if data == 'admin_password_set':
        context.user_data['state'] = 'awaiting_password'
        await query.edit_message_caption(caption="Please send the new password.",
                                             reply_markup=InlineKeyboardMarkup(
                                                 [[InlineKeyboardButton("« Cancel", callback_data='admin_panel')]]))
    if data == 'admin_password_clear':
        set_bot_password("")
        await query.answer("Password cleared successfully.", show_alert=True)
        await query.edit_message_reply_markup(reply_markup=await get_main_admin_keyboard())

async def handle_admin_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE, list_key: str):
    query = update.callback_query
    if list_key == 'vip':
        await query.edit_message_caption(caption="Fetching VIP user list...")
        vip_users_data = read_vip_users_data()
        keyboard = []
        if not vip_users_data:
            keyboard.append([InlineKeyboardButton("No VIP users found.", callback_data="no_op")])
        else:
            for user_id, user_data in vip_users_data.items():
                perms = user_data.get("permissions", {})
                p_view = "V" if perms.get('view') else "v"
                p_add = "A" if perms.get('add') else "a"
                p_del = "D" if perms.get('delete') else "d"
                p_filter = "F" if perms.get('filter') else "f"
                perms_str = f"[{p_view}{p_add}{p_del}{p_filter}]"
                username = user_data.get("username", f"ID: {user_id}")
                button_text = f"{perms_str} @{username}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f'admin_vip_manage_{user_id}')])
        keyboard.append([
            InlineKeyboardButton("➕ Add User by ID", callback_data="admin_vip_add"),
            InlineKeyboardButton("➖ Remove User by ID", callback_data="admin_vip_remove")
        ])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="vip_request")])
        await query.edit_message_caption(
            caption="👥 **Manage VIP Users**\n\nSelect a user to manage their permissions.\n`V=View, A=Add, D=Delete, F=Filter`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
        
    list_map = {
        'whitelist': ("Whitelist", WHITELIST_FILE, "admin_whitelist_add", "admin_whitelist_remove", "admin_panel"),
        'blocklist': ("Blocklist", BLOCKLIST_FILE, "admin_blocklist_add", "admin_blocklist_remove", "admin_panel"),
        'gemini': ("Gemini Access", GEMINI_ACCESS_LIST_FILE, "admin_gemini_add", "admin_gemini_remove", "admin_panel"),
        'english': ("English Access", ENGLISH_ACCESS_LIST_FILE, "admin_english_add", "admin_english_remove", "admin_panel"),
    }
    list_name, file_path, add_cb, remove_cb, back_cb = list_map[list_key]
    user_ids = load_user_list(file_path)
    id_list_str = "\n".join(map(str, user_ids)) if user_ids else "Empty"
    text = f"<b>Managing {list_name}</b>\n\nCurrent Users:\n<code>{id_list_str}</code>"
    keyboard = [
        [InlineKeyboardButton("➕ Add User", callback_data=add_cb),
         InlineKeyboardButton("➖ Remove User", callback_data=remove_cb)],
        [InlineKeyboardButton("« Back", callback_data=back_cb)]
    ]
    await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def manage_specific_vip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    all_users_data = read_vip_users_data()
    user_data = all_users_data.get(str(user_id))
    if not user_data:
        await query.answer("User not found in VIP list.", show_alert=True)
        await handle_admin_user_list(update, context, 'vip')
        return
    user_perms = user_data.get("permissions", {"view": True, "add": False, "delete": False, "filter": False})
    username = user_data.get("username", f"ID: {user_id}")
    keyboard = [
        [InlineKeyboardButton(f"{'✅' if user_perms.get('view', False) else '❌'} See Content", callback_data=f"admin_vip_perm_toggle_{user_id}_view")],
        [InlineKeyboardButton(f"{'✅' if user_perms.get('add', False) else '❌'} Add Content", callback_data=f"admin_vip_perm_toggle_{user_id}_add")],
        [InlineKeyboardButton(f"{'✅' if user_perms.get('delete', False) else '❌'} Remove Content", callback_data=f"admin_vip_perm_toggle_{user_id}_delete")],
        [InlineKeyboardButton(f"{'✅' if user_perms.get('filter', False) else '❌'} Filter Content", callback_data=f"admin_vip_perm_toggle_{user_id}_filter")],
        [InlineKeyboardButton("« Back to VIP List", callback_data='vip_admin_users')]
    ]
    caption = f"Managing permissions for:\n**@{username}**"
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def toggle_vip_permission(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, perm: str):
    all_users_data = read_vip_users_data()
    user_data = all_users_data.get(str(user_id))
    if not user_data:
        await update.callback_query.answer("User not found.", show_alert=True)
        return
    user_data["permissions"][perm] = not user_data["permissions"].get(perm, False)
    all_users_data[str(user_id)] = user_data
    save_vip_users_data(all_users_data)
    await manage_specific_vip_menu(update, context, user_id)

async def handle_sendto_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Helper function to process content for the 'send to' command."""
    message_to_send = update.message
    target_user_id = context.user_data.get('sendto_target_id')

    context.user_data['sendto_message_id'] = message_to_send.message_id
    
    keyboard = [[
        InlineKeyboardButton("✅ Yes, Send", callback_data='sendto_confirm_yes'),
        InlineKeyboardButton("❌ Cancel", callback_data='sendto_confirm_no')
    ]]
    await message_to_send.reply_text(
        f"Are you sure you want to send this to user `{target_user_id}`?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['state'] = 'awaiting_sendto_confirmation'

async def sendto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiates sending a message to a specific user ID."""
    try:
        target_user_id = int(re.search(r"send to (\d+)", update.message.text, re.IGNORECASE).group(1))
    except (AttributeError, IndexError, ValueError):
        await update.message.reply_text("Invalid format. Please use: `send to <user_id>`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        await context.bot.get_chat(target_user_id)
    except BadRequest:
        await update.message.reply_text(f"❌ User with ID `{target_user_id}` not found or I can't talk to them.", parse_mode=ParseMode.MARKDOWN)
        return

    context.user_data['state'] = 'awaiting_sendto_content'
    context.user_data['sendto_target_id'] = target_user_id
    
    await update.message.reply_text(
        f"✅ OK. Please send the message you want to forward to user `{target_user_id}`.",
        parse_mode=ParseMode.MARKDOWN
    )

async def sendto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiates sending a message to a specific user ID."""
    try:
        target_user_id = int(re.search(r"send to (\d+)", update.message.text, re.IGNORECASE).group(1))
    except (AttributeError, IndexError, ValueError):
        await update.message.reply_text("Invalid format. Please use: `send to <user_id>`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        await context.bot.get_chat(target_user_id)
    except BadRequest:
        await update.message.reply_text(f"❌ User with ID `{target_user_id}` not found or I can't talk to them.", parse_mode=ParseMode.MARKDOWN)
        return

    context.user_data['state'] = 'awaiting_sendto_content'
    context.user_data['sendto_target_id'] = target_user_id
    
    await update.message.reply_text(
        f"✅ OK. Please send the message you want to forward to user `{target_user_id}`.",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Routes all non-command, non-reply messages from the admin based on state."""
    state = context.user_data.get('state')

    if state == 'awaiting_sendto_content':
        message_to_send = update.message
        target_user_id = context.user_data.get('sendto_target_id')

        context.user_data['sendto_message_id'] = message_to_send.message_id
        
        keyboard = [[
            InlineKeyboardButton("✅ Yes, Send", callback_data='sendto_confirm_yes'),
            InlineKeyboardButton("❌ Cancel", callback_data='sendto_confirm_no')
        ]]
        await message_to_send.reply_text(
            f"Are you sure you want to send this to user `{target_user_id}`?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['state'] = 'awaiting_sendto_confirmation'
        return
    
    # Fallback to old logic if no state matches
    if update.message.document:
        await handle_admin_document(update, context)
    elif update.message.photo or update.message.video:
        await handle_admin_media(update, context)
    elif update.message.text:
        await handle_admin_state_inputs(update, context)

async def handle_admin_state_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') == 'awaiting_sendto_content':
        await handle_sendto_content(update, context)
        return
    if context.user_data.get('state') == 'awaiting_sendto_content':
        await handle_sendto_content(update, context)
        return
    state = context.user_data.get('state')
    text = update.message.text
    admin_user = update.effective_user
    context.user_data['state'] = None # Clear state immediately

    if state == 'awaiting_english_input':
        with open(IXI_FLOWER_ENGLISH_FILE, 'a', encoding='utf-8') as f:
            f.write(f"User: {text}\n")
        await handle_english_learning(update, context, user_input=text)
        return

    if state == 'awaiting_vip_caption_edit':
        content_id = context.user_data.get('editing_vip_content_id')
        if not content_id:
            await update.message.reply_text("Error: Could not find content to edit. Operation cancelled.")
        else:
            vip_content = read_vip_content()
            updated = any(item['content_id'] == content_id for item in vip_content)
            if updated:
                for item in vip_content:
                    if item['content_id'] == content_id:
                        item['caption'] = text; break
                write_vip_content(vip_content)
                await update.message.reply_text(f"✅ Caption for content `{content_id}` updated.", parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(f"❌ Error: Could not find content with ID `{content_id}`.", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        await start_command(update, context)
        return

    if state in ['awaiting_deepseek_add_id', 'awaiting_deepseek_remove_id']:
        list_map = {
            'deepseek': (DEEPSEEK_ACCESS_LIST_FILE, "DeepSeek Access"),
        }
        file_path, list_name = list_map['deepseek']
        
        if 'add' in state:
            user_ids = load_user_list(file_path)
            if user_id in user_ids:
                await update.message.reply_text(f"User {user_id} is already in the {list_name}.")
            else:
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n{user_id}")
                await update.message.reply_text(f"✅ User {user_id} added to the {list_name}.")
        elif 'remove' in state:
            if remove_user_from_list(user_id, file_path):
                await update.message.reply_text(f"✅ User {user_id} removed from the {list_name}.")
            else:
                await update.message.reply_text(f"User {user_id} was not found in the {list_name}.")
        await start_command(update, context)
        return

    if state == 'awaiting_vip_caption':
        media_info = context.user_data.get('pending_vip_media')
        if not media_info:
            await update.message.reply_text("Error: Could not find the media file. Please start over.")
        else:
            vip_content = read_vip_content()
            vip_content.append({
                "content_id": media_info['content_id'], "file_id": media_info['file_id'],
                "file_type": media_info['file_type'], "caption": text, "added_by": admin_user.id
            })
            write_vip_content(vip_content)
            await update.message.reply_text("✅ VIP content added successfully!")
        context.user_data.clear()
        await start_command(update, context)
        return

    if state == 'awaiting_password':
        set_bot_password(text)
        await update.message.reply_text(f"✅ Password set successfully to `{text}`.", parse_mode='Markdown')
        context.user_data.clear()
        await start_command(update, context)
        return

    try:
        user_id = int(text)
    except ValueError:
        await update.message.reply_text("Error: ID must be a number. Operation cancelled.")
        await start_command(update, context)
        return

    if state in ['awaiting_vip_add_id', 'awaiting_vip_remove_id']:
        vip_users_data = read_vip_users_data()
        user_id_str = str(user_id)
        if state == 'awaiting_vip_add_id':
            if user_id_str in vip_users_data:
                await update.message.reply_text(f"User {user_id} is already a VIP.")
            else:
                try:
                    user_info = await context.bot.get_chat(user_id)
                    vip_users_data[user_id_str] = {"username": user_info.username or user_info.first_name,
                                                     "permissions": {"view": True, "add": False, "delete": False, "filter": False}}
                    save_vip_users_data(vip_users_data)
                    await update.message.reply_text(f"✅ User @{user_info.username or user_info.first_name} added to VIPs.")
                except BadRequest:
                    await update.message.reply_text(f"❌ Could not find user with ID {user_id}.")
        elif state == 'awaiting_vip_remove_id':
            if user_id_str in vip_users_data:
                username = vip_users_data[user_id_str].get("username", user_id_str)
                del vip_users_data[user_id_str]
                save_vip_users_data(vip_users_data)
                await update.message.reply_text(f"✅ User @{username} removed from VIPs.")
            else:
                await update.message.reply_text(f"User {user_id} was not found in the VIP list.")
        await start_command(update, context)
        return
        
    list_map = {
        'whitelist': (WHITELIST_FILE, "Whitelist"), 'blocklist': (BLOCKLIST_FILE, "Blocklist"),
        'gemini': (GEMINI_ACCESS_LIST_FILE, "Gemini Access"), 'english': (ENGLISH_ACCESS_LIST_FILE, "English Access"),
    }
    file_path, list_name = next(((path, name) for key, (path, name) in list_map.items() if state in [f'awaiting_{key}_add_id', f'awaiting_{key}_remove_id']), (None, None))
    
    if file_path:
        if 'add' in state:
            user_ids = load_user_list(file_path)
            if user_id in user_ids:
                await update.message.reply_text(f"User {user_id} is already in the {list_name}.")
            else:
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n{user_id}")
                await update.message.reply_text(f"✅ User {user_id} added to the {list_name}.")
        elif 'remove' in state:
            if remove_user_from_list(user_id, file_path):
                await update.message.reply_text(f"✅ User {user_id} removed from the {list_name}.")
            else:
                await update.message.reply_text(f"User {user_id} was not found in the {list_name}.")
        await start_command(update, context)

async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles replies from the admin to either a forwarded message from a user
    or a notification message from the bot, and forwards the admin's message
    to the original user.
    """
    admin_message = update.message
    reply_to_message = admin_message.reply_to_message

    # This handler is only for admin replies.
    if not reply_to_message:
        return

    target_user_id = None

    # Case 1: Admin replied to a message that was forwarded from a user.
    if reply_to_message.forward_origin:
        # In python-telegram-bot v20+, we check `forward_origin`.
        # We do a local import to ensure compatibility without modifying global scope.
        from telegram import MessageOriginUser
        if isinstance(reply_to_message.forward_origin, MessageOriginUser):
             target_user_id = reply_to_message.forward_origin.sender_user.id
    
    # Case 2: Admin replied to one of the bot's notification messages.
    elif reply_to_message.from_user.is_bot and (reply_to_message.text or reply_to_message.caption):
        original_bot_message_text = reply_to_message.text or reply_to_message.caption
        # This regex looks for (ID: 12345) or (ID: <code>12345</code>)
        match = re.search(r"\(ID: (?:<code>)?(\d+)(?:</code>)?\)", original_bot_message_text)
        if match:
            target_user_id = int(match.group(1))

    if not target_user_id:
        return

    try:
        # Forward the admin's message (any type) to the target user.
        sent_msg = await context.bot.copy_message(
            chat_id=target_user_id,
            from_chat_id=admin_message.chat_id,
            message_id=admin_message.message_id
        )
        
        # Confirm to the admin.
        conf_msg = await admin_message.reply_text("✅ Message forwarded to user.")

        # Check if the original message being replied to was a request that needs deletion.
        original_text = ""
        if reply_to_message.text:
            original_text = reply_to_message.text.lower()
        elif reply_to_message.caption:
            original_text = reply_to_message.caption.lower()

        # Keywords that trigger message deletion for the user.
        deletion_keywords = ['vip', 'v2ray', 'proxy', 'پروکسی']
        
        if any(keyword in original_text for keyword in deletion_keywords):
            # Schedule deletion only for specific message types.
            asyncio.create_task(schedule_message_deletion(context.bot, target_user_id, sent_msg.message_id, 30))
        
        # Always delete the admin's confirmation message to keep the chat clean.
        asyncio.create_task(schedule_message_deletion(context.bot, conf_msg.chat_id, conf_msg.message_id, 10))

    except Exception as e:
        await admin_message.reply_text(f"⚠️ Could not send message to user {target_user_id}. Reason: {e}")

async def handle_admin_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('state') == 'awaiting_sendto_content':
        await handle_sendto_content(update, context)
        return
    doc = update.message.document
    if not doc or not doc.file_name: return
    
    match = re.match(r"(proxies|v2ray)_(\d+)\.txt", doc.file_name)
    if match:
        target_user_id = int(match.group(2))
        context.bot_data.get('pending_requests', {}).pop(target_user_id, None)
        try:
            await context.bot.send_document(chat_id=target_user_id, document=doc.file_id, caption=update.message.caption)
            await update.message.reply_text(f"✅ File sent successfully to user {target_user_id}.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Could not send file to user {target_user_id}. Reason: {e}")
        return

    target_path = None
    if doc.file_name == PROXY_BACKUP_FILE: target_path = PROXY_BACKUP_FILE
    elif doc.file_name == V2RAY_BACKUP_FILE: target_path = V2RAY_BACKUP_FILE
    
    if target_path:
        try:
            new_file = await doc.get_file()
            await new_file.download_to_drive(target_path)
            await update.message.reply_text(f"✅ Backup file `{target_path}` updated successfully.", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error updating file: {e}")
        return
    
    # Check if this is a V2Ray config file sent in response to a user request
    # If so, also upload it to the Django backend
    if doc.file_name.endswith('.txt') and 'v2ray' in doc.file_name.lower():
        try:
            # Download the file content
            file_obj = await doc.get_file()
            file_content = await file_obj.download_as_bytearray()
            
            # Upload to Django backend
            django_url = "http://185.92.181.112:8000/tickets/api/upload/"
            files = {'file': (doc.file_name, io.BytesIO(bytes(file_content)), 'text/plain')}
            response = requests.post(django_url, files=files, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                await update.message.reply_text(
                    f"✅ File also uploaded to Django backend!\n"
                    f"File ID: {result.get('file_id')}\n"
                    f"File Name: {result.get('file_name')}\n"
                    f"You can view all uploaded files at: http://185.92.181.112:8000/tickets/api/files/\n"
                    f"Or access this specific file at: http://185.92.181.112:8000/tickets/api/files/{result.get('file_id')}/"
                )
            else:
                await update.message.reply_text(f"⚠️ File uploaded to user but failed to upload to Django backend. Status: {response.status_code}")
        except Exception as e:
            await update.message.reply_text(f"⚠️ File uploaded to user but failed to upload to Django backend. Error: {str(e)}")

async def handle_admin_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('state') == 'awaiting_sendto_content':
        await handle_sendto_content(update, context)
        return
    state = context.user_data.get('state')
    if state == 'awaiting_vip_media':
        message = update.message
        media = message.photo[-1] if message.photo else message.video
        file_type = 'photo' if message.photo else 'video'
        if not media: return
        context.user_data['pending_vip_media'] = {'file_id': media.file_id, 'content_id': media.file_unique_id, 'file_type': file_type}
        context.user_data['state'] = 'awaiting_vip_caption'
        await message.reply_text("✅ Media received. Now, please send the caption for this content.")
    else:
        # Fallback to general message handler if not in a specific state
        await handle_user_messages(update, context)


# --- Group-Specific Handlers ---
async def handle_admin_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not (update.message and update.message.reply_to_message) or update.effective_chat.id != TARGET_GROUP_ID:
        return
    if update.message.reply_to_message.message_thread_id is not None: return

    original_message = update.message.reply_to_message
    media_type = None
    if original_message.photo: media_type = 'photo'
    elif original_message.video: media_type = 'video'
    elif original_message.audio: media_type = 'audio'
    elif original_message.voice: media_type = 'voice'
    if not media_type: return

    keyboard = [[
        InlineKeyboardButton("✅ Yes, Save It", callback_data=f"savegroup_{update.effective_chat.id}_{original_message.message_id}_{media_type}"),
        InlineKeyboardButton("❌ No", callback_data=f"savegroup_cancel")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text="Do you want to save this message to its topic?", reply_markup=reply_markup)

async def keyword_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not (update.message and update.message.text): return
    command = update.message.text.strip().lower()
    user = update.effective_user
    
    keyword_replies = {
        'spotify': '@spotifysavesbot', 'youtube': '@SaveMedia_bot',
        'music finder': '@dr_music_finder_bot', 'movie': '@alphadlbot', 'bot': '@BotFather',
    }
    if command in keyword_replies:
        await update.message.reply_text(keyword_replies[command])
        return

    if command == 'movie':
        service_name = "فیلم"
        await update.message.reply_text(f"✅ Your request for a {service_name} has been sent to the admin.")
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"❗️New {service_name} request from a group\n\n"
                 f"User: @{user.username or 'N/A'} (ID: <code>{user.id}</code>)\n"
                 f"Reply to this message to respond to the user.",
            parse_mode=ParseMode.HTML
        )
        return

# --- AI and Learning Functions ---
async def call_gemini_api(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        ]
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(GEMINI_API_URL, json=payload, headers=headers, timeout=40.0)
            response.raise_for_status()
            data = response.json()
            if not data.get('candidates'):
                reason = data.get('promptFeedback', {}).get('blockReason', 'Unknown').replace('_', ' ').title()
                return f"❌ **Request Blocked:** Your prompt was blocked.\nReason: *{reason}*"
            return data['candidates'][0]['content']['parts'][0]['text']
        except httpx.HTTPStatusError as e:
            error_details = f"Server returned an error ({e.response.status_code})."
            try: error_details += f"\nDetails: `{e.response.json().get('error', {}).get('message', 'N/A')}`"
            except json.JSONDecodeError: pass
            return f"❌ **API Error:**\n{error_details}"
        except httpx.TimeoutException:
            return "❌ **API Error:** The request to Gemini timed out. Please try again later."
        except Exception as e:
            return f"❌ **An Unexpected Error Occurred:**\n`{str(e)}`"

async def handle_english_learning(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str = None):
    query = update.callback_query
    user = update.effective_user
    context.user_data['state'] = 'awaiting_english_input'
    
    prompt_instruction = (
        "You are an English teacher bot. Your goal is to assess the user's English level and then teach them. "
        "Keep your responses concise and friendly. If your question can be answered with short, simple options "
        "(like 'Yes/No' or multiple choice), please provide them at the end of your message in the format: "
        "[BUTTONS]Option 1|Option 2|Option 3"
    )
    if user_input:
        prompt = f"{prompt_instruction}\n\nContinue the English lesson. The user's last response was: '{user_input}'"
    else:
        if os.path.exists(IXI_FLOWER_ENGLISH_FILE):
            open(IXI_FLOWER_ENGLISH_FILE, 'w').close() # Clear file
        prompt = f"{prompt_instruction}\n\nStart a new English lesson. First, assess my English level by asking a few simple questions."
    
    await context.bot.send_chat_action(chat_id=user.id, action='typing')
    response_text = await call_gemini_api(prompt)
    
    with open(IXI_FLOWER_ENGLISH_FILE, 'a', encoding='utf-8') as f:
        f.write(f"Gemini: {response_text}\n")
        
    main_text = response_text
    keyboard = []
    if '[BUTTONS]' in response_text:
        parts = response_text.split('[BUTTONS]')
        main_text = parts[0].strip()
        button_titles = [btn.strip() for btn in parts[1].split('|')]
        row = [InlineKeyboardButton(title, callback_data=f'english_answer_{title}') for title in button_titles]
        keyboard = [row[i:i + 2] for i in range(0, len(row), 2)] 
        
    keyboard.append([InlineKeyboardButton("« Back to Main Menu", callback_data='back_to_start')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.message.delete()
        await context.bot.send_message(chat_id=user.id, text=main_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(main_text, reply_markup=reply_markup)

def main() -> None:
    initialize_files()
    application = Application.builder().token(BOT_TOKEN).build()
    application.bot_data['pending_requests'] = {}

    admin_filter = filters.Chat(chat_id=ADMIN_CHAT_ID)
    private_chat_filter = filters.ChatType.PRIVATE
    group_chat_filter = filters.ChatType.GROUPS
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.Regex(r"^send to \d+") & filters.Chat(chat_id=ADMIN_CHAT_ID), sendto_command))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    
    application.add_handler(MessageHandler(filters.Regex(r"^send to \d+") & admin_filter & ~filters.COMMAND & ~filters.REPLY, sendto_command))
    application.add_handler(MessageHandler(filters.REPLY & ~filters.COMMAND & admin_filter, admin_reply_handler))
    application.add_handler(MessageHandler(~filters.COMMAND & ~filters.REPLY & admin_filter, admin_message_router))

    application.add_handler(MessageHandler(group_chat_filter & filters.TEXT & ~filters.COMMAND, keyword_group_handler))
    
    application.add_handler(MessageHandler(private_chat_filter & ~filters.COMMAND, handle_user_messages))
    
    application.run_polling()

if __name__ == "__main__":
    main()