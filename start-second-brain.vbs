' Javis Second Brain - silent autostart (python.exe + window 0 = an hoan toan)
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = currentDir
WshShell.Environment("PROCESS")("PYTHONUTF8") = "1"
WshShell.Environment("PROCESS")("PYTHONIOENCODING") = "utf-8"
WshShell.Run """" & currentDir & "\venv\Scripts\python.exe"" app.py", 0, False
