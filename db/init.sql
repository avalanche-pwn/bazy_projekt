create table if not exists users (
    user_id SERIAL,
    name VARCHAR(50) not null,
    surname VARCHAR(50) not null,
    email VARCHAR(100) unique not null,
    salty_hash VARCHAR(100) not null,
    is_admin BOOLEAN default false,
    creation_date TIMESTAMP not null default CURRENT_TIMESTAMP,
    constraint pk_users primary key(user_id)
);
create unique index on users (email);

create table if not exists categories (
    cat_id SERIAL primary key,
    name VARCHAR(50) not null,
    parent_cat_id INT default null
);

alter table categories drop constraint if exists parent;
alter table categories add constraint parent foreign key (parent_cat_id)
    references categories(cat_id);

DO $$DECLARE new_id INT;
BEGIN
    insert into categories (name) values ('Wszystko') returning cat_id INTO new_id;
    insert into categories (name, parent_cat_id) values ('Broń', new_id);
    insert into categories (name, parent_cat_id) values ('Amunicja', new_id);
END $$;
    

create table if not exists equipment (
    manufacturer_code VARCHAR(50) primary key,
    image_file VARCHAR(150) not null,
    name VARCHAR(50) not null,
    model VARCHAR(50) not null,
    quantity INTEGER,
    caliber DECIMAL(6, 2) not null,
    type INTEGER references categories(cat_id)
);

create table if not exists ammunition (
    manufacturer_code VARCHAR(50) references equipment(manufacturer_code),
    rim_or_centerfire VARCHAR(20) not null,
    weight INTEGER not null,
    price_per_round DECIMAL(6, 2) not null,
    constraint pk_ammunition primary key(manufacturer_code)
);
create table if not exists guns (
    manufacturer_code VARCHAR(50) references equipment(manufacturer_code),
    price_per_hour DECIMAL(6, 2) not null,
    constraint pk_guns primary key(manufacturer_code)
);
create table if not exists reservations (
    reservation_id SERIAL primary key,
    start_time TIMESTAMP not null,
    end_time TIMESTAMP not null,
    constraint reservation_time check(end_time - start_time < interval '2 hours'),
    user_id INT references users(user_id) NOT NULL,
    status VARCHAR(50) not null default 'reserved'
);


create table if not exists reserved_items (
    reservation_id INTEGER NOT NULL,
    manufacturer_code VARCHAR(50) references equipment(manufacturer_code) NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (reservation_id) references reservations(reservation_id) ON DELETE CASCADE
);
create index reservation_id on reserved_items (reservation_id);


grant select, insert, update, delete on users to backend_user;
grant select, insert, update, delete on reservations to backend_user;
grant select, insert, update, delete on reserved_items to backend_user;
grant select, insert, update, delete on equipment to backend_user;
grant select, insert, update, delete on users to backend_user;
grant select, insert, update, delete on categories to backend_user;
grant select, insert, update, delete on ammunition to backend_user;
grant select, insert, update, delete on guns to backend_user;
grant usage, select on users_user_id_seq to backend_user;
grant usage, select on categories_cat_id_seq to backend_user;
grant usage, select on reservations_reservation_id_seq to backend_user;
