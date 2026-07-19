@echo off

chcp 65001 > NUL
echo !!!! -=== OKHO HE 3AKPbIBATb ===- !!!!     

call :fromnow -1
#For Pasolink NEO
for %%a in (107, 106, 105, 104, 103, 102, 101, 100, 99, 96, 95, 94, 93, 92, 91, 90, 89, 88, 86, 85, 84, 83, 82, 81, 80, 79, 78, 70) do (
cd C:\PMON\172.18.0.%%a
date /t >> log.txt
tftp -i 172.18.0.%%a GET /pmon/daily-dmr-%yyyymmdd%.pm >> log.txt 2>&1
timeout /t 0 /NOBREAK > NUL
)
#For Pasolink NEO/c, Pasolink NEO/a
for %%a in (117, 116, 115, 114, 111, 110, 109, 108, 87, 73, 71, 69) do (
cd C:\PMON\172.18.0.%%a
date /t >> log.txt
tftp -i 172.18.0.%%a GET /pmon/daily-%yyyymmdd%.pm >> log.txt 2>&1
timeout /t 0 /NOBREAK > NUL
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
