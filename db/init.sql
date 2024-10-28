
create table if not exists USERS (
	user_id INTEGER,
    name VARCHAR(50),
    surname VARCHAR(50),
    email VARCHAR(100) unique,
    pwd_salty VARCHAR(100),
 	constraint pk_users primary key(user_id)
)
