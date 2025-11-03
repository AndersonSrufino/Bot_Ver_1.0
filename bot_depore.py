# --- FUNÇÃO AUXILIAR: BUSCA CÓDIGO DA CIDADE PELO NOME ---
import telepot, time, json, requests, magic, os, pytesseract, traceback, logging
from datetime import date, timedelta
from PIL import Image, ImageDraw, ImageFont
from geopy import distance

# ---------------------------------------------------------------------------
# bot_depore.py
# Bot Telegram multifuncional: comandos de texto, OCR, clima, localização.
#
# Principais funcionalidades:
# - Comando 'imagem <texto>': gera imagem com texto e envia ao usuário.
# - Comando 'clima': previsão do tempo via INMET.
# - Comando '?', '? lat,lon': localização base ou envio de coordenadas.
# - Envio de foto: OCR automático.
# - Envio de documento: identifica tipo do arquivo.
# - Envio de localização: calcula distância entre dois pontos.
# ---------------------------------------------------------------------------

# telepot.api.set_proxy('http://192.168.0.1:3128',('usuario','senha'))
# proxy = {
#    'http': 'http://usuário:senha@192.168.0.1:3128',
#    'https': 'http://usuário:senha@192.168.0.1:3128',
# }



# --- CONFIGURAÇÃO ROBUSTA DO TESSERACT ---
# Caminho do executável do Tesseract (ajuste conforme sua instalação)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# Caminho da pasta tessdata (ajuste conforme sua instalação)
tessdata_path = r"C:\Program Files\Tesseract-OCR\tessdata"
os.environ["TESSDATA_PREFIX"] = tessdata_path


# --- CONFIGURAÇÃO DE LOG ---
# Logs são gravados em bot.log para facilitar depuração e auditoria.
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Armazena a última localização recebida por chat para cálculo de distância.
last_location = {}


# --- MANIPULADORES DE COMANDOS DE TEXTO ---
def handle_imagem(char_id, mensagem):
    """Gera uma imagem simples com o texto informado e envia ao chat.

    Exemplo de uso:
    - Usuário envia: imagem Olá mundo!
    - Bot responde com uma imagem azul contendo o texto 'Olá mundo!'.
    """
    partes = mensagem.split()
    if len(partes) < 2:
        bot.sendMessage(char_id, "Por favor, use o formato: imagem <texto>")
        return  # Sai da função se o formato estiver errado

    texto_para_imagem = " ".join(partes[1:])
    file_path = "temp_image.png"

    try:
        # Cria a imagem RGB 200x50 azul
        img = Image.new("RGB", (200, 50), color="blue")
        d = ImageDraw.Draw(img)
        # Usa fonte Calibri tamanho 15 (ajuste se necessário)
        fnt = ImageFont.truetype("C:\\Windows\\Fonts\\calibri.ttf", 15)
        d.text((10, 15), texto_para_imagem, font=fnt, fill=(255, 255, 255))
        img.save(file_path)

        # Envia a imagem para o usuário
        with open(file_path, "rb") as photo:
            bot.sendPhoto(char_id, photo)

    finally:
        # Remove o arquivo temporário
        if os.path.exists(file_path):
            os.remove(file_path)

def buscar_codigo_cidade(nome_cidade):
    """Busca o código da cidade no INMET a partir do nome informado pelo usuário.
    Faz uma requisição para a lista de cidades do INMET e retorna o código correspondente.
    Retorna None se não encontrar.
    """
    try:
        # API pública do INMET com lista de cidades e códigos
        url = "https://apiprevmet3.inmet.gov.br/municipios/"
        resposta = requests.get(url, timeout=10)
        if resposta.status_code != 200:
            return None
        cidades = resposta.json()
        nome_cidade = nome_cidade.strip().lower()
        for cidade in cidades:
            # Busca por nome exato ou parcial (ignora acentuação e caixa)
            if nome_cidade in cidade['nome'].lower() == nome_cidade:
                return cidade['geocode']
        return None
    except Exception as e:
        logging.error("Erro ao buscar código da cidade: %s", e)
        return None

