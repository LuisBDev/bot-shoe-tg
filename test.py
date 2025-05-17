import subprocess
import os
import time
import requests
from playwright.sync_api import sync_playwright


BOT_TOKEN = '7341327293:AAF5RJYD719VFFDCYuIekurEdH9p5KIPfjY'
CHAT_ID = '1125783102'

def toggle_tunnelbear():
    ahk_path = r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe"
    script_path = os.path.abspath("scripttunnelbear.ahk")
    print(f"Running AutoHotkey script: {script_path}")
    subprocess.run([ahk_path, script_path], check=True)



def enviar_mensaje(mensaje):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {'chat_id': CHAT_ID, 'text': mensaje}
    response = requests.get(url, params=params)
    return response.json()

def check_health_shoedazzlepage(url="https://www.shoedazzle.com/"):
    """Intenta acceder a la página con Playwright en modo headless hasta obtener status 200, reiniciando IP si es necesario."""
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                page = context.new_page()
                response = page.goto(url, timeout=60000, wait_until="domcontentloaded")
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
            
            

toggle_tunnelbear()
