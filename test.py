import subprocess
import os
import requests


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

enviar_mensaje("test aasdsdasd")
