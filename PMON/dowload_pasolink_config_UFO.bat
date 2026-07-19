@echo off

chcp 65001 > NUL
echo !!!! -=== OKHO HE 3AKPbIBATb ===- !!!!     

set d=%date:~0,2%
set m=%date:~3,2%
set y=%date:~6,4%

for %%a in (107, 106, 105, 104, 103, 102, 101, 100, 99, 96, 95, 94, 93, 92, 91, 90, 89, 88, 86, 85, 84, 83, 82, 81, 80, 79, 78, 70) do (
md C:\Pasolink_config\%d%_%m%_%y%\172.18.0.%%a
cd C:\Pasolink_config\%d%_%m%_%y%\172.18.0.%%a
for %%f in ("/cfg/pn_network.cfg", "/cfg/pn_mib.cfg", "/cfg/equip/pn_equip.cfg", "/softkey/current/License0001.key", "/softkey/current/License0002.key", "/softkey/current/License0003.key", "/softkey/current/License0004.key") do (
tftp -i 172.18.0.%%a GET %%f
timeout /t 1 /NOBREAK > NUL
)
)

for %%a in (117, 116, 115, 114, 111, 110, 109, 108, 87, 73, 71, 69) do (
md C:\Pasolink_config\%d%_%m%_%y%\172.18.0.%%a
cd C:\Pasolink_config\%d%_%m%_%y%\172.18.0.%%a
for %%f in ("/cfg/pn_network.cfg", "/cfg/pn_mib.cfg", "/cfg/equip/pn_equip.cfg") do (
tftp -i 172.18.0.%%a GET %%f
timeout /t 1 /NOBREAK > NUL
)
)


for %%a in (87, 69) do (
md C:\Pasolink_config\%d%_%m%_%y%\172.18.0.%%a
cd C:\Pasolink_config\%d%_%m%_%y%\172.18.0.%%a
for %%f in ("/cfg/pn_network.cfg", "/cfg/pn_mib.cfg") do (
tftp -i 172.18.0.%%a GET %%f
timeout /t 1 /NOBREAK > NUL
)
)

exit /b