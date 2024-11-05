
FROM postgres:latest
ADD create_user.sh /docker-entrypoint-initdb.d/1_create_user.sh
ADD init.sql /docker-entrypoint-initdb.d/2_create_db.sql
ADD delete_pwd.sh /docker-entrypoint-initdb.d/3_delete_pwd.sh
ADD pwd.txt /run/secrets/db_passwd
ADD user.txt /run/secrets/db_user
ADD pwd_back.txt /run/secrets/db_passwd_back
RUN chown postgres /run/secrets
RUN chmod a+r /docker-entrypoint-initdb.d/*
