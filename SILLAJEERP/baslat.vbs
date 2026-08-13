Set WshShell = CreateObject("WScript.Shell")
' Run Flask app in background
WshShell.Run "py app.py", 0, False
WScript.Sleep 2000
' Open web browser at localhost:5000
WshShell.Run "http://127.0.0.1:5000"