# --- METODO PARA VERIFICAR O CLIMA PELA API INMET ---
def handle_clima(char_id, nome_cidade):
    """Busca a previsão do tempo para uma cidade usando a API do INMET.

    Exemplo de uso:
    - Usuário envia: clima Fortaleza
    - Bot responde com a previsão do tempo para Fortaleza para hoje e amanhã.
    """
    if not nome_cidade:
        bot.sendMessage(char_id, "Por favor, informe o nome da cidade. Ex: clima Fortaleza")
        return

    codigo_cidade = buscar_codigo_cidade(nome_cidade)

    if not codigo_cidade:
        bot.sendMessage(char_id, f"Não consegui encontrar a cidade '{nome_cidade}'. Verifique o nome e tente novamente.")
        return

    try:
        url = f"https://apiprevmet3.inmet.gov.br/previsao/{codigo_cidade}"
        previsao_data = requests.get(url, timeout=10).json()

        # A chave do dicionário é o próprio código da cidade
        dados_cidade = previsao_data.get(codigo_cidade)
        if not dados_cidade:
            bot.sendMessage(char_id, f"Não foi possível obter a previsão para {nome_cidade}.")
        # O JSON retornado já é o objeto da cidade, a chave é o próprio código.
        # Não é necessário fazer .get(codigo_cidade)
        if not previsao_data or not isinstance(previsao_data, dict):
            bot.sendMessage(char_id, f"Não foi possível obter a previsão para '{nome_cidade}'. A resposta da API estava vazia ou em formato inesperado.")
            return

        hoje = date.today()
        amanha = hoje + timedelta(days=1)

        previsao_hoje = dados_cidade.get(hoje.strftime("%d/%m/%Y"))
        previsao_amanha = dados_cidade.get(amanha.strftime("%d/%m/%Y"))
        previsao_hoje = previsao_data.get(hoje.strftime("%d/%m/%Y"))
        previsao_amanha = previsao_data.get(amanha.strftime("%d/%m/%Y"))

        if not previsao_hoje or not previsao_amanha:
            bot.sendMessage(char_id, f"A previsão para '{nome_cidade}' para hoje ou amanhã não está disponível no momento.")
            return

        nome_cidade_formatado = previsao_hoje['manha']['entidade']
        resposta = f"Previsão do tempo para {nome_cidade_formatado}:\n\n"
        resposta += f"*Hoje ({hoje.strftime('%d/%m')}):*\n"
        resposta = f"🌦️ Previsão do tempo para {nome_cidade_formatado}:\n\n"
        resposta += f"🗓️ *Hoje ({hoje.strftime('%d/%m')}):*\n"
        resposta += f"Mañana: {previsao_hoje['manha']['resumo']}\n"
        resposta += f"Tarde: {previsao_hoje['tarde']['resumo']}\n"
        resposta += f"Noite: {previsao_hoje['noite']['resumo']}\n\n"
        resposta += f"*Amanhã ({amanha.strftime('%d/%m')}):*\n"
        resposta += f"🗓️ *Amanhã ({amanha.strftime('%d/%m')}):*\n"
        resposta += f"{previsao_amanha['resumo']}"

        bot.sendMessage(char_id, resposta, parse_mode='Markdown')

    except requests.exceptions.RequestException as e:
        logging.error("Erro de requisição ao INMET: %s", e)
        bot.sendMessage(char_id, "Desculpe, o serviço de previsão do tempo está indisponível no momento.")
    except Exception as e:
        logging.error("Erro ao processar previsão do tempo: %s", e)
        bot.sendMessage(char_id, f"Ocorreu um erro ao buscar a previsão do tempo.")


# --- METODO PARA DIRECIONAR COMANDOS DE TEXTO ---
def handle_text(char_id, msg):
    """Roteador para comandos recebidos como texto.
    Extrai o comando e chama o handler correspondente.
    """
    mensagem = msg["text"]
    partes = mensagem.strip().split()
    comando = partes[0].lower() if partes else ""

    if comando == "imagem":
        handle_imagem(char_id, mensagem)
    elif comando == "clima":
        # Permite: clima Fortaleza, clima "São Paulo", etc.
        nome_cidade = " ".join(partes[1:]) if len(partes) > 1 else None
        handle_clima(char_id, nome_cidade)
    elif comando == "?":
        # passar o dict completo para que handle_geo acesse 'location' ou 'text'
        handle_geo(char_id, msg)
    else:
        bot.sendMessage(char_id, "Comando de texto não reconhecido.")


