#!/bin/env bash

# Variables
BACKUP_DIR=./backups
DB_NAME=docker
echo -n User: 
read DB_USER
echo
# Run Command
echo -n Password: 
read -s DB_PASSWORD
echo
# Run Command
CONTAINER_NAME=postgres

# Get current date and time for backup file
TIMESTAMP=$(date +"%F_%T")
BACKUP_FILE=$BACKUP_DIR/backup_$DB_NAME_$TIMESTAMP.sql

# Run pg_dump inside the PostgreSQL container
sudo docker exec -t $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME > $BACKUP_FILE

echo "Backup completed: $BACKUP_FILE"
