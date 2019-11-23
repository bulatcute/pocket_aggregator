from pony.orm import *

db = Database()
class User(db.Entity):
    user_id = Required(int)
    sites = Set('Feed')

class Feed(db.Entity):
    url = Required(str)
    users = Set(User)

db.bind(provider='sqlite', filename='datebase.sqlite', create_db=True)

@db_session
def add_feed_user(feed, user):
    Feed.users.append(feed)

@db_session
def add_user(id):
    User(user_id=id)

@db_session
def add_feed(url):
    Feed(url=url)

u1 = add_user(32424542)
f1 = add_feed('https://dtf.ru')

add_feed_user(f1, u1)[:]
print(select(p for p in User))
