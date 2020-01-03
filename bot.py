# pip install python-telegram-bot
import telegram.bot
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, ConversationHandler, CallbackQueryHandler)
from telegram.ext.dispatcher import run_async
import logging
from functools import wraps
import random
import time
from params import bottoken, port
import json
from datetime import datetime

# pip install pyopenssl
from requests import get
ip = get('https://api.ipify.org').text
try:
    certfile = open("cert.pem")
    keyfile = open("private.key")
    certfile.close()
    keyfile.close()
except IOError:
    from OpenSSL import crypto
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    cert = crypto.X509()
    cert.get_subject().CN = ip
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')
    with open("cert.pem", "wt") as certfile:
        certfile.write(crypto.dump_certificate(
            crypto.FILETYPE_PEM, cert).decode('ascii'))
    with open("private.key", "wt") as keyfile:
        keyfile.write(crypto.dump_privatekey(
            crypto.FILETYPE_PEM, key).decode('ascii'))

logging.basicConfig(filename='debug.log', filemode='a+', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)


def loader():
    global users
    try:
        with open('users.json') as userfile:
            users = json.load(userfile)
    except:
        with open('users.json', 'w+') as userfile:
            users = {}
    global groups
    try:
        with open('groups.json') as groupfile:
            groups = json.load(groupfile)
    except:
        with open('groups.json', 'w+') as groupfile:
            groups = {}


def start(update, context):
    user_id = str(update.message.chat_id)
    if user_id.startswith('-'):
        message = context.bot.send_message(
            chat_id=user_id, text='*Added to group successfully*', parse_mode=telegram.ParseMode.MARKDOWN)
        global groups
        groups[user_id] = str(message.message_id)
        with open('groups.json', 'w') as groupfile:
            json.dump(groups, groupfile)
    else:
        first_name = update.message.from_user.first_name
        last_name = update.message.from_user.last_name
        full_name = (str(first_name or '') + ' ' +
                     str(last_name or '')).strip()
        context.bot.send_message(
            chat_id=user_id, text='Hi *{}*! You may leave at any time using /leave.'.format(full_name), parse_mode=telegram.ParseMode.MARKDOWN)
        global users
        users[user_id] = {'name': full_name, 'prayer': ''}
        with open('users.json', 'w') as userfile:
            json.dump(users, userfile)


def leave(update, context):
    user_id = str(update.effective_user.id)
    global users
    del users[user_id]
    with open('users.json', 'w') as userfile:
        json.dump(users, userfile)
    context.bot.send_message(
        chat_id=user_id, text='*Goodbye!*', parse_mode=telegram.ParseMode.MARKDOWN)


def new(update, context):
    global groups
    for group in groups:
        message = context.bot.send_message(
            chat_id=int(group), text='*Prayer List*', parse_mode=telegram.ParseMode.MARKDOWN)
        groups[group] = str(message.message_id)
        with open('groups.json', 'w') as groupfile:
            json.dump(groups, groupfile)
    compose = '*Send me your thanksgiving / prayer requests.*\n\n(You can update it at any time by sending another message)'
    global users
    for user_id in users:
        users[user_id]['prayer'] = ''
        sendnew(context, user_id, compose)
    with open('users.json', 'w') as userfile:
        json.dump(users, userfile)


@run_async
def sendnew(context, user_id, compose):
    context.bot.send_message(
        chat_id=int(user_id), text=compose, parse_mode=telegram.ParseMode.MARKDOWN)


def shuffle(update, context):
    randomlist = []
    for value in users.values():
        randomlist.append(value['name'])
    if len(randomlist) < 2:
        update.message.reply_text(
            '_Too few people!_', parse_mode=telegram.ParseMode.MARKDOWN)
        return
    random.shuffle(randomlist)
    compose = '*Prayer Partners*\n\n'
    i = 0
    while i < len(randomlist) - 1:
        compose += '*{}*'.format(randomlist[i])
        compose += ' & '
        compose += '*{}*'.format(randomlist[i+1])
        if i + 2 == len(randomlist):
            break
        elif i + 3 == len(randomlist):
            compose += ' & '
            compose += '*{}*'.format(randomlist[i+2])
            break
        else:
            compose += '\n'
        i += 2
    for group in groups:
        context.bot.send_message(
            chat_id=int(group), text=compose, parse_mode=telegram.ParseMode.MARKDOWN)


def prayer(update, context):
    user_id = str(update.message.chat_id)
    if user_id.startswith('-'):
        return
    users[user_id]['prayer'] = update.message.text
    with open('users.json', 'w') as userfile:
        json.dump(users, userfile)
    groupedit(context)
    update.message.reply_text(
        '_Saved._', parse_mode=telegram.ParseMode.MARKDOWN)


def groupedit(context):
    compose = '*Prayer List*\n\n'
    for value in users.values():
        name = value['name']
        prayer = value['prayer']
        compose += '*{}*:\n'.format(name)
        compose += prayer
        compose += '\n\n'
    compose = compose.strip()
    for key, value in groups.items():
        context.bot.edit_message_text(
            chat_id=int(key),
            message_id=int(value),
            text=compose,
            parse_mode=telegram.ParseMode.MARKDOWN
        )


def main():
    updater = Updater(token=bottoken, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("leave", leave))
    dp.add_handler(CommandHandler("new", new))
    dp.add_handler(CommandHandler("shuffle", shuffle))
    dp.add_handler(MessageHandler(Filters.text, prayer))

    loader()

    updater.start_polling()
    updater.start_webhook(listen='0.0.0.0',
                          port=port,
                          url_path=bottoken,
                          key='private.key',
                          cert='cert.pem',
                          webhook_url='https://{}:{}/{}'.format(ip, port, bottoken))

    print("Bot is running. Press Ctrl+C to stop.")
    print("Please wait for confirmation before closing.")
    updater.idle()
    print("Bot stopped successfully.")


if __name__ == '__main__':
    main()
