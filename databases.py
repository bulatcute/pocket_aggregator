from __future__ import absolute_import, print_function

from pony.orm import *

db = Database("sqlite", "bot.sqlite", create_db=True)


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
def add_feed(url):
    return Feed(url=url)


db.generate_mapping(create_tables=True)

with db_session:
    u1 = add_user(32424542)
    f1 = add_feed('https://dtf.ru')

    add_feed_user(f1, u1)
    print(select(p for p in User)[:])
