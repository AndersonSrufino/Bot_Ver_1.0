import telepot, time, json, requests, magic, os, pytesseract, traceback, logging
from datetime import date, timedelta
from PIL import Image, ImageDraw, ImageFont
from geopy import distance

# telepot.api.set_proxy('http://192.168.0.1:3128',('usuario','senha'))
# proxy = {
#    'http': 'http://usuário:senha@192.168.0.1:3128',
#    'https': 'http://usuário:senha@192.168.0.1:3128',
# }


# --- CONFIGURAÇÃO ROBUSTA DO TESSERACT ---
# Define o caminho para o executável do Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Define a variável de ambiente que aponta para a pasta de dados de idioma
# Esta é a forma mais confiável de garantir que o Tesseract encontre os idiomas.
tessdata_path = r"C:\Program Files\Tesseract-OCR\tessdata"
os.environ["TESSDATA_PREFIX"] = tessdata_path

# --- CONFIGURAÇÃO DE LOG ---
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Armazenamento simples da última localização por chat
last_location = {}


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
        cidade_nome = requisicao[codigo_cidade][data.strftime("%d/%m/%Y")]["manha"][
            "entidade"
        ]
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
    elif comando == "?":
        # passar o dict completo para que handle_geo acesse 'location' ou 'text'
        handle_geo(char_id, msg)
    else:
        bot.sendMessage(char_id, "Comando de texto não reconhecido.")


# --- MANIPULADORES DE TIPOS DE CONTEÚDO ---
def handle_photo(char_id, msg):
    file_id = msg["photo"][-1]["file_id"]
    file_path = f"{file_id}.jpg"
    try:
        bot.download_file(file_id, file_path)

        try:
            foto = Image.open(file_path)

            try:
                # tenta extrair texto com tesseract
                texto = pytesseract.image_to_string(foto, lang="por")
                if texto and not texto.isspace():
                    bot.sendMessage(char_id, f"Texto extraído da imagem:\n\n{texto}")
                else:
                    bot.sendMessage(
                        char_id,
                        "Recebi sua foto, mas não consegui encontrar nenhum texto nela.",
                    )

            except pytesseract.pytesseract.TesseractError as t_err:
                # Erro específico do Tesseract (problema com exec, tessdata, permissões etc.)
                tb = traceback.format_exc()
                logging.error("TesseractError durante OCR: %s\n%s", t_err, tb)
                bot.sendMessage(
                    char_id,
                    "Erro no OCR: falha ao inicializar o Tesseract ou carregar os dados de idioma. Verifique a instalação e a variável TESSDATA_PREFIX.",
                )

            except Exception as ocr_error:
                # Erro genérico durante o OCR
                tb = traceback.format_exc()
                logging.exception("Erro inesperado durante OCR: %s", ocr_error)
                bot.sendMessage(
                    char_id,
                    f"Ocorreu um erro ao tentar ler o texto da imagem. Erro: {ocr_error}",
                )

        except Exception as img_err:
            tb = traceback.format_exc()
            logging.exception("Erro ao abrir/processar imagem: %s", img_err)
            bot.sendMessage(char_id, f"Erro ao processar a imagem: {img_err}")

    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as remove_err:
                logging.warning(
                    "Falha ao remover arquivo temporario %s: %s", file_path, remove_err
                )


def handle_geo(char_id, msg):
    """Calcula distância entre duas posições 'location' enviadas pelo mesmo chat.

    Fluxo:
    - Se for a primeira localização do chat, guarda em last_location e pede a segunda.
    - Se já existir uma localização anterior, calcula a distância, envia e remove o estado.
    """
    try:
        # se a mensagem contiver apenas o comando '?', envie uma localização de exemplo
        if msg.get('text', '').strip() == '?':
            try:
                # tenta enviar como localização (latitude, longitude)
                return bot.sendLocation(char_id, -3.8007494007575136, -38.59834326748713)
            except Exception:
                # fallback para mensagem de texto se sendLocation não estiver disponível
                return bot.sendMessage(char_id, "-3.8007494007575136, -38.59834326748713")

        if "location" not in msg:
            bot.sendMessage(char_id, "Por favor, envie uma localização (location).")
            return

        lat = msg["location"].get("latitude")
        lon = msg["location"].get("longitude")

        if lat is None or lon is None:
            bot.sendMessage(char_id, "Localização inválida.")
            return

        if char_id not in last_location:
            # guarda primeira localização
            last_location[char_id] = (lat, lon)
            bot.sendMessage(
                char_id,
                "Localização registrada. Agora envie a segunda localização para calcular a distância.",
            )
            logging.info(
                "Registrada primeira localização para chat %s: %s,%s", char_id, lat, lon
            )
            return

        # já existe localização anterior -> calcula distância
        lat_i, lon_i = last_location.pop(char_id)
        lat_f, lon_f = lat, lon
        local_i = (lat_i, lon_i)
        local_f = (lat_f, lon_f)
        try:

            distancia_km = distance.distance(local_i, local_f).km
            bot.sendMessage(
                char_id,
                f"A distância entre as duas localizações é de {format(distancia_km, '.2f')} km",
            )
            logging.info(
                "Distância calculada para chat %s: %s km (from %s to %s)",
                char_id,
                distancia_km,
                local_i,
                local_f,
            )
        except Exception as dist_err:
            tb = traceback.format_exc()
            logging.exception("Erro ao calcular distância: %s", dist_err)
            bot.sendMessage(char_id, f"Erro ao calcular a distância: {dist_err}")

    except Exception as e:
        tb = traceback.format_exc()
        logging.exception("Erro no handle_geo: %s", e)
        bot.sendMessage(char_id, f"Erro ao processar localização: {e}")


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
    elif content_type == "location":
        handle_geo(char_id, msg)
    else:
        bot.sendMessage(
            char_id, "Desculpe, não sei como processar este tipo de conteúdo."
        )


bot = telepot.Bot("8218649012:AAF_uIHTNiJFFzsnTpHRyldTogsD1VU-YjY")
bot.message_loop(principal)

while 1:
    time.sleep(5)
