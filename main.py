import asyncio
import os
import sys
import tempfile
import time
import platform
import shutil
import subprocess
import pyautogui
import cv2
import psutil
import pyperclip
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("MAIN_BOT_TOKEN")
MY_ID = int(os.getenv("MY_ID", "1455766271"))
BOT_NAME = "BotForPC"

# --- ПУТИ ДЛЯ PYINSTALLER ---
def get_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
CURRENT_DIR = BASE_DIR

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- АВТОЗАГРУЗКА ---
def add_to_autostart():
    try:
        import winreg as reg
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath(__file__)
        
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, reg.KEY_SET_VALUE)
        reg.SetValueEx(key, BOT_NAME, 0, reg.REG_SZ, '"' + exe_path + '"')
        reg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Ошибка автозагрузки: {e}")
        return False

def remove_from_autostart():
    try:
        import winreg as reg
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, reg.KEY_SET_VALUE)
        reg.DeleteValue(key, BOT_NAME)
        reg.CloseKey(key)
        return True
    except Exception:
        return False

def check_first_run():
    marker_file = os.path.join(BASE_DIR, ".autostart_added")
    if not os.path.exists(marker_file):
        if add_to_autostart():
            with open(marker_file, "w") as f:
                f.write("1")
            print("✅ Добавлено в автозагрузку!")

check_first_run()

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРЫ ---
def get_main_kb():
    """Основное меню с кнопками в 2 колонки."""
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📸 Скриншот"), KeyboardButton(text="📹 Фото")],
        [KeyboardButton(text="🎤 Звук"), KeyboardButton(text="💻 Инфо")],
        [KeyboardButton(text="📊 Мониторинг"), KeyboardButton(text="🔊 Громкость")],
        [KeyboardButton(text="📁 Файлы"), KeyboardButton(text="⌨️ Ввод")],
        [KeyboardButton(text="🖱️ Мышь"), KeyboardButton(text="🪟 Окна")],
        [KeyboardButton(text="⚙️ Система"), KeyboardButton(text="📋 Буфер")],
        [KeyboardButton(text="❓ Помощь")]
    ], resize_keyboard=True)


