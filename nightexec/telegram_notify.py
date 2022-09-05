#!/usr/bin/env python3

import telegram
import telegram.ext
import logging
import os


def telegram_notify(token, chat_id, text):
    try:
        with open(token, "r") as f:
            token = f.read()
    except Exception as e:
        pass

    try:
        with open(chat_id, "r") as f:
            chat_id = f.read()
    except Exception as e:
        pass

    bot = telegram.Bot(token=token)
    bot.send_message(chat_id=chat_id, text=text)
