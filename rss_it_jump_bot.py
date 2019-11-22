#region Imports
from telegram.ext import Updater, CommandHandler
from bs4 import BeautifulSoup
import feedparser
import urllib.request
import telegram
#endregion

#region Util functions
def get_user_data(data_path):
    with open(data_path, 'rt') as data_file:
        data_list = data_file.read().split('\n')
    user_data = {data_list[i * 6] : [data_list[i*6 + j] for j in range(1, 6)] for i in range(len(data_list) // 6)}
    for key in user_data.keys():
        user_data[key][-1] = user_data[key][-1].split() # Если подписки записаны через пробел
    # В итоге должно получиться что-то типа {id : [first_name, is_bot, username, language_code, [subscribes]]}
    return user_data

def set_user_data(data_path, user_data):
    data_list = []
    for key in user_data.keys():
        data_list.append(str(key))
        data_list.extend([str(user_data[key][i]) for i in range(4)])
        data_list.append(' '.join(user_data[key][-1])) 
    with open(data_path, 'wt') as data_file:
        data_file.write('\n'.join(data_list))

def get_rss_feed1(website_url):
    page = urllib.request.urlopen(website_url)
    soup = BeautifulSoup(page)

    link = soup.find('link', type='application/rss+xml')
    if link is None:
        return 'no link'
    return link['href']
#endregion

#region Start
def start(update, context):
    user_data = get_user_data('user_db.txt')
    tg_user = update.message.from_user

    if not tg_user.id in user_data.keys():
        user_data[tg_user.id] = [tg_user.first_name, tg_user.is_bot, tg_user.username, tg_user.language_code, []]

    set_user_data('user_db.txt', user_data)

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

        msg = f'''{article_title}
----------------------------
published at {article_published_at}
----------------------------
{article_link}'''
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
#endregion

#region Add
def add(update, context):
    args = update.message.text.split()
    arg_url = args[1]
    del args
    user_data = get_user_data('user_db.txt')
    tg_user = update.message.from_user

    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Ищу RSS ленту на {arg_url}...')

    feed_url = get_rss_feed1(arg_url)
    if feed_url == 'no link':
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Извините, я не нашёл RSS ленту на этом'
                                                                        f' сайте. Попробуйте ввести другую ссылку')
        return

    if feed_url.startswith('/'):
        feed_url = arg_url + feed_url

    print(user_data, tg_user.id, feed_url)
    if(not feed_url in user_data[str(tg_user.id)][-1]):
        user_data[str(tg_user.id)][-1].append(feed_url)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Теперь вы подписаны на {feed_url}')
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Этот сайт уже есть среди ваших подписок')
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Список ваших подписок: '
                                                                    f'{user_data[str(tg_user.id)][-1]}')
    set_user_data('user_db.txt', user_data)
#endregion

#region Setup
telegram_token = 'TOKEN'
updater = Updater(telegram_token, use_context=True)
dispather = updater.dispatcher

dispather.add_handler(CommandHandler("start", start))
dispather.add_handler(CommandHandler("help", help))
dispather.add_handler(CommandHandler("read", read))
dispather.add_handler(CommandHandler("add", add))

updater.start_polling()
#endregion