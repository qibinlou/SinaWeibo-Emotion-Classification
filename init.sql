-- SQL for creating tables:

create table settings (id varchar(50) not null, value varchar(1000) not null, primary key(id));

create table users (id varchar(200) not null, name varchar(50) not null, image_url varchar(1000) not null, statuses_count bigint not null, friends_count bigint not null, followers_count bigint not null, verified bool not null, verified_type int not null, auth_token varchar(2000) not null, expired_time real not null, primary key(id));
