@echo off
chcp 65001

set r=66

> 20260301.txt 2>&1 (
	cd C:\PMON\172.18.0.%r% 
	echo Connect 172.18.0.%r%
	tftp -i 172.18.0.%r% GET /pmon/daily-dmr-20260301.pm
	tftp -i 172.18.0.%r% GET /pmon/daily-20260301.pm

	echo Download complete
)


@pause