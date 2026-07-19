@echo off

chcp 65001

cd "c:\Program Files\SNMPc Network Manager"

date /t > %d%
time /t > %t%

snmpget -b -n 2697 1.3.6.1.4.1.12148.9.3.2 > %dc%

echo %d%, %t%, %dc% >> 6176_FP2_DC.txt

