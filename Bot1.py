import os
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = os.getenv("8433194557:AAFeYUpVejptWUTvFIp5Ir_T4JWgjMJ5NNU")

async def start(update, context):
    await update.message.reply_text("Hello! Your bot is working.")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

if __name__ == "__main__":
    app.run_polling()
  
  
