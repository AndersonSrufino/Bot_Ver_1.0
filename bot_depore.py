import telepot, time, json, requests, magic, os
from datetime import date, timedelta
from PIL import Image, ImageDraw, ImageFont

# telepot.api.set_proxy('http://192.168.0.1:3128',('usuario','senha'))
# proxy = {
#    'http': 'http://usuário:senha@192.168.0.1:3128',
#    'https': 'http://usuário:senha@192.168.0.1:3128',
# }


# --- MANIPULADORES DE COMANDOS DE TEXTO ---
def handle_imagem(char_id, mensagem):
    partes = mensagem.split()
    if len(partes) < 2:
        bot.sendMessage(char_id, "Por favor, use o formato: imagem <texto>")
        return  # Sai da função se o formato estiver errado

    texto_para_imagem = " ".join(partes[1:])
    file_path = "temp_image.png"

    try:
        # Cria a imagem
        img = Image.new("RGB", (200, 50), color="blue")
        d = ImageDraw.Draw(img)
        fnt = ImageFont.truetype("C:\\Windows\\Fonts\\calibri.ttf", 15)
        d.text((10, 15), texto_para_imagem, font=fnt, fill=(255, 255, 255))
        img.save(file_path)

        # Envia a foto usando 'with' para garantir que o arquivo seja fechado
        with open(file_path, "rb") as photo:
            bot.sendPhoto(char_id, photo)

    finally:
        # Garante que a imagem temporária seja sempre removida
        if os.path.exists(file_path):
            os.remove(file_path)

# --- METODO PARA VERIFICAR O CLIMA PELA API INMET ---
def handle_clima(char_id):
    try:
        codigo_cidade = "2304400"
        requisicao = requests.get(
            f"https://apiprevmet3.inmet.gov.br/previsao/{codigo_cidade}"
        ).json()

        data = date.today()
        cidade_nome = requisicao[codigo_cidade][data.strftime("%d/%m/%Y")][
            "manha"
        ]["entidade"]
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
                resposta += (
                    f"*{data_str}* (resumo): {previsao_dia['resumo']}\n"
                )
            data += timedelta(days=1)

        bot.sendMessage(char_id, resposta, parse_mode="Markdown")

    except Exception as e:
        bot.sendMessage(
            char_id,
            f"Desculpe, não consegui obter a previsão do tempo. Erro: {e}",
        )


# --- METODO PARA DIRECIONAR COMANDOS DE TEXTO ---
def handle_text(char_id, msg):
    mensagem = msg["text"]
    comando = mensagem.lower().split()[0]  # Pega a primeira palavra como comando

    if comando == "imagem":
        handle_imagem(char_id, mensagem)
    elif comando == "clima":
        handle_clima(char_id)
    else:
        bot.sendMessage(char_id, "Comando de texto não reconhecido.")


# --- MANIPULADORES DE TIPOS DE CONTEÚDO ---
def handle_photo(char_id, msg):
    file_id = msg["photo"][-1]["file_id"]
    file_path = f"{file_id}.jpg"  # Define um nome para o arquivo temporário

    try:
        # Baixa o arquivo da foto.
        bot.download_file(file_id, file_path)

        # Usa a biblioteca magic para confirmar o tipo (opcional, mas bom para consistência).
        tipo_arquivo = magic.from_file(file_path)
        bot.sendMessage(char_id, f"Recebi sua foto! O tipo dela é: {tipo_arquivo}")

        # Aqui você poderia adicionar um processamento de imagem, se quisesse.

    finally:
        # Garante que a foto baixada seja sempre removida.
        if os.path.exists(file_path):
            os.remove(file_path)

# --- METODO PARA IDENTIFICAR O TIPO DE DOCUMENTO ---
def handle_document(char_id, msg):
    file_id = msg["document"]["file_id"]
    file_path = file_id

    try:
        bot.download_file(file_id, file_path)
        tipo_arquivo = magic.from_file(file_path)
        bot.sendMessage(char_id, f"Recebi seu documento! O tipo dele é: {tipo_arquivo}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# --- Metodo PRINCIPAL ---
def principal(msg):
    content_type, char_type, char_id = telepot.glance(msg)

    if content_type == "text":
        handle_text(char_id, msg)
    elif content_type == "photo":
        handle_photo(char_id, msg)
    elif content_type == "document":
        handle_document(char_id, msg)
    else:
        bot.sendMessage(char_id, "Desculpe, não sei como processar este tipo de conteúdo.")


bot = telepot.Bot("8218649012:AAF_uIHTNiJFFzsnTpHRyldTogsD1VU-YjY")
bot.message_loop(principal)

while 1:
    time.sleep(5)