# --- MANIPULADORES DE TIPOS DE CONTEÚDO ---
def handle_photo(char_id, msg):
    """Processa fotos enviadas pelo usuário.
    Faz OCR (pytesseract) e responde com o texto extraído ou mensagem de erro.
    """
    file_id = msg["photo"][-1]["file_id"]
    file_path = f"{file_id}.jpg"
    try:
        # Baixa a foto temporária
        bot.download_file(file_id, file_path)
        try:
            foto = Image.open(file_path)
            try:
                # OCR na imagem
                texto = pytesseract.image_to_string(foto, lang="por")
                if texto and not texto.isspace():
                    bot.sendMessage(char_id, f"Texto extraído da imagem:\n\n{texto}")
                else:
                    bot.sendMessage(char_id, "Recebi sua foto, mas não consegui encontrar nenhum texto nela.")
            except pytesseract.pytesseract.TesseractError as t_err:
                tb = traceback.format_exc()
                logging.error("TesseractError durante OCR: %s\n%s", t_err, tb)
                bot.sendMessage(char_id, "Erro no OCR: falha ao inicializar o Tesseract ou carregar os dados de idioma. Verifique a instalação e a variável TESSDATA_PREFIX.")
            except Exception as ocr_error:
                tb = traceback.format_exc()
                logging.exception("Erro inesperado durante OCR: %s", ocr_error)
                bot.sendMessage(char_id, f"Ocorreu um erro ao tentar ler o texto da imagem. Erro: {ocr_error}")
        except Exception as img_err:
            tb = traceback.format_exc()
            logging.exception("Erro ao abrir/processar imagem: %s", img_err)
            bot.sendMessage(char_id, f"Erro ao processar a imagem: {img_err}")
    finally:
        # Remove a foto temporária
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as remove_err:
                logging.warning("Falha ao remover arquivo temporario %s: %s", file_path, remove_err)


def handle_geo(char_id, msg):
    """Calcula distância entre duas localizações enviadas pelo chat.

    - Se receber apenas '?', registra localização base do bot e pede a do usuário.
    - Se receber '? lat,lon', envia localização para o usuário.
    - Se receber uma localização, armazena ou calcula distância até a anterior.
    """
    try:
        # se a mensagem começar com '?', pode ser '? lat,lon' ou apenas '?' para registrar base
        text = msg.get('text', '').strip()
        if text.startswith('?'):
            coords_text = text[1:].strip()
            # caso o usuário envie apenas '?' registramos uma localização base
            if coords_text == '':
                bot_lat, bot_lon = -3.8007494007575136, -38.59834326748713
                last_location[char_id] = (bot_lat, bot_lon)
                bot.sendMessage(char_id, "Localização base registrada. Agora envie sua localização para que eu calcule a distância.")
                logging.info("Localização base registrada para chat %s: %s,%s", char_id, bot_lat, bot_lon)
                return

            # tenta extrair duas coordenadas do texto (aceita separador ',' ';' ou espaço)
            raw = coords_text.replace(';', ',')
            parts = raw.replace(',', ' ').split()
            if len(parts) >= 2:
                try:
                    lat = float(parts[0].replace(',', '.'))
                    lon = float(parts[1].replace(',', '.'))
                    try:
                        return bot.sendLocation(char_id, lat, lon, live_period=360)
                    except Exception:
                        # caso api do telegran fora do ar, enviar como mensagem com link
                        maps = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        return bot.sendMessage(char_id, f"Coordenadas: {lat}, {lon}\n{maps}")
                except ValueError:
                    bot.sendMessage(char_id, "Não consegui entender as coordenadas. Use: ? lat,lon (ex: ? -3.80,-38.59)")
                    return
            else:
                bot.sendMessage(char_id, "Formato de coordenadas inválido. Use: ? lat,lon ou envie uma localização pelo botão do Telegram.")
                return

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
    """Baixa documento enviado, identifica tipo com magic e responde ao usuário."""
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
    """Roteador principal: despacha cada mensagem para o handler correto.

    Usa telepot.glance para identificar o tipo de conteúdo e chama o handler
    apropriado. Facilita manutenção e extensão do bot.
    """
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
