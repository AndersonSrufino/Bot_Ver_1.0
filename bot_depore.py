import telepot, time, json, requests, magic, os
from datetime import date, timedelta

# telepot.api.set_proxy('http://192.168.0.1:3128',('usuario','senha'))
# proxy = {
#    'http': 'http://usuário:senha@192.168.0.1:3128',
#    'https': 'http://usuário:senha@192.168.0.1:3128',
# }


def principal(msg):
    content_type, char_type, char_id = telepot.glance(msg)

    if content_type == "document":
        file_id = msg[content_type]["file_id"]
        # O nome do arquivo será o próprio file_id
        file_path = file_id 
        
        try:
            # Baixa o arquivo
            bot.download_file(file_id, file_path)
            
            # Verifica o tipo de arquivo
            tipo_arquivo = magic.from_file(file_path)
            bot.sendMessage(char_id, f"O tipo do arquivo é: {tipo_arquivo}")
            
        finally:
            # Garante que o arquivo seja removido, mesmo se ocorrer um erro
            if os.path.exists(file_path):
                os.remove(file_path)

    # codigo para verificar o clima na api inmet
    """
    if content_type == 'text':
        mensagem = msg['text']

        if mensagem.lower() == 'clima':
            try:
                # Use o código da sua cidade
                codigo_cidade = "2304400"
                requisicao = requests.get(f"https://apiprevmet3.inmet.gov.br/previsao/{codigo_cidade}").json()
                
                data = date.today()
                cidade_nome = requisicao[codigo_cidade][data.strftime("%d/%m/%Y")]["manha"]["entidade"]
                resposta = f"O clima para {cidade_nome}\n\n"

                # Previsão para hoje e amanhã (manhã, tarde, noite)
                for i in range(2):
                    data_str = data.strftime("%d/%m/%Y")
                    if data_str in requisicao[codigo_cidade]:
                        previsao_dia = requisicao[codigo_cidade][data_str]
                        resposta += f"*{data_str}*\n"
                        resposta += f"Manhã: {previsao_dia['manha']['resumo']} - Max: {previsao_dia['manha']['temp_max']} - Min: {previsao_dia['manha']['temp_min']}\n"
                        resposta += f"Tarde: {previsao_dia['tarde']['resumo']} - Max: {previsao_dia['manha']['temp_max']} - Min: {previsao_dia['manha']['temp_min']}\n"
                        resposta += f"Noite: {previsao_dia['noite']['resumo']} - Max: {previsao_dia['manha']['temp_max']} - Min: {previsao_dia['manha']['temp_min']}\n\n"
                    data += timedelta(days=1)

                # Previsão resumida para os próximos 3 dias
                for i in range(3):
                    data_str = data.strftime("%d/%m/%Y")
                    if data_str in requisicao[codigo_cidade]:
                        previsao_dia = requisicao[codigo_cidade][data_str]
                        resposta += f"*{data_str}* (resumo): {previsao_dia['resumo']}\n"
                    data += timedelta(days=1)

                bot.sendMessage(char_id, resposta, parse_mode='Markdown')

            except Exception as e:
                bot.sendMessage(char_id, f"Desculpe, não consegui obter a previsão do tempo. Erro: {e}")
    else:
        bot.sendMessage(char_id, f'Desculpe no momento funcionamos apenas com comandos em texto')
"""


bot = telepot.Bot("8218649012:AAF_uIHTNiJFFzsnTpHRyldTogsD1VU-YjY")
bot.message_loop(principal)

while 1:
    time.sleep(5)
