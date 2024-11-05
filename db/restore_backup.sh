#!/bin/bash

# Parametry wejściowe
BACKUP_FILE=$1  # Ścieżka do pliku backupu
DB_NAME="docker"  # Nazwa bazy danych, na której przywracamy
DB_USER="postgres"  # Główny użytkownik bazy danych
DB_HOST="localhost"  # Host, może być 'localhost' lub nazwa kontenera
DB_PORT="5432"  # Port PostgreSQL

# Sprawdzanie, czy plik backupu został podany jako argument
if [ -z "$BACKUP_FILE" ]; then
    echo "Użycie: $0 <ścieżka_do_pliku_backup.sql>"
    exit 1
fi

# Sprawdzanie, czy plik backupu istnieje
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Plik backupu $BACKUP_FILE nie istnieje."
    exit 1
fi

# Przywracanie bazy danych z backupu
echo "Przywracanie bazy danych $DB_NAME z pliku $BACKUP_FILE..."
PGPASSWORD=$(cat /run/secrets/db_passwd) psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME < "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Przywracanie bazy danych zakończone sukcesem."
else
    echo "Błąd podczas przywracania bazy danych."
fi
