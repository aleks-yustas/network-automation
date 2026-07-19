@echo off

set d1=13
set d2=15
set m=11
set y=2020

for %%a in (107, 106, 105, 104, 103, 102, 101, 100, 99, 96, 95, 94, 93, 92, 91, 90, 89, 88, 86, 85, 84, 83, 82, 81, 80, 79, 78, 70) do (
cd C:\PMON\172.18.0.%%a
echo Connect 172.18.0.%%a
for /L %%d in (%d1%,1,%d2%) do (
if %%d LEQ 9 (
tftp -i 172.18.0.%%a GET /pmon/daily-dmr-%y%%m%0%%d.pm & timeout /t 0 | find "успешная") else (
tftp -i 172.18.0.%%a GET /pmon/daily-dmr-%y%%m%%%d.pm & timeout /t 0 | find "успешная"
)
)
)


for %%a in (117, 116, 115, 114, 111, 110, 109, 108, 87, 73, 71, 69) do (
cd C:\PMON\172.18.0.%%a
echo Connect 172.18.0.%%a
for /L %%d in (%d1%,1,%d2%) do (
if %%d LEQ 9 (
tftp -i 172.18.0.%%a GET /pmon/daily-%y%%m%0%%d.pm & timeout /t 0 | find "успешная") else (
tftp -i 172.18.0.%%a GET /pmon/daily-%y%%m%%%d.pm & timeout /t 0 | find "успешная"
)
)
)

echo Download complete

@pause