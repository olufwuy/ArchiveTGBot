import os
import zipfile
import tarfile
import tempfile
import shutil
import mimetypes

import rarfile  # pip install rarfile
import py7zr    # pip install py7zr

from telegram import Update, Document
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

SUPPORTED_EXTENSIONS = ['.zip', '.rar', '.7z', '.tar', '.tar.gz', '.tgz']

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне архив (.zip, .rar, .7z, .tar.gz и т.д.), я его распакую и пришлю файлы обратно.")

# Главный обработчик документов
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document: Document = update.message.document
    filename = document.file_name.lower()

    # Проверка расширения
    if not any(filename.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        await update.message.reply_text("Этот формат архива не поддерживается. Поддержка: zip, rar, 7z, tar, tar.gz.")
        return

    # Загрузка архива
    file = await document.get_file()
    file_path = tempfile.mktemp(suffix=os.path.splitext(filename)[1])
    await file.download_to_drive(file_path)

    extract_dir = tempfile.mkdtemp()
    try:
        # Распаковка архива
        if filename.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as archive:
                archive.extractall(extract_dir)

        elif filename.endswith('.rar'):
            with rarfile.RarFile(file_path) as archive:
                archive.extractall(extract_dir)

        elif filename.endswith('.7z'):
            with py7zr.SevenZipFile(file_path, mode='r') as archive:
                archive.extractall(path=extract_dir)

        elif filename.endswith(('.tar.gz', '.tgz', '.tar')):
            with tarfile.open(file_path, 'r:*') as archive:
                archive.extractall(path=extract_dir)

        else:
            await update.message.reply_text("Не удалось определить формат архива.")
            return

        # Отправка файлов пользователю
        sent = 0
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, extract_dir)

                # Проверка размера (Telegram ограничивает до ~20 МБ для обычных аккаунтов)
                if os.path.getsize(full_path) > 19 * 1024 * 1024:
                    await update.message.reply_text(f"❗ Файл `{rel_path}` слишком большой (>19MB), не могу отправить.", parse_mode='Markdown')
                    continue

                # Отправка файла
                await update.message.reply_document(document=open(full_path, 'rb'), filename=rel_path)
                sent += 1

        if sent == 0:
            await update.message.reply_text("Файлы извлечены, но ни один не удалось отправить (возможно, они слишком большие или пустой архив).")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Произошла ошибка при распаковке: {e}")
    finally:
        # Удаление временных файлов
        try:
            os.remove(file_path)
            shutil.rmtree(extract_dir)
        except:
            pass

# Создание и запуск бота
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

print("Бот запущен.")
app.run_polling()