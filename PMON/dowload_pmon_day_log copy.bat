@echo off

chcp 65001 > NUL
echo !!!! -=== OKHO HE 3AKPbIBATb ===- !!!!     

call :fromnow -1

>>log.txt 2>&1(
echo %yyyymmdd%

for %%a in (107, 106) do (
cd C:\PMON\172.18.0.%%a
echo 172.18.0.%%a
tftp -i 172.18.0.%%a GET /pmon/daily-dmr-%yyyymmdd%.pm & timeout /t 0 > NUL
)

echo Download complete
)
goto :eof

:FromNow
setLocal
set now=%date%
set /a yyyy=%now:~-4%
set /a mm=1%now:~3,2%-100
set /a dd=1%now:~,2%-100
set /a JD=%~1+dd-32075+1461*(yyyy+4800+(mm-14)/12)/4+367*(mm-2-(mm-14)/12*12)/12-3*((yyyy+4900+(mm-14)/12)/100)/4
set /a L=JD+68569,N=4*L/146097,L=L-(146097*N+3)/4,I=4000*(L+1)/1461001
set /a L=L-1461*I/4+31,J=80*L/2447,K=L-2447*J/80,L=J/11
set /a J=J+2-12*L,I=100*(N-49)+I+L
set /a yyyy=I,mm=100+J,dd=100+K
EndLocal& set yyyymmdd=%yyyy%%mm:~-2%%dd:~-2%
exit /b
