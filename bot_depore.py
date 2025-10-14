
import telepot, time


def principal(msg):
    content_type, char_type, char_id = telepot.glance(msg)
    
    if content_type == 'text':
        char_id = msg['chat']['id']
        mensagem = msg['text']

    if mensagem == 'oi':
        bot.sendMessage(char_id,'teste de plataforma 3')

bot = telepot.Bot('8218649012:AAF_uIHTNiJFFzsnTpHRyldTogsD1VU-YjY')
bot.message_loop(principal)

while 1:
    time.sleep(5)