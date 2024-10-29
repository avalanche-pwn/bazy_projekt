#!/bin/bash
psql -U $(cat /run/secrets/db_user) -d docker -c "CREATE USER backend_user WITH PASSWORD '$(cat /run/secrets/db_passwd_back)';"
