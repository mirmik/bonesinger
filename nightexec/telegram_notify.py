import telegram
import telegram.ext
import logging
import os


def telegram_notify(token, chat_id, text):
    bot = telegram.Bot(token=token)
    bot.send_message(chat_id=chat_id, text=text)
