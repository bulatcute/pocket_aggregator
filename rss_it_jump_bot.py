from telegram.ext import Updater, CommandHandler
import telegram
import requests
from bs4 import BeautifulSoup
import feedparser
import urllib.request
import time


def get_rss_feed1(website_url):
    page = urllib.request.urlopen(website_url)
    soup = BeautifulSoup(page)

    link = soup.find('link', type='application/rss+xml')
    if link is None:
        return 'no link'
    return link['href']


telegram_token = '1017866523:AAEAVHRHWbnJO48nm5Rud8bKAST-1-sUVD0'
updater = Updater(telegram_token, use_context=True)
dispather = updater.dispatcher


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я — бот-новостной агрегатор, разработанный на смене IT Jump Pro\
\nНапиши мне /help и я скажу тебе как мной пользоваться")


def help(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Напиши мне /read {ссылка на новостной ресурс} и я \
покажу тебе последние статьи этого сайта.\
\nНапример: /read https://dtf.ru')


def read(update, context):
    args = update.message.text.split()
    del args[0]

    arg_url = args[0]

    # arg_name = args[1]
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Ищу RSS ленту на {arg_url}...')

    feed_url = get_rss_feed1(arg_url)
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
        article_published_at_parsed = entry.published_parsed  # Time object
        content = entry.summary

        msg = f'''{article_title}
{content}
----------------------------
published at {article_published_at}
----------------------------
{article_link}'''
        print(msg)
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


dispather.add_handler(CommandHandler("start", start))
dispather.add_handler(CommandHandler("help", help))
dispather.add_handler(CommandHandler("read", read))

updater.start_polling()
