
FROM postgres:latest
ADD init.sql /docker-entrypoint-initdb.d
ADD pwd.txt /run/secrets/db_passwd
ADD user.txt /run/secrets/db_user
RUN chmod a+r /docker-entrypoint-initdb.d/*
