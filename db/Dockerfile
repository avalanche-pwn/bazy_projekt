
FROM postgres:latest
ADD create_user.sh /docker-entrypoint-initdb.d/1_create_user.sh
ADD init.sql /docker-entrypoint-initdb.d/2_create_db.sql
RUN mkdir /run/secrets
RUN chown postgres /run/secrets
RUN chmod a+r /docker-entrypoint-initdb.d/*
