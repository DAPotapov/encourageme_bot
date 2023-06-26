"""
Bot sends motivational messages in interval set by user

Note:
Based on timerbot.py https://docs.python-telegram-bot.org/en/stable/examples.timerbot.html
"""

import logging
import os
import re
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from random import choice
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)
logger = logging.getLogger(__name__)

# Set list of commands
help_cmd = BotCommand("help","о боте")
set_cmd = BotCommand("set", "<интервал> - установка таймера сообщений от бота")
unset_cmd = BotCommand("unset", "отключить уведомления")
stop_cmd = BotCommand("stop", "прекращение работы бота")

# Define a few command handlers. These usually take the two arguments update and
# context.
# Best practice would be to replace context with an underscore,
# since context is an unused local variable.
# This being an example and not having context present confusing beginners,
# we decided to have it present as context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    await update.message.reply_text(f"Привет, {update.effective_user.first_name}! Чтобы бот заработал напиши:\n"
                                    f"/set <интервал уведомлений>.\n"
                                    f"или просто укажи этот интервал."
                                    f"Например: 13 сек, 6 мин., 3 ч., 1 д."
                                    )


async def alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    job = context.job

    # choose line randomly
    if 'phrases' in job.data.keys():
        bot_msg = choice(job.data['phrases'])
    else:
        bot_msg = "Ты - молодец!"

    # Add user name to message
    if 'first_name' in job.data.keys():
        bot_msg = job.data['first_name'] + '! ' + bot_msg

    await context.bot.send_message(job.chat_id, text=bot_msg)


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler of /set command"""
    chat_id = update.effective_user.id
    try:
        bot_msg = set_job(str(chat_id), str(context.args), context) 
        await update.effective_message.reply_text(bot_msg)
    except (IndexError, ValueError):
        await update.effective_message.reply_text("Использование: /set <интервал уведомлений>.\n"
                                                  "Например: 13 сек, 6 мин., 3 ч., 1 д.")


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Handler for text input from user"""
    text = update.message.text
    chat_id = update.effective_user.id
    bot_msg = set_job(str(chat_id), text, context)
    if bot_msg:        
        await update.message.reply_text(bot_msg)
    else:
        logger.info(f'{tm.asctime()}\t{user.id} ({user.username}) wrote: {text}')


def set_job(chat_id: str, text: str, context: ContextTypes.DEFAULT_TYPE):
    ''' Recognize interval and set job accordingly'''
    interval, due = None, None
    suffix = None
    nonvalid = (f"Не, это понятно, но какой интервал времени задать?"
                "Например: 13 сек, 6 мин., 3 ч., 1 д.")
    
    # Recognize seconds
    p = re.compile(r'\d+ ?[сs]', re.IGNORECASE)
    found = re.search(p, text)
    if found:
        p = re.compile(r'\d+', re.IGNORECASE)
        interval = re.search(p, found[0])
        if interval:            
            due = int(interval[0])
            suffix = 'секунд'
        else:
            return nonvalid
    else:    
        # Recognize minutes
        p = re.compile(r'\d+ ?[мm]', re.IGNORECASE)
        found = re.search(p, text)
        if found:
            p = re.compile(r'\d+', re.IGNORECASE)
            interval = re.search(p, found[0])
            if interval:            
                due = int(interval[0]) * 60
                suffix = 'минут'
            else:
                return nonvalid
        else:    
            # Recognize hours
            p = re.compile(r'\d+ ?[чh]', re.IGNORECASE)
            found = re.search(p, text)
            if found:
                p = re.compile(r'\d+', re.IGNORECASE)
                interval = re.search(p, found[0])
                if interval:            
                    due = int(interval[0]) * 60 * 60
                    suffix = 'часов'
                else:
                    return nonvalid
            else:
                # Recognize days 
                p = re.compile(r'\d+ ?[дd]', re.IGNORECASE)
                found = re.search(p, text)
                if found:
                    p = re.compile(r'\d+', re.IGNORECASE)
                    interval = re.search(p, found[0])
                    if interval:            
                        due = int(interval[0]) * 60 * 60 * 24
                        suffix = 'дней'
                    else:
                        return nonvalid
                else:
                    return nonvalid
    
    # If there is interval specified then schedule a job and inform user
    if due:
        job_removed = remove_job_if_exists(str(chat_id), context)
        job = context.job_queue.run_repeating(alarm, due, chat_id=chat_id, name=str(chat_id), data=context.user_data)

        # Load phrases from file
        phrases = load_txt()

        if phrases:
            context.user_data['phrases'] = phrases 

        bot_msg = f"Таймер успешно установлен на {int(interval[0])} {suffix}!"
        if job_removed:
            bot_msg += " Предыдущий таймер удалён."

        # Run it immediately
        # await job.run(context.application)
        return bot_msg
    else:
        return nonvalid


async def unset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Таймер успешно отключен!" if job_removed else "Таймер не был установлен."
    await update.message.reply_text(text)


def load_txt():
    """
    Helper function to load text file with phrases
    """
    phrases = []
    filename = 'files/phrases.txt'
    # connect to file with phrases
    with open(filename, 'r') as file:
        for l in file:
            phrases.append(l)
    return phrases


# Function to control list of commands in bot itself. Commands itself are global
async def post_init(application: Application):
    await application.bot.set_my_commands([
                                        help_cmd,
                                        set_cmd,
                                        unset_cmd,
                                        stop_cmd
                                        ])


def main() -> None:
    """Run bot."""

    load_dotenv()
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("set", set_timer))
    application.add_handler(CommandHandler("unset", unset))
    application.add_handler(MessageHandler(filters.Regex(re.compile(r'стоп|останов|отмен'
                                                                    '|переста|хорош|довольно'
                                                                    '|хватит|stop|sta*hp',
                                                                    re.IGNORECASE)), unset))
    application.add_handler(CommandHandler("stop", unset))
    application.add_handler(MessageHandler(filters.TEXT, text))
    

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
