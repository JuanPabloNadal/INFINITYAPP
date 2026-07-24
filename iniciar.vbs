' Inicia Infinity Inmobiliaria SIN ventana de terminal.
' Corre en segundo plano con un icono en la bandeja del sistema (menu Salir).
Option Explicit
Dim fso, sh, carpeta, pythonw, script
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = carpeta & "\venv\Scripts\pythonw.exe"
script  = carpeta & "\run.py"

If Not fso.FileExists(pythonw) Then
    MsgBox "No se encontro el entorno. Ejecuta primero setup.bat.", _
           vbExclamation, "Infinity Inmobiliaria"
    WScript.Quit 1
End If

sh.CurrentDirectory = carpeta
sh.Environment("Process")("INFINITY_TRAY") = "1"
' 0 = ventana oculta ; False = no esperar
sh.Run """" & pythonw & """ """ & script & """", 0, False