def get_menu_kb():
    """Дополнительное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить меню", callback_data="menu:refresh")],
        [InlineKeyboardButton(text="🗑️ Удалить бота", callback_data="delete:confirm")]
    ])


def get_volume_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔇 Мут", callback_data="vol:mute"),
         InlineKeyboardButton(text="🔊 100%", callback_data="vol:100")],
        [InlineKeyboardButton(text="🔉 -10%", callback_data="vol:-10"),
         InlineKeyboardButton(text="🔈 +10%", callback_data="vol:+10")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]
    ])


def get_mouse_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️", callback_data="mouse:up"),
         InlineKeyboardButton(text="⬇️", callback_data="mouse:down")],
        [InlineKeyboardButton(text="⬅️", callback_data="mouse:left"),
         InlineKeyboardButton(text="➡️", callback_data="mouse:right")],
        [InlineKeyboardButton(text="🖱️ ЛКМ", callback_data="mouse:click"),
         InlineKeyboardButton(text="🖱️ ПКМ", callback_data="mouse:rclick")],
        [InlineKeyboardButton(text="🖱️ ДКМ", callback_data="mouse:dblclick")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]
    ])


def get_windows_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪟 Свернуть все", callback_data="win:minimize")],
        [InlineKeyboardButton(text="🖥️ Рабочий стол", callback_data="win:desktop")],
        [InlineKeyboardButton(text="🔄 Alt+Tab", callback_data="win:alttab")],
        [InlineKeyboardButton(text="❌ Закрыть окно", callback_data="win:close")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]
    ])


def get_system_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔌 Выключить", callback_data="sys:shutdown"),
         InlineKeyboardButton(text="🔄 Перезагрузить", callback_data="sys:restart")],
        [InlineKeyboardButton(text="😴 Сон", callback_data="sys:sleep"),
         InlineKeyboardButton(text="🔒 Блокировка", callback_data="sys:lock")],
        [InlineKeyboardButton(text="📊 Процессы", callback_data="sys:processes")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]
    ])


def get_files_kb(page: int, current_path=DOWNLOAD_DIR):
    try:
        items = os.listdir(current_path)
        items = sorted(items, key=lambda x: (not os.path.isdir(os.path.join(current_path, x)), x.lower()))
        
        total_pages = (len(items) - 1) // 10 + 1 if items else 1
        start = page * 10
        end = start + 10
        page_items = items[start:end]

        builder = []
        if current_path != DOWNLOAD_DIR:
            builder.append([InlineKeyboardButton(text="📁 ..", callback_data=f"filedir:..")])
        
        for item in page_items:
            item_path = os.path.join(current_path, item)
            if os.path.isdir(item_path):
                builder.append([InlineKeyboardButton(text=f"📁 {item}", callback_data=f"filedir:{item}")])
            else:
                size = os.path.getsize(item_path)
                size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
                builder.append([InlineKeyboardButton(text=f"📄 {item} ({size_str})", callback_data=f"fileaction:{item}")])

        nav_btns = []
        if page > 0:
            nav_btns.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"filepage:{page-1}"))
        if page < total_pages - 1:
            nav_btns.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"filepage:{page+1}"))
        
        if nav_btns:
            builder.append(nav_btns)
        builder.append([InlineKeyboardButton(text="⬅️ В главное меню", callback_data="menu:main")])
        
        return InlineKeyboardMarkup(inline_keyboard=builder)
    except Exception:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:files")]
        ])


def get_file_action_kb(file_name: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Открыть", callback_data=f"fileopen:{file_name}")],
        [InlineKeyboardButton(text="📤 Отправить", callback_data=f"filesend:{file_name}")],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"filedelete:{file_name}")],
        [InlineKeyboardButton(text="📋 Копировать", callback_data=f"filecopy:{file_name}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:files")]
    ])


def get_info_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="info:refresh")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]
    ])


def get_monitoring_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="monitoring:refresh")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]
    ])


def get_help_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]
    ])


# --- ЛОГИКА ---
def is_owner(user_id):
    return user_id == MY_ID


def get_system_info():
    """Красивое отображение информации о системе."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:")
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "Неизвестно"
    
    info = (
        f"🖥 <b>СИСТЕМА:</b>\n"
        f"├ ОС: <code>{platform.system()} {platform.release()}</code>\n"
        f"├ ПК: <code>{platform.node()}</code>\n"
        f"├ User: <code>{os.getlogin()}</code>\n"
        f"└ IP: <code>{local_ip}</code>\n\n"
        f"⏱ <b>Время работы:</b> <code>{str(uptime).split('.')[0]}</code>\n\n"
        f"📊 <b>РЕСУРСЫ:</b>\n"
        f"├ CPU: <code>{cpu_percent}%</code>\n"
        f"├ RAM: <code>{ram.percent}%</code> ({ram.used / 1024**3:.1f} GB)\n"
        f"└ DISK: <code>{disk.percent}%</code> ({disk.used / 1024**3:.1f} GB)\n\n"
        f"📈 <b>Процессы:</b> <code>{len(psutil.pids())}</code>"
    )
    return info


def get_monitoring_info():
    """Мониторинг в реальном времени."""
    cpu_percent = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:")
    net = psutil.net_io_counters()
    
    try:
        temps = psutil.sensors_temperatures()
        cpu_temp = temps.get('coretemp', [{}])[0].get('current', 'N/A')
    except:
        cpu_temp = "N/A"
    
    # Проверка на критические значения
    alerts = []
    if cpu_percent > 90:
        alerts.append("⚠️ <b>CPU > 90%!</b>")
    if ram.percent > 90:
        alerts.append("⚠️ <b>RAM > 90%!</b>")
    if disk.percent > 95:
        alerts.append("⚠️ <b>DISK > 95%!</b>")
    
    info = (
        f"📊 <b>МОНИТОРИНГ:</b>\n\n"
        f"🧠 <b>CPU:</b> <code>{cpu_percent}%</code>\n"
        f"🌡️ <b>Температура:</b> <code>{cpu_temp}°C</code>\n\n"
        f"💾 <b>RAM:</b> <code>{ram.percent}%</code>\n"
        f"└ <code>{ram.used / 1024**3:.1f} GB / {ram.total / 1024**3:.1f} GB</code>\n\n"
        f"💿 <b>DISK C:</b> <code>{disk.percent}%</code>\n\n"
        f"📡 <b>СЕТЬ:</b>\n"
        f"├ ⬆️ <code>{net.bytes_sent / 1024**2:.1f} MB</code>\n"
        f"└ ⬇️ <code>{net.bytes_recv / 1024**2:.1f} MB</code>"
    )
    
    if alerts:
        info = "\n".join(alerts) + "\n\n" + info
    
    return info


