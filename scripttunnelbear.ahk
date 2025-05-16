; AutoHotkey v2 - Toggle ON/OFF de TunnelBear en cualquier monitor (principal a la izquierda)

SetTitleMatchMode "2" ; Coincidencia parcial del título de ventana

if WinExist("TunnelBear") {
    WinActivate
    Sleep 1000

    hwnd := WinActive()

    ; Obtener posición de la ventana cliente (área sin bordes ni barra de título)
    WinGetClientPos &clientX, &clientY, &clientW, &clientH, hwnd

    ; Coordenadas relativas al botón ON/OFF dentro del área cliente (según Window Spy)
    relX := 124
    relY := 46

    ; Coordenadas absolutas calculadas a partir de cliente
    absX := clientX + relX
    absY := clientY + relY

    CoordMode "Mouse", "Screen"
    MouseMove absX, absY, 20
    Click
} else {
    MsgBox "TunnelBear no está abierto."
}
