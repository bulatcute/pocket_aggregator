# region Imports
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, ConversationHandler
from bs4 import BeautifulSoup
from pony.orm import *
from telegram import ReplyKeyboardMarkup
import telegram
import feedparser
import requests
import time
import os
import dotenv

# endregion

# region Variables
ADD_COMMAND = 0
REMOVE_COMMAND = 1
CHOOSING = 2

choosing_kb = [['Подписаться на сайт'], ['Отписаться'], ['Мои подписки']]
choosing_markup = ReplyKeyboardMarkup(choosing_kb, one_time_keyboard=True, resize_keyboard=True)
# endregion

# region Database Setup
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


# endregion

# region Util functions

def get_rss_feed(website_url):
    try:
        source_code = requests.get(website_url)
        plain_text = source_code.text
        soup = BeautifulSoup(plain_text)
        for link in soup.find_all("link", {"type": "application/rss+xml"}):
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


# endregion

# region Start
def start(update, context):
    tg_user = update.message.from_user

    with db_session:
        if tg_user.id not in select(u.user_id for u in User)[:]:
            u1 = add_user(tg_user.id)

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Привет! Я — бот-новостной агрегатор Pocket Aggregator. Нажми на кнопку 'Подписаться "
                                  "на сайт', а затем введи ссылку. Например theverge.com",
                             reply_markup=choosing_markup)
    return CHOOSING


# endregion

# region Add Text
def add_text(update, context):
    print('running add_text')
    arg_url = convert(update.message.text)
    print(arg_url)
    tg_user = update.message.from_user

    msg_id = context.bot.send_message(chat_id=update.effective_chat.id,
                                      text=f'Ищу RSS ленту на {arg_url}...').message_id

    feed_url = get_rss_feed(arg_url)

    if not feed_url:
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        context.bot.send_message(chat_id=update.effective_chat.id, text='По вашему запросу ничего не найдено',
                                 reply_markup=choosing_markup)
        return CHOOSING

    if feed_url.startswith('/'):
        feed_url = arg_url + feed_url
        print(feed_url)

    feed = feedparser.parse(feed_url)
    last_post = int(max([time.mktime(e.published_parsed) for e in feed.entries]))
    print(last_post)
    with db_session:
        if feed_url not in select(f.url for f in Feed)[:]:
            f1 = add_feed(feed_url, last_post)
    with db_session:
        for u1 in select(u for u in User if u.user_id == tg_user.id)[:]:
            u = u1
        for f1 in select(f for f in Feed if f.url == feed_url)[:]:
            f = f1
        if f not in u.sites:

            add_feed_user(f, u)
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Теперь вы подписаны на {feed_url}\n'
                                                                            f'Пока можете оснакомиться с последними '
                                                                            f'статьями этого сайта')
            entry = feed.entries[0]
            article_title = entry.title
            article_link = entry.link
            article_published_at = entry.published
            msg = f'''{article_title}
{article_link}'''
            context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=choosing_markup)
        else:
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text='Этот сайт уже есть среди ваших подписок',
                                     reply_markup=choosing_markup)
    return CHOOSING


# endregion

# region Add Command
def add_command(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Введите адрес ссылки')
    return ADD_COMMAND


# endregion

# region Remove Text
def remove_text(update, context):
    feed_url = update.message.text
    tg_user = update.message.from_user

    if not feed_url:
        context.bot.send_message(chat_id=update.effective_chat.id, text='По вашему запросу ничего не найдено',
                                 reply_markup=choosing_markup)
        return CHOOSING

    with db_session:
        if feed_url not in select(f.url for f in Feed)[:]:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Вы не подписаны на {feed_url}')
            return CHOOSING

    with db_session:
        for u1 in select(u for u in User if u.user_id == tg_user.id)[:]:
            u = u1
        for f1 in select(f for f in Feed if f.url == feed_url)[:]:
            f = f1
        if f not in u.sites:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Вы не подписаны на {feed_url}')
            return CHOOSING
        else:
            remove_feed_user(f, u)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'{feed_url} успешно удалён',
                                     reply_markup=choosing_markup)
    return CHOOSING


# endregion

# region Remove Command
def remove_command(update, context):
    tg_user = update.message.from_user
    remove_kb = []
    with db_session:
        for usr in select(u1 for u1 in User if u1.user_id == tg_user.id)[:]:
            for fd in select(f1.url for f1 in Feed if f1 in usr.sites)[:]:
                remove_kb.append([fd])
    print(remove_kb)
    remove_markup = ReplyKeyboardMarkup(remove_kb, resize_keyboard=True, one_time_keyboard=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text='Выберите сайт', reply_markup=remove_markup)
    return REMOVE_COMMAND


# endregion

# region list
def sub_list(update, context):
    tg_user = update.message.from_user
    msg = ''
    with db_session:
        for usr in select(u1 for u1 in User if u1.user_id == tg_user.id)[:]:
            for fd in select(f1.url for f1 in Feed if f1 in usr.sites)[:]:
                msg = msg + fd + '\n'
    if not msg:
        context.bot.send_message(chat_id=update.effective_chat.id, text='У вас нет подписок.',
                                 reply_markup=choosing_markup)
        return CHOOSING
    context.bot.send_message(chat_id=update.effective_chat.id, text='Список подписок:\n' + msg,
                             reply_markup=choosing_markup)
    return CHOOSING


# endregion

# region Refresh Function
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

                    msg = f'''{article_title}
{article_link}'''
                    print(msg)
                    for user in feed_obj.users:
                        context.bot.send_message(chat_id=user.user_id, text=msg)
            change_modified(feed_obj, int(max([time.mktime(e.published_parsed) for e in feed.entries])))


# endregion

# region Unknown Command
def unknown_command(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Простите, я вас не понимаю",
                             reply_markup=choosing_markup)
    return CHOOSING


# endregion

# region Telegram Setup
dotenv.load_dotenv()
telegram_token = os.environ['TOKEN']
updater = Updater(telegram_token, use_context=True)
j_queue = updater.job_queue
dispather = updater.dispatcher

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],

    states={
        CHOOSING: [MessageHandler(Filters.regex(r'^Подписаться на сайт$'), add_command),
                   MessageHandler(Filters.regex(r'^Отписаться$'), remove_command),
                   MessageHandler(Filters.regex(r'^Мои подписки$'), sub_list)],
        ADD_COMMAND: [MessageHandler(Filters.text, add_text)],
        REMOVE_COMMAND: [MessageHandler(Filters.text, remove_text)]
    },

    fallbacks=[]
)
dispather.add_handler(conv_handler)

updater.start_polling()

j_queue.run_repeating(refresh_function, 900)
# endregion