@dp.message(Command("start"))
async def start(message: types.Message):
    if not is_owner(message.from_user.id):
        await message.answer("⛔️ <b>ДОСТУП ЗАПРЕЩЁН!</b>\n\nВы не являетесь владельцем.", parse_mode="HTML")
        return
    
    await message.answer(
        f"👋 <b>Привет, {message.from_user.first_name}!</b>\n\n"
        "🤖 <b>BotForPC — удалённое управление</b>\n\n"
        "📋 <b>Функции:</b>\n"
        "├ 📸 Скриншоты\n"
        "├ 📹 Фото с камеры\n"
        "├ 🎤 Запись звука\n"
        "├ 💻 Инфо о системе\n"
        "├ 📊 Мониторинг\n"
        "├ 🔊 Громкость\n"
        "├ 📁 Файлы\n"
        "├ ⌨️ Ввод текста\n"
        "├ 🖱️ Мышь\n"
        "├ 🪟 Окна\n"
        "├ ⚙️ Система\n"
        "└ 📋 Буфер\n\n"
        f"🔐 <b>ID:</b> <code>{MY_ID}</code>\n"
        "✅ <b>Автозагрузка:</b> Активна\n\n"
        "👇 <b>Меню:</b>",
        reply_markup=get_main_kb(),
        parse_mode="HTML"
    )


@dp.message(Command("info"))
async def cmd_info(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer(get_system_info(), reply_markup=get_info_kb(), parse_mode="HTML")


@dp.message(Command("clean"))
async def cmd_clean(message: types.Message):
    """Полное удаление бота с ПК."""
    if not is_owner(message.from_user.id):
        return

    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ ОТМЕНА", callback_data="clean:cancel")],
        [InlineKeyboardButton(text="✅ УДАЛИТЬ", callback_data="clean:confirm")]
    ])

    await message.answer(
        "⚠️ <b>ПОЛНОЕ УДАЛЕНИЕ!</b>\n\n"
        "Это действие:\n"
        "├ 🗑️ Удалит бота из автозагрузки\n"
        "├ 📁 Удалит папку downloads\n"
        "├ 📝 Удалит временные файлы\n"
        "├ 🗑️ Удалит файл .autostart_added\n"
        "└ ❌ Остановит бота\n\n"
        "<b>ВЫ УВЕРЕНЫ?</b>",
        reply_markup=confirm_kb,
        parse_mode="HTML"
    )


@dp.message(F.text == "❓ Помощь")
async def help_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer(
        "📚 <b>СПРАВКА</b>\n\n"
        "<b>📸 Скриншот</b> — снимок экрана\n"
        "<b>📹 Фото</b> — фото с веб-камеры\n"
        "<b>🎤 Звук</b> — запись 5 сек аудио\n"
        "<b>💻 Инфо</b> — CPU, RAM, диск, IP\n"
        "<b>📊 Мониторинг</b> — ресурсы онлайн\n"
        "<b>🔊 Громкость</b> — управление звуком\n"
        "<b>📁 Файлы</b> — проводник downloads\n"
        "<b>⌨️ Ввод</b> — ввод текста\n"
        "<b>🖱️ Мышь</b> — управление курсором\n"
        "<b>🪟 Окна</b> — управление окнами\n"
        "<b>⚙️ Система</b> — выключение/сон\n"
        "<b>📋 Буфер</b> — чтение/запись\n\n"
        "📥 <b>Файлы:</b> до 20 МБ",
        reply_markup=get_help_kb(),
        parse_mode="HTML"
    )


