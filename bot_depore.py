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
            if nome_cidade in cidade['nome'].lower():
                return cidade['geocode']
        return None
    except Exception as e:
        logging.error("Erro ao buscar código da cidade: %s", e)
        return None

# --- METODO PARA VERIFICAR O CLIMA PELA API INMET ---
def handle_clima(char_id, nome_cidade):
    """Busca a previsão do tempo via API do INMET para a cidade informada.
    Se não for informada, pede ao usuário. Se a API falhar, envia mensagem de erro amigável.
    """
    try:
        # 1. PREPARAÇÃO E VALIDAÇÃO DA ENTRADA
        # Limpa espaços em branco e formata o nome da cidade (Ex: " fortaleza " -> "Fortaleza")
        cidade_nome = nome_cidade.strip().title() if nome_cidade else ""
        # Se o nome da cidade não foi fornecido com o comando, pede ao usuário para informar.
        if not nome_cidade:
            bot.sendMessage(char_id, "Por favor, informe a cidade. Exemplo: clima Fortaleza")
            return

        # 2. BUSCA DO CÓDIGO DA CIDADE
        # Usa a função auxiliar para obter o código geográfico da cidade (ex: "Fortaleza" -> "2304400")
        codigo_cidade = buscar_codigo_cidade(nome_cidade)
        # Se o código não for encontrado, informa ao usuário e encerra a função.
        if not codigo_cidade:
            bot.sendMessage(char_id, f"Cidade '{nome_cidade}' não encontrada. Tente o nome completo ou sem acentos.")
            return

        # 3. REQUISIÇÃO À API DE PREVISÃO DO TEMPO
        # Monta a URL da API do INMET usando o código da cidade obtido.
        url_previsao = f"https://apiprevmet3.inmet.gov.br/previsao/{codigo_cidade}"
        # Faz a requisição GET para a API, com um timeout de 15 segundos.
        resposta_api = requests.get(url_previsao, timeout=15)
        # Verifica se a resposta da API foi um erro (ex: 404, 500). Se sim, lança uma exceção.
        resposta_api.raise_for_status()  # Lança exceção para erros HTTP (4xx ou 5xx)
        # Converte a resposta JSON (texto) em um dicionário Python.
        dados_completos = resposta_api.json()

        # 4. EXTRAÇÃO DOS DADOS DA RESPOSTA
        # A estrutura da API é {codigo_cidade: {data: dados_previsao}}.
        # Usamos .get(codigo_cidade) para acessar o dicionário com as previsões diárias de forma segura.
        previsoes_diarias = dados_completos.get(codigo_cidade, {})

        # Se, mesmo com a resposta OK, os dados de previsão não forem encontrados, informa o usuário.
        if not previsoes_diarias:
            bot.sendMessage(char_id, f"Não foram encontradas previsões para {cidade_nome}. A API pode estar indisponível.")
            return

        # 5. MONTAGEM DA MENSAGEM DE RESPOSTA
        # Inicia a string de resposta que será enviada ao usuário.
        resposta = f"O clima para {cidade_nome}\n\n"
        previsao_adicionada = False
        data = date.today() # Pega a data atual para começar a previsão.

        # Previsão para hoje e amanhã (detalhada)
        for i in range(2):
            data_str_display = data.strftime("%d/%m/%Y")
            data_str_api = data.strftime("%Y-%m-%d")
            previsao_dia = previsoes_diarias.get(data_str_api)

            if previsao_dia:
                previsao_adicionada = True
                resposta += f"*{data_str_display}*\n"
                # Usamos .get() para acesso seguro aos dados, evitando erros se uma chave não existir.
                manha = previsao_dia.get('manha', {})
                tarde = previsao_dia.get('tarde', {})
                noite = previsao_dia.get('noite', {})
                resposta += f"Manhã: {manha.get('resumo', 'N/A')} - Max: {manha.get('temp_max', 'N/A')} - Min: {manha.get('temp_min', 'N/A')}\n"
                resposta += f"Tarde: {tarde.get('resumo', 'N/A')} - Max: {tarde.get('temp_max', 'N/A')} - Min: {tarde.get('temp_min', 'N/A')}\n"
                resposta += f"Noite: {noite.get('resumo', 'N/A')} - Max: {noite.get('temp_max', 'N/A')} - Min: {noite.get('temp_min', 'N/A')}\n\n"
            data += timedelta(days=1)

        # Previsão resumida para os próximos 3 dias
        for i in range(5):
            data_str_display = data.strftime("%d/%m/%Y")
            data_str_api = data.strftime("%Y-%m-%d")
            previsao_dia = previsoes_diarias.get(data_str_api)

            if previsao_dia:
                previsao_adicionada = True
                resposta += f"*{data_str_display}* (resumo): {previsao_dia.get('resumo', 'N/A')}\n"
            data += timedelta(days=1) # Avança para o próximo dia.

        # 6. ENVIO DA RESPOSTA FINAL
        # Se nenhuma previsão foi encontrada no loop, envia uma mensagem de falha.
        if not previsao_adicionada:
            bot.sendMessage(char_id, f"Não foi possível obter a previsão para {cidade_nome}.")
        else:
            # Envia a mensagem formatada em Markdown para o usuário.
            bot.sendMessage(char_id, resposta, parse_mode="Markdown")

    except requests.exceptions.RequestException as http_err:
        # Captura erros de conexão/HTTP (API fora do ar, sem internet, etc.)
        logging.error(f"Erro de HTTP ao buscar clima: {http_err}")
        bot.sendMessage(char_id, "Desculpe, o serviço de previsão do tempo parece estar indisponível no momento.")
    except Exception as e:
        # Captura qualquer outro erro inesperado durante o processo.
        logging.error(f"Erro ao buscar clima: {e}")
        bot.sendMessage(
            char_id,
            "Desculpe, não consegui obter a previsão do tempo. Ocorreu um erro inesperado.",
        )


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
