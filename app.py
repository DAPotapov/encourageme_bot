#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to send timed Telegram messages.

This Bot uses the Application class to handle the bot and the JobQueue to send
timed messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Note:
Based on timerbot.py https://docs.python-telegram-bot.org/en/stable/examples.timerbot.html
"""

import logging
import os
import string
from datetime import datetime, date, time
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from random import choice
from pprint import pprint
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

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
    # TODO add username
    await update.message.reply_text("Привет! Чтобы бот заработал напиши: /set <интервал уведомлений>.\n Например: 10 сек, 5 мин., 2 ч., 1 д.")


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
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id
    try:
        # args[0] should contain the time for the timer
        due = float(context.args[0])
        if due < 0:
            await update.effective_message.reply_text("Sorry we can not go back to future!")
            return
        # will change this according to input
        interval = due

        job_removed = remove_job_if_exists(str(chat_id), context)
        job = context.job_queue.run_repeating(alarm, interval, chat_id=chat_id, name=str(chat_id), data=context.user_data)

        phrases = load_txt()

        if phrases:
            context.user_data['phrases'] = phrases 
        context.user_data['first_name'] = update.effective_user.first_name

        text = "Timer successfully set!"
        if job_removed:
            text += " Old one was removed."
        await update.effective_message.reply_text(text)
        # Run it immediately
        await job.run(context.application)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Usage: /set <minutes>")


async def unset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Timer successfully cancelled!" if job_removed else "You have no active timer."
    await update.message.reply_text(text)


def load_txt():
    """
    Helper function to load text file with phrases
    """
    phrases = []
    filename = 'data/phrases.txt'
    # connect to file with phrases
    with open(filename, 'r') as file:
        for l in file:
            phrases.append(l)
    return phrases

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    TODO should delete all jobs for user
    """


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
    application.add_handler(CommandHandler("stop", stop))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