@dp.message(F.text == "🔄 Обновить")
async def refresh_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer("🔄 <b>Меню обновлено!</b>", reply_markup=get_main_kb(), parse_mode="HTML")


@dp.message(F.text == "🗑️ УДАЛИТЬ БОТА")
async def delete_bot_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ ОТМЕНА", callback_data="delete:cancel")],
        [InlineKeyboardButton(text="✅ УДАЛИТЬ", callback_data="delete:confirm")]
    ])
    
    await message.answer(
        "⚠️ <b>УДАЛЕНИЕ БОТА!</b>\n\n"
        "Это действие:\n"
        "├ 🗑️ Удалит из автозагрузки\n"
        "├ 📁 Удалит downloads\n"
        "├ 📝 Удалит временные файлы\n"
        "└ ❌ Остановит бота\n\n"
        "<b>ВЫ УВЕРЕНЫ?</b>",
        reply_markup=confirm_kb,
        parse_mode="HTML"
    )


@dp.message(F.text == "📸 Скриншот")
async def take_screenshot(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    
    wait_msg = await message.answer("📸 <b>Скриншот...</b>", parse_mode="HTML")
    
    try:
        temp_path = os.path.join(tempfile.gettempdir(), f"screen_{int(time.time())}.png")
        pyautogui.screenshot(temp_path)
        
        width, height = pyautogui.size()
        await message.answer_photo(
            photo=types.FSInputFile(temp_path),
            caption=f"✅ <b>Готово!</b>\n📊 <code>{width}x{height}</code>"
        )
        os.remove(temp_path)
        await wait_msg.delete()
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"❌ <b>Ошибка:</b> <code>{e}</code>", parse_mode="HTML")


@dp.message(F.text == "📹 Фото")
async def take_photo(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    
    wait_msg = await message.answer("📹 <b>Камера...</b>", parse_mode="HTML")
    
    cap = None
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            await wait_msg.delete()
            await message.answer("❌ <b>Камера недоступна!</b>", parse_mode="HTML")
            return
        
        for _ in range(5):
            cap.read()
            time.sleep(0.1)
        
        ret, frame = cap.read()
        
        if ret and frame is not None:
            temp_path = os.path.join(tempfile.gettempdir(), f"cam_{int(time.time())}.jpg")
            cv2.imwrite(temp_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            await message.answer_photo(
                photo=types.FSInputFile(temp_path),
                caption="✅ <b>Фото готово!</b>"
            )
            os.remove(temp_path)
        else:
            await wait_msg.delete()
            await message.answer("❌ <b>Не удалось!</b>", parse_mode="HTML")
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"❌ <b>Ошибка:</b> <code>{e}</code>", parse_mode="HTML")
    finally:
        if cap is not None:
            cap.release()
    
    await wait_msg.delete()


@dp.message(F.text == "🎤 Звук")
async def record_audio(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    
    wait_msg = await message.answer("🎤 <b>Запись...</b>", parse_mode="HTML")
    
    try:
        import sounddevice as sd
        from scipy.io.wavfile import write
        
        sample_rate = 44100
        duration = 5
        temp_path = os.path.join(tempfile.gettempdir(), f"audio_{int(time.time())}.wav")
        
        default_device = sd.query_devices(kind="input")
        channels = min(2, default_device["max_input_channels"])
        
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=channels)
        sd.wait()
        write(temp_path, sample_rate, recording)
        
        await message.answer_audio(
            types.FSInputFile(temp_path),
            caption=f"✅ <b>Готово!</b>\n⏱️ <code>{duration} сек</code>"
        )
        os.remove(temp_path)
        await wait_msg.delete()
    except ImportError:
        await wait_msg.delete()
        await message.answer("❌ <b>Установите:</b>\n<code>pip install sounddevice scipy</code>", parse_mode="HTML")
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"❌ <b>Ошибка:</b> <code>{e}</code>", parse_mode="HTML")


