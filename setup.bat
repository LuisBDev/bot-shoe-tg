@echo off

:: Verificar si ya existe el entorno virtual
if exist venv (
    echo El entorno virtual 'venv' ya existe.
) else (
    echo Creando el entorno virtual 'venv'...
    python -m venv venv
)

:: Activar el entorno virtual
if exist venv\Scripts\activate (
    echo Activando el entorno virtual...
    call venv\Scripts\activate
) else (
    echo Error: No se pudo encontrar el entorno virtual. Asegúrate de que se creó correctamente.
    pause
    exit /b
)

:: Instalar las dependencias
echo Instalando las dependencias...
pip install -r requirements.txt

:: Instalar los navegadores necesarios para Playwright
echo Instalando los navegadores de Playwright...
playwright install

:: Ejecutar el script de Python
echo Ejecutando codigo.py...
python codigo.py