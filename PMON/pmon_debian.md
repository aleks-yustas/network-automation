Скрипт: `fetch_pm.sh`

```bash
#!/bin/bash

# --- Конфигурация ---
BASE_DIR="/home/user/pmon"
LOG_FILE="$BASE_DIR/download_log.txt"
# Дата за вчера (формат YYYYMMDD)
YESTERDAY=$(date -d "yesterday" +%Y%m%d)

# Списки IP-адресов
GROUP_DMR=(107 106 105 104 103 102 101 100 99 96 95 94 93 92 91 90 89 88 86 85 84 83 82 81 80 79 78 70)
GROUP_STD=(117 116 115 114 111 110 109 108 87 73 71 69)

# Функция для загрузки
fetch_file() {
    local ip="172.18.0.$1"
    local filename=$2
    local target_dir="$BASE_DIR/$ip"

    # Создаем директорию, если её нет
    mkdir -p "$target_dir"
    cd "$target_dir" || return

    # Загрузка через tftp (используем tftp-hpa или atftp)
    # -g (get), -r (remote file), -l (local file)
    tftp -g -r "$filename" -l "$filename" "$ip" 2>/dev/null

    if [ $? -eq 0 ]; then
        echo "[$(date '+%H:%M:%S')] OK: $ip -> $filename" >> "$LOG_FILE"
    else
        echo "[$(date '+%H:%M:%S')] FAIL: $ip -> $filename" >> "$LOG_FILE"
    fi
}

# --- Начало работы ---
echo "--- Запуск: $(date '+%Y-%m-%d %H:%M:%S') ---" >> "$LOG_FILE"

# Обработка группы DMR
for last_octet in "${GROUP_DMR[@]}"; do
    fetch_file "$last_octet" "pmon/daily-dmr-$YESTERDAY.pm"
done

# Обработка стандартной группы
for last_octet in "${GROUP_STD[@]}"; do
    fetch_file "$last_octet" "pmon/daily-$YESTERDAY.pm"
done

echo "--- Завершено ---" >> "$LOG_FILE"
```

Как подготовить систему
 * Установите tftp-клиент:
   В Debian по умолчанию его может не быть. Установите стандартный клиент:

```bash
sudo apt update && sudo apt install tftp-hpa -y
```

 * Настройте права доступа:
   Сохраните код в файл, например /home/user/fetch_pm.sh, и сделайте его исполняемым:

```bash
chmod +x /home/user/fetch_pm.sh
```

 * Проверьте пути:
   Убедитесь, что переменная BASE_DIR в скрипте указывает на существующую папку, где у вашего пользователя есть права на запись.
Настройка расписания (Cron)
Чтобы скрипт запускался автоматически каждый день (например, в 03:00 утра), добавьте задачу в планировщик:
 * Введите команду: `crontab -e`
 * В конец файла добавьте строку: `0 3 * * * /home/user/fetch_pm.sh`

