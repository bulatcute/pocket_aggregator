#region Imports
from telegram.ext import Updater, CommandHandler
from bs4 import BeautifulSoup
from pony.orm import *
import feedparser
import urllib.request
import telegram
import requests
#endregion

#region Database Setup
db = Database('sqlite', 'bot.sqlite', create_db=True)

class User(db.Entity):
    user_id = Required(int)
    sites = Set('Feed')

class Feed(db.Entity):
    url = Required(str)
    users = Set(User)

@db_session
def add_feed_user(feed, user):
    feed.users.add(user)

@db_session
def add_user(id):
    return User(user_id=id)

@db_session
def add_feed(aurl):
    return Feed(url=aurl)

db.generate_mapping(create_tables=True)
#endregion

#region Util functions

def get_rss_feed(website_url):
    source_code = requests.get(website_url)
    plain_text = source_code.text
    soup = BeautifulSoup(plain_text)
    for link in soup.find_all("link", {"type" : "application/rss+xml"}):
        href = link.get('href')
        return href
#endregion

#region Start
def start(update, context):
    tg_user = update.message.from_user

    with db_session:
        if not tg_user.id in select(u.user_id for u in User)[:]:
            u1 = add_user(tg_user.id)

    context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я — бот-новостной агрегатор, разработанный на смене IT Jump Pro\
\nНапиши мне /help и я скажу тебе как мной пользоваться")
#endregion

#region Help
def help(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Напиши мне /read {ссылка на новостной ресурс} и я \
покажу тебе последние статьи этого сайта.\
\nНапример: /read https://dtf.ru')
#endregion

#region Read
def read(update, context):
    arg_url = context.args[0]
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Ищу RSS ленту на {arg_url}...')

    feed_url = get_rss_feed(arg_url)
    if feed_url == 'no link':
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Извините, я не нашёл RSS ленту на этом'
                                                                        f' сайте. Попробуйте ввести другую ссылку')
        return

    if feed_url.startswith('/'):
        feed_url = arg_url + feed_url

    context.bot.send_message(chat_id=update.effective_chat.id, text='Осталось совсем чуть-чуть...')

    feed = feedparser.parse(feed_url)
    feed_title = feed['feed']['title']
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'*{feed_title.upper()}*', parse_mode='markdown')

    feed_entries = feed.entries
    for entry in feed.entries:
        article_title = entry.title
        article_link = entry.link
        article_published_at = entry.published

        msg = f'''{article_title}
----------------------------
published at {article_published_at}
----------------------------
{article_link}'''
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
#endregion

#region Add
def add(update, context):
    arg_url = context.args[0]
    tg_user = update.message.from_user

    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Ищу RSS ленту на {arg_url}...')

    feed_url = get_rss_feed(arg_url)
    if feed_url == 'no link':
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Извините, я не нашёл RSS ленту на этом'
                                                                        f' сайте. Попробуйте ввести другую ссылку')
        return

    if feed_url.startswith('/'):
        feed_url = arg_url + feed_url

    # context.bot.send_message(chat_id=update.effective_chat.id, text=feed_url)

    with db_session:
        if not feed_url in select(f.url for f in Feed)[:]:
            f1 = add_feed(feed_url)

    with db_session:    
        for u1 in select(u for u in User if u.user_id == tg_user.id)[:]:
            u = u1
        for f1 in select(f for f in Feed if f.url == feed_url)[:]:
            f = f1
        if not f in u.sites:
            add_feed_user(f, u)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Теперь вы подписаны на {feed_url}')
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Этот сайт уже есть среди ваших подписок')
#endregion

#region Refresh Function
def refresh_function(context: telegram.ext.CallbackContext):
    for site in select(feed.site for feed in Feed):
        pass
#endregion

#region Telegram Setup
telegram_token = '1025022667:AAGy4d57cRfbZAOXsNM5W2rvRPYKegyttgM'
updater = Updater(telegram_token, use_context=True)
j_queue = updater.job_queue
dispather = updater.dispatcher

dispather.add_handler(CommandHandler("start", start))
dispather.add_handler(CommandHandler("help", help))
dispather.add_handler(CommandHandler("read", read))
dispather.add_handler(CommandHandler("add", add))

updater.start_polling()
#endregion