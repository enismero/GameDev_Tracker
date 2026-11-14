CREATE DATABASE IF NOT EXISTS gamedev_tracker
# database oluştur varsa oluşturma
CHARACTER SET utf8mb4 #tr karakterleri destekle
COLLATE utf8mb4_unicode_ci; #büyük küçük harfe duyarsız 

USE gamedev_tracker; #sonraki sorgular burda çalışıcak

CREATE TABLE users(
	user_id int AUTO_INCREMENT primary key,
    username varchar(50) not null unique,
    display_name varchar(100) not null,
    password_hash varchar(255) not null,
    created_at datetime not null default current_timestamp
	) engine= InnoDB;
DESCRIBE users;

create table tasks (
	task_id int AUTO_INCREMENT primary key,
    title varchar(150) not null,
    description text,
    
    status enum(
		"todo","in_progress","testing","done"
    ) not null default "todo",
    
    priority enum(
    "low","medium","high"
    ) not null default "medium",
    
    created_by int not null,
    assigned_to int,
    
    created_at datetime not null default current_timestamp,
    updated_at datetime not null default current_timestamp on update current_timestamp,
    
    constraint fk_task_creator
		foreign key(created_by)
        references users(user_id)
        on delete restrict,
        
	constraint fk_task_assignee
		foreign key(assigned_to)
        references users(user_id)
        on delete set null
) engine=InnoDB;
USE gamedev_tracker;
SHOW TABLES;
DESCRIBE tasks;