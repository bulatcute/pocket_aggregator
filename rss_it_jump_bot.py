#region Imports
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
from bs4 import BeautifulSoup
from pony.orm import *
import feedparser
import urllib.request
import telegram
import requests
import time
import os
import dotenv
#endregion

#region Database Setup
db = Database('sqlite', 'bot.sqlite', create_db=True)

class User(db.Entity):
    user_id = Required(int)
    sites = Set('Feed')

class Feed(db.Entity):
    url = Required(str)
    modified = Required(int)
    users = Set(User)

@db_session
def add_feed_user(feed, user):
    feed.users.add(user)

@db_session
def remove_feed_user(feed, user):
    feed.users.remove(user)

@db_session
def add_user(id):
    return User(user_id=id)

@db_session
def add_feed(aurl, modif):
    return Feed(url=aurl, modified=modif)

@db_session
def change_modified(feed, modif):
    feed.modified = modif

db.generate_mapping(create_tables=True)
#endregion

#region Util functions

def get_rss_feed(website_url):
    try:
        source_code = requests.get(website_url)
        plain_text = source_code.text
        soup = BeautifulSoup(plain_text)
        for link in soup.find_all("link", {"type" : "application/rss+xml"}):
            href = link.get('href')        
            print(href)
            return href
    except:
        return ''

def convert(url):
    if url.startswith('http://www.'):
        return 'http://' + url[len('http://www.'):]
    elif url.startswith('https://www.'):
        return 'http://' + url[len('https://www.'):]
    if url.startswith('www.'):
        return 'http://' + url[len('www.'):]
    if not url.startswith('http'):
        return 'http://' + url
    print(url)
    return url
#endregion

#region Start
def start(update, context):
    tg_user = update.message.from_user

    with db_session:
        if not tg_user.id in select(u.user_id for u in User)[:]:
            u1 = add_user(tg_user.id)

    context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я — бот-новостной агрегатор PocketAgregator\
\nНапиши мне /help и я скажу тебе как мной пользоваться")
#endregion

#region Help
def help(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='''
Напиши мне /add {ссылка на сайт} и я буду отправлять тебе новые статьи оттуда
Напиши мне /list и я покажу тебе список подписок
Напиши мне /remove {ссылка на сайт} и я удалю этот сайт из твоих подписок''')
#endregion

#region Add
def add(update, context):
    arg_url = convert(context.args[0])
    tg_user = update.message.from_user

    msg_id = context.bot.send_message(chat_id=update.effective_chat.id, text=f'Ищу RSS ленту на {arg_url}...').message_id

    feed_url = get_rss_feed(arg_url)

    if not feed_url:
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        context.bot.send_message(chat_id=update.effective_chat.id, text='По вашему запросу ничего не найдено.')
        return

    if feed_url.startswith('/'):
        feed_url = arg_url + feed_url
        print(feed_url)

    feed = feedparser.parse(feed_url)
    last_post = int(max([time.mktime(e.published_parsed) for e in feed.entries]))
    print(last_post)
    with db_session:
        if not feed_url in select(f.url for f in Feed)[:]:
            f1 = add_feed(feed_url, last_post)
    with db_session:    
        for u1 in select(u for u in User if u.user_id == tg_user.id)[:]:
            u = u1
        for f1 in select(f for f in Feed if f.url == feed_url)[:]:
            f = f1
        if not f in u.sites:
    
            add_feed_user(f, u)
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Теперь вы подписаны на {feed_url}\n'
                                                                            f'Пока можете оснакомиться с последними статьями этого сайта')
            entry = feed.entries[0]
            article_title = entry.title
            article_link = entry.link
            article_published_at = entry.published
            msg = f'''{article_title}
{article_link}'''
            context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        else:
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text='Этот сайт уже есть среди ваших подписок')
#endregion

#region Remove
def remove(update, context):
    arg_url = convert(context.args[0])
    tg_user = update.message.from_user

    msg_id = context.bot.send_message(chat_id=update.effective_chat.id, text=f'Ищу {arg_url} среди ваших подписок...').message_id

    feed_url = get_rss_feed(arg_url)

    if not feed_url:
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        context.bot.send_message(chat_id=update.effective_chat.id, text='По вашему запросу ничего не найдено.')
        return

    if feed_url.startswith('/'):
        feed_url = arg_url + feed_url

    with db_session:
        if not feed_url in select(f.url for f in Feed)[:]:
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Вы не подписаны на {feed_url}')

    with db_session:
        for u1 in select(u for u in User if u.user_id == tg_user.id)[:]:
            u = u1
        for f1 in select(f for f in Feed if f.url == feed_url)[:]:
            f = f1
        if not f in u.sites:
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Вы не подписаны на {feed_url}')
        else:
            remove_feed_user(f, u)
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'{feed_url} успешно удалён')
#endregion

#region list
def sub_list(update,context):
    tg_user = update.message.from_user
    msg = ''
    with db_session:
        for usr in select(u1 for u1 in User if u1.user_id == tg_user.id)[:]:
            for fd in select(f1.url for f1 in Feed if f1 in usr.sites)[:]:
                msg = msg + fd + '\n'
    if not msg:
        context.bot.send_message(chat_id=update.effective_chat.id, text='У вас нет подписок. Напишите /help, чтобы узнать, как подписаться на сайт')
        return
    context.bot.send_message(chat_id=update.effective_chat.id, text='Список подписок:\n' + msg)
            
#endregion

#region Refresh Function
def refresh_function(context: telegram.ext.CallbackContext):
    print('running refresh-function')
    with db_session:
        for feed_obj in select(feed for feed in Feed)[:]:
            feed = feedparser.parse(feed_obj.url)
            
            for entry in feed.entries:
                print(entry.published_parsed)
                print(time.mktime(entry.published_parsed))
                print(int((time.mktime(entry.published_parsed))))
                print(feed_obj.modified)
                if int(time.mktime(entry.published_parsed)) > feed_obj.modified:

                    article_title = entry.title
                    article_link = entry.link
                    article_published_at = entry.published

                    msg = f'''{article_title}
{article_link}'''
                    print(msg)
                    for user in feed_obj.users:
                        context.bot.send_message(chat_id=user.user_id, text=msg)
            change_modified(feed_obj, int(max([time.mktime(e.published_parsed) for e in feed.entries])))
        
#endregion

#region Unknown Command
def unknown_command(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Простите, я вас не понимаю. Напишите /help")
#endregion

#region Telegram Setup
dotenv.load_dotenv()
telegram_token = os.environ['TOKEN']
updater = Updater(telegram_token, use_context=True)
j_queue = updater.job_queue
dispather = updater.dispatcher

dispather.add_handler(CommandHandler("start", start))
dispather.add_handler(CommandHandler("help", help))
dispather.add_handler(CommandHandler("add", add))
dispather.add_handler(CommandHandler("remove", remove))
dispather.add_handler(CommandHandler("list", sub_list))
dispather.add_handler(MessageHandler(Filters.command, unknown_command))
dispather.add_handler(MessageHandler(Filters.text, unknown_command))

updater.start_polling()

j_queue.run_repeating(refresh_function, 900)
#endregion