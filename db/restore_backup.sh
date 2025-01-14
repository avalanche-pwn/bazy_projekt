#!/bin/env bash

# Variables
BACKUP_FILE=$1
DB_NAME=docker
CONTAINER_NAME=postgres
echo -n User: 
read DB_USER
echo
# Run Command
echo -n Password: 
read -s DB_PASSWORD
echo

# Restore the database
cat $BACKUP_FILE | sudo docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME

echo "Database restored from: $BACKUP_FILE"
