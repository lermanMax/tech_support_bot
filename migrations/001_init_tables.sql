DROP TABLE IF EXISTS tg_user, operator, customer, message CASCADE;

CREATE TABLE tg_user (
        tg_id int8 PRIMARY KEY,
        tg_username varchar(255) NOT NULL,
        is_banned bool NOT NULL DEFAULT FALSE
);

CREATE TABLE operator (
        operator_id int GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        tg_id int8 UNIQUE REFERENCES tg_user(tg_id) ON DELETE CASCADE
);

CREATE TABLE customer (
        customer_id int GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        tg_id int8 UNIQUE REFERENCES tg_user(tg_id) ON DELETE CASCADE,
        phone varchar(15) UNIQUE NOT NULL,
        first_name varchar(255),
        last_name varchar(255)
);

CREATE TABLE message (
        text_message_id int GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        tg_id int8 REFERENCES tg_user(tg_id) ON DELETE CASCADE,
        support_chat_message_id int8 UNIQUE,
        is_answered bool NOT NULL DEFAULT FALSE
);
