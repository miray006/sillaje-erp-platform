Set WshShell = CreateObject("WScript.Shell")
' Run Bank Flask app in background
WshShell.Run "py banka_app.py", 0, False
WScript.Sleep 2000
' Open web browser at localhost:5001
WshShell.Run "http://127.0.0.1:5001"