@dp.message(F.text == "💻 Инфо")
async def sys_info_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer(get_system_info(), reply_markup=get_info_kb(), parse_mode="HTML")


@dp.message(F.text == "📊 Мониторинг")
async def monitoring_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer(get_monitoring_info(), reply_markup=get_monitoring_kb(), parse_mode="HTML")


@dp.message(F.text == "🔊 Громкость")
async def volume_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        if devices is None:
            await message.answer("❌ <b>Устройство не найдено!</b>", parse_mode="HTML")
            return
        
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        current_volume = int(volume.GetMasterVolumeLevelScalar() * 100)
        is_muted = volume.GetMute()
        
        status = "🔇 Мут" if is_muted else f"🔊 {current_volume}%"
        
        await message.answer(
            f"🔊 <b>ГРОМКОСТЬ</b>\n\n"
            f"📊 <b>Уровень:</b> <code>{status}</code>",
            reply_markup=get_volume_kb(),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            "❌ <b>Недоступно!</b>\n\n"
            "<code>pip install pycaw comtypes</code>\n\n"
            f"Ошибка: <code>{e}</code>",
            parse_mode="HTML"
        )


@dp.message(F.text == "📁 Файлы")
async def show_files(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer(f"📁 <b>ПРОВОДНИК</b>\n<code>{DOWNLOAD_DIR}</code>", reply_markup=get_files_kb(0), parse_mode="HTML")


@dp.message(F.text == "⌨️ Ввод")
async def input_text_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer(
        "⌨️ <b>ВВОД ТЕКСТА</b>\n\n"
        "📝 <b>Отправь текст</b> — я введу его на клавиатуре.\n\n"
        "⚠️ <b>Внимание:</b> Текст будет введён в активное окно!",
        parse_mode="HTML"
    )


@dp.message(F.text == "🖱️ Мышь")
async def mouse_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer("🖱️ <b>МЫШЬ</b>\n\n👇 <b>Выберите:</b>", reply_markup=get_mouse_kb(), parse_mode="HTML")


@dp.message(F.text == "🪟 Окна")
async def windows_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer("🪟 <b>ОКНА</b>\n\n👇 <b>Выберите:</b>", reply_markup=get_windows_kb(), parse_mode="HTML")


@dp.message(F.text == "⚙️ Система")
async def system_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer("⚙️ <b>СИСТЕМА</b>\n\n👇 <b>Выберите:</b>", reply_markup=get_system_kb(), parse_mode="HTML")


@dp.message(F.text == "📋 Буфер")
async def clipboard_cmd(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    
    try:
        clipboard_content = pyperclip.paste()
        if clipboard_content:
            await message.answer(
                f"📋 <b>БУФЕР ОБМЕНА</b>\n\n"
                f"<b>Содержимое:</b>\n<code>{clipboard_content[:4000]}</code>\n\n"
                "📝 <b>Отправь текст</b> для записи.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "📋 <b>Буфер пуст</b>\n\n"
                "📝 <b>Отправь текст</b> для записи.",
                parse_mode="HTML"
            )
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка:</b> <code>{e}</code>", parse_mode="HTML")


# --- ЗАГРУЗКА ФАЙЛОВ (ПЕРВЫЙ ОБРАБОТЧИК!) ---
@dp.message(F.audio | F.document | F.video | F.animation | F.voice | F.video_note)
async def download_file(message: types.Message):
    if not is_owner(message.from_user.id):
        return

    file_obj = message.document or message.video or message.audio or message.voice or message.animation or message.video_note

    if not file_obj:
        return

    if file_obj.file_size > 20 * 1024 * 1024:
        await message.answer("❌ <b>Файл > 20 МБ!</b>", parse_mode="HTML")
        return

    file_name = getattr(file_obj, "file_name", f"file_{int(time.time())}")
    safe_file_name = "".join(c for c in str(file_name) if c.isalnum() or c in "._- ").strip()
    safe_file_name = f"{int(time.time())}_{safe_file_name}"
    path = os.path.join(DOWNLOAD_DIR, safe_file_name)

    wait_msg = await message.answer("📥 <b>Загрузка...</b>", parse_mode="HTML")

    try:
        file_info = await bot.get_file(file_obj.file_id)
        await bot.download_file(file_info.file_path, path)

        size = os.path.getsize(path)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"

        await wait_msg.delete()
        await message.answer(
            f"✅ <b>Сохранён!</b>\n\n"
            f"📄 <b>Имя:</b> <code>{safe_file_name}</code>\n"
            f"📊 <b>Размер:</b> <code>{size_str}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"❌ <b>Ошибка:</b> <code>{e}</code>", parse_mode="HTML")


# --- ОБРАБОТКА ТЕКСТА (ВТОРОЙ!) ---
@dp.message(F.text)
async def text_for_input(message: types.Message):
    if not is_owner(message.from_user.id):
        return

    # Проверяем, не команда ли это
    commands = ["📸 Скриншот", "📹 Фото", "🎤 Звук", "💻 Инфо",
                "📊 Мониторинг", "🔊 Громкость", "📁 Файлы", "⌨️ Ввод", "🖱️ Мышь",
                "🪟 Окна", "⚙️ Система", "📋 Буфер", "❓ Помощь", "🔄 Обновить", "🗑️ УДАЛИТЬ БОТА"]

    if message.text in commands:
        return

    try:
        pyperclip.copy(message.text)
        pyautogui.hotkey("ctrl", "v")
        await message.answer(f"✅ <b>Введено!</b>\n<code>{message.text[:50]}</code>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка:</b> <code>{e}</code>", parse_mode="HTML")


# --- CALLBACK ---
@dp.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery):
    await callback.message.edit_text("👋 <b>BotForPC</b>\n\n👇 <b>Меню:</b>", reply_markup=get_main_kb(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "menu:refresh")
async def menu_refresh(callback: CallbackQuery):
    await callback.message.edit_text("🔄 <b>Обновлено!</b>", reply_markup=get_main_kb(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "info:refresh")
async def info_refresh(callback: CallbackQuery):
    await callback.message.edit_text(get_system_info(), reply_markup=get_info_kb(), parse_mode="HTML")
    await callback.answer("🔄 Обновлено!")


@dp.callback_query(F.data == "monitoring:refresh")
async def monitoring_refresh(callback: CallbackQuery):
    await callback.message.edit_text(get_monitoring_info(), reply_markup=get_monitoring_kb(), parse_mode="HTML")
    await callback.answer("🔄 Обновлено!")


@dp.callback_query(F.data.startswith("filepage:"))
async def change_file_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    await callback.message.edit_text(f"📁 <b>ПРОВОДНИК</b>\n<code>{DOWNLOAD_DIR}</code>", reply_markup=get_files_kb(page), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("filedir:"))
async def file_dir(callback: CallbackQuery):
    dir_name = callback.data.split(":", 1)[1]
    current_path = callback.message.text.split("<code>")[1].split("</code>")[0] if "<code>" in callback.message.text else DOWNLOAD_DIR
    
    if dir_name == "..":
        new_path = os.path.dirname(current_path)
    else:
        new_path = os.path.join(current_path, dir_name)
    
    try:
        await callback.message.edit_text(f"📁 <b>ПРОВОДНИК</b>\n<code>{new_path}</code>", reply_markup=get_files_kb(0, new_path), parse_mode="HTML")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
    await callback.answer()


@dp.callback_query(F.data.startswith("fileaction:"))
async def file_action(callback: CallbackQuery):
    file_name = callback.data.split(":", 1)[1]
    await callback.message.edit_text(
        f"📄 <b>Файл:</b> <code>{file_name}</code>\n\n👇 <b>Выберите:</b>",
        reply_markup=get_file_action_kb(file_name),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("fileopen:"))
async def file_open(callback: CallbackQuery):
    file_name = callback.data.split(":", 1)[1]
    file_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, file_name))
    
    if os.path.exists(file_path):
        try:
            os.startfile(file_path)
            await callback.answer(f"🚀 {file_name}", show_alert=True)
        except Exception as e:
            await callback.answer(f"❌ {e}", show_alert=True)
    else:
        await callback.answer("❌ Не найден!", show_alert=True)


@dp.callback_query(F.data.startswith("filesend:"))
async def file_send(callback: CallbackQuery):
    file_name = callback.data.split(":", 1)[1]
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    
    if os.path.exists(file_path):
        try:
            await callback.message.answer_document(types.FSInputFile(file_path), caption=f"📄 {file_name}")
            await callback.answer("📤 Отправка...")
        except Exception as e:
            await callback.answer(f"❌ {e}", show_alert=True)
    else:
        await callback.answer("❌ Не найден!", show_alert=True)


@dp.callback_query(F.data.startswith("filedelete:"))
async def file_delete(callback: CallbackQuery):
    file_name = callback.data.split(":", 1)[1]
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    
    if os.path.exists(file_path):
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            else:
                shutil.rmtree(file_path)
            await callback.message.edit_text(f"🗑️ <b>Удалено:</b> <code>{file_name}</code>", parse_mode="HTML")
            await callback.answer("✅ Готово!")
        except Exception as e:
            await callback.answer(f"❌ {e}", show_alert=True)
    else:
        await callback.answer("❌ Не найден!", show_alert=True)


@dp.callback_query(F.data.startswith("filecopy:"))
async def file_copy(callback: CallbackQuery):
    file_name = callback.data.split(":", 1)[1]
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    
    if os.path.exists(file_path):
        try:
            pyperclip.copy(file_path)
            await callback.answer(f"📋 {file_name}", show_alert=True)
        except Exception as e:
            await callback.answer(f"❌ {e}", show_alert=True)
    else:
        await callback.answer("❌ Не найден!", show_alert=True)


@dp.callback_query(F.data.startswith("vol:"))
async def volume_control(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        if devices is None:
            await callback.answer("❌ Не найдено!", show_alert=True)
            return
        
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        if action == "mute":
            current = volume.GetMute()
            volume.SetMute(not current, None)
            status = "🔇 Выкл" if not current else "🔊 Вкл"
            await callback.answer(status, show_alert=True)
        elif action == "100":
            volume.SetMasterVolumeLevelScalar(1.0, None)
            await callback.answer("🔊 100%", show_alert=True)
        elif action == "-10":
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(max(0, current - 0.1), None)
            await callback.answer(f"🔉 {int((current - 0.1) * 100)}%", show_alert=True)
        elif action == "+10":
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(min(1, current + 0.1), None)
            await callback.answer(f"🔈 {int((current + 0.1) * 100)}%", show_alert=True)
        
        await callback.message.edit_text("🔊 <b>Готово!</b>", parse_mode="HTML")
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@dp.callback_query(F.data.startswith("mouse:"))
async def mouse_control(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    
    try:
        if action == "up":
            pyautogui.move(0, -50)
        elif action == "down":
            pyautogui.move(0, 50)
        elif action == "left":
            pyautogui.move(-50, 0)
        elif action == "right":
            pyautogui.move(50, 0)
        elif action == "click":
            pyautogui.click()
        elif action == "rclick":
            pyautogui.rightClick()
        elif action == "dblclick":
            pyautogui.doubleClick()
        
        await callback.answer(f"✅ {action}", show_alert=False)
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@dp.callback_query(F.data.startswith("win:"))
async def windows_control(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    
    try:
        if action == "minimize":
            pyautogui.hotkey("win", "d")
        elif action == "desktop":
            pyautogui.hotkey("win", "d")
        elif action == "alttab":
            pyautogui.hotkey("alt", "tab")
        elif action == "close":
            pyautogui.hotkey("alt", "f4")
        
        await callback.answer(f"✅ {action}", show_alert=False)
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@dp.callback_query(F.data.startswith("sys:"))
async def system_control(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    
    try:
        if action == "shutdown":
            await callback.answer("⏳ Выключение...", show_alert=True)
            subprocess.Popen(["shutdown", "/s", "/t", "5"], creationflags=subprocess.CREATE_NO_WINDOW)
        elif action == "restart":
            await callback.answer("⏳ Перезагрузка...", show_alert=True)
            subprocess.Popen(["shutdown", "/r", "/t", "5"], creationflags=subprocess.CREATE_NO_WINDOW)
        elif action == "sleep":
            await callback.answer("⏳ Сон...", show_alert=True)
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif action == "lock":
            await callback.answer("🔒 Блокировка...", show_alert=True)
            os.system("rundll32.exe user32.dll,LockWorkStation")
        elif action == "processes":
            processes = len(psutil.pids())
            await callback.answer(f"📊 Процессы: {processes}", show_alert=True)
        
        await callback.message.edit_text(f"✅ <b>Выполнено:</b> {action}", parse_mode="HTML")
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@dp.callback_query(F.data.startswith("delete:"))
async def delete_bot(callback: CallbackQuery):
    action = callback.data.split(":")[1]

    if action == "cancel":
        await callback.message.edit_text("❌ <b>Отменено</b>", parse_mode="HTML")
        await callback.answer()
    elif action == "confirm":
        await callback.message.edit_text("⏳ <b>Удаление...</b>", parse_mode="HTML")
        await callback.answer()

        try:
            remove_from_autostart()

            if os.path.exists(DOWNLOAD_DIR):
                shutil.rmtree(DOWNLOAD_DIR)

            marker_file = os.path.join(BASE_DIR, ".autostart_added")
            if os.path.exists(marker_file):
                os.remove(marker_file)

            await callback.message.answer("✅ <b>Бот удалён!</b>", parse_mode="HTML")

            await asyncio.sleep(2)
            os._exit(0)
        except Exception as e:
            await callback.message.answer(f"❌ <b>Ошибка:</b> <code>{e}</code>", parse_mode="HTML")


@dp.callback_query(F.data.startswith("clean:"))
async def clean_bot(callback: CallbackQuery):
    """Обработчик команды /clean."""
    action = callback.data.split(":")[1]

    if action == "cancel":
        await callback.message.edit_text("❌ <b>Отменено</b>", parse_mode="HTML")
        await callback.answer()
    elif action == "confirm":
        await callback.message.edit_text("⏳ <b>Очистка...</b>", parse_mode="HTML")
        await callback.answer()

        try:
            # Удаляем из автозагрузки
            remove_from_autostart()

            # Удаляем папку downloads
            if os.path.exists(DOWNLOAD_DIR):
                shutil.rmtree(DOWNLOAD_DIR)

            # Удаляем маркер
            marker_file = os.path.join(BASE_DIR, ".autostart_added")
            if os.path.exists(marker_file):
                os.remove(marker_file)

            # Удаляем временные файлы
            temp_screen = os.path.join(tempfile.gettempdir(), "temp_screen.png")
            temp_cam = os.path.join(tempfile.gettempdir(), "temp_cam.jpg")
            temp_audio = os.path.join(tempfile.gettempdir(), "audio_")

            if os.path.exists(temp_screen):
                os.remove(temp_screen)
            if os.path.exists(temp_cam):
                os.remove(temp_cam)

            # Удаляем файлы audio_*
            for f in os.listdir(tempfile.gettempdir()):
                if f.startswith("audio_"):
                    os.remove(os.path.join(tempfile.gettempdir(), f))

            await callback.message.answer(
                "✅ <b>Бот полностью удалён!</b>\n\n"
                "🗑️ Удалено:\n"
                "├ Автозагрузка\n"
                "├ Папка downloads\n"
                "├ Временные файлы\n"
                "└ Маркер автозапуска\n\n"
                "Бот будет остановлен через 2 секунды.",
                parse_mode="HTML"
            )

            await asyncio.sleep(2)
            os._exit(0)
        except Exception as e:
            await callback.message.answer(f"❌ <b>Ошибка:</b> <code>{e}</code>", parse_mode="HTML")


async def main():
    print("=" * 50)
    print(f"🤖 {BOT_NAME} запущен!")
    print("=" * 50)
    print(f"👤 ID: {MY_ID}")
    print(f"📁 Downloads: {DOWNLOAD_DIR}")
    print("=" * 50)
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
