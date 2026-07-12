Name "DevOrbit"
OutFile "dist\\DevOrbit-Setup.exe"
InstallDir "$LOCALAPPDATA\\DevOrbit"
RequestExecutionLevel user

Section "Install"
  SetOutPath $INSTDIR
  File "dist\\DevOrbit.exe"
  File "dist\\models.json"
  File "dist\\.env.example"
  File "dist\\providers.example.json"
  File "dist\\settings.example.json"
  File "dist\\README.md"
  File "dist\\SECURITY.md"
  File "dist\\PRODUCTION.md"
  CreateDirectory "$INSTDIR\\workspace"
  CreateShortcut "$DESKTOP\\DevOrbit.lnk" "$INSTDIR\\DevOrbit.exe"
  CreateShortcut "$SMPROGRAMS\\DevOrbit.lnk" "$INSTDIR\\DevOrbit.exe"
  WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\\DevOrbit.lnk"
  Delete "$SMPROGRAMS\\DevOrbit.lnk"
  Delete "$INSTDIR\\DevOrbit.exe"
  Delete "$INSTDIR\\Uninstall.exe"
  RMDir /r "$INSTDIR"
SectionEnd
