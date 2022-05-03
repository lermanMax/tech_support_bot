import psycopg2
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT

db_config = {'host': DB_HOST,
             'dbname': DB_NAME,
             'user': DB_USER,
             'password': DB_PASS,
             'port': DB_PORT}

not_found_err = NameError('db: tg_user not found')


class MarketBotData:
    @staticmethod
    def add_tg_user(tg_id: int, tg_username: str) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (tg_id, tg_username)
            insert_script = '''INSERT INTO tg_user (tg_id, tg_username)
                                VALUES (%s, %s)
                                ON CONFLICT (tg_id)
                                DO UPDATE
                                SET tg_username = EXCLUDED.tg_username;'''
            cursor.execute(insert_script, insert_values)
        connection.commit()
        connection.close()

    @staticmethod
    def does_user_exist(tg_id: int) -> bool:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''
                    SELECT exists(
                       SELECT tg_id
                       FROM tg_user
                       WHERE tg_id = %s);'''
            cursor.execute(select_script, (tg_id,))
            exists, = cursor.fetchone()
        connection.commit()
        connection.close()
        return exists

    @staticmethod
    def add_operator(tg_id: int) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (tg_id,)
            insert_script = '''INSERT INTO operator (tg_id) VALUES (%s)
                                ON CONFLICT (tg_id) DO NOTHING;'''
            cursor.execute(insert_script, insert_values)
        connection.commit()
        connection.close()

    @staticmethod
    def add_customer(tg_id: int, phone: str) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (tg_id, phone)
            insert_script = '''INSERT INTO customer (tg_id, phone)
                                VALUES (%s, %s)
                                ON CONFLICT (tg_id) DO NOTHING;'''
            cursor.execute(insert_script, insert_values)
        connection.commit()
        connection.close()

    @staticmethod
    def get_customer_list() -> list:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_user.tg_id FROM tg_user
                                INNER JOIN customer 
                                ON tg_user.tg_id = customer.tg_id
                                WHERE tg_user.is_banned = FALSE;'''
            cursor.execute(select_script)
            try:
                id_list = cursor.fetchall()
            except TypeError:
                id_list = []
        connection.commit()
        connection.close()
        return [id_tuple[0] for id_tuple in id_list]

    @staticmethod
    def get_tg_users() -> list:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_id FROM tg_user
                                WHERE is_banned = FALSE
                                EXCEPT SELECT tg_id FROM customer;'''
            cursor.execute(select_script)
            try:
                id_list = cursor.fetchall()
            except TypeError:
                id_list = []
        connection.commit()
        connection.close()
        return [id_tuple[0] for id_tuple in id_list]

    @staticmethod
    def get_ban_list() -> list:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_id FROM tg_user
                                WHERE is_banned = TRUE;'''
            cursor.execute(select_script)
            try:
                id_list = cursor.fetchall()
            except TypeError:
                id_list = []
        connection.commit()
        connection.close()
        return [id_tuple[0] for id_tuple in id_list]


class TgUserData:
    def __init__(self, tg_id: int):
        self.tg_id = tg_id

        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_username, is_banned
                                FROM tg_user 
                                WHERE tg_id = %s;'''
            cursor.execute(select_script, (tg_id,))
            select_username, is_banned = cursor.fetchone()
        connection.commit()
        connection.close()

        self.tg_username = select_username
        self.is_banned = is_banned

    def get_tg_id(self) -> int:
        return self.tg_id

    def get_tg_username(self) -> str:
        return self.tg_username

    def is_banned(self) -> bool:
        return self.is_banned


class OperatorData:

    def __init__(self, operator_id: int):
        self.operator_id = operator_id

        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_id FROM operator 
                                WHERE operator_id = %s;'''
            cursor.execute(select_script, (operator_id,))
            tg_id, = cursor.fetchone()
        connection.commit()
        connection.close()

        self.tg_id = tg_id

    def get_tg_id(self):
        return self.tg_id

    @staticmethod
    def ban(tg_id: int) -> None:
        if MarketBotData.does_user_exist(tg_id):
            connection = psycopg2.connect(**db_config)
            with connection.cursor() as cursor:
                update_script = '''UPDATE tg_user
                                    SET is_banned = TRUE
                                    WHERE tg_id = %s
                                    RETURNING tg_id;'''
                cursor.execute(update_script, (tg_id,))
            connection.commit()
            connection.close()
        else:
            raise not_found_err

    @staticmethod
    def unban(tg_id: int) -> None:
        if MarketBotData.does_user_exist(tg_id):
            connection = psycopg2.connect(**db_config)
            with connection.cursor() as cursor:
                update_script = '''UPDATE tg_user
                                    SET is_banned = FALSE
                                    WHERE tg_id = %s
                                    RETURNING tg_id;'''
                cursor.execute(update_script, (tg_id,))
            connection.commit()
            connection.close()
        else:
            raise not_found_err


class CustomerData:
    def __init__(self, customer_id: int):
        self.customer_id = customer_id

        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_id, phone, first_name, last_name
                                FROM customer
                                WHERE customer_id = %s;'''
            cursor.execute(select_script, (customer_id,))
            tg_id, phone, first_name, last_name = cursor.fetchone()
        connection.commit()
        connection.close()

        self.tg_id = tg_id
        self.phone = phone
        self.first_name = first_name
        self.last_name = last_name

    def get_tg_id(self) -> int:
        return self.tg_id

    def get_phone(self) -> str:
        return self.phone

    def first_name(self) -> str:
        return self.first_name

    def last_name(self) -> str:
        return self.last_name

    # надо? exceptions?
    def change_phone(self, new_phone: str) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (new_phone, self.customer_id)
            update_script = '''UPDATE customer
                                SET phone = %s
                                WHERE customer_id = %s;'''
            cursor.execute(update_script, insert_values)
        connection.commit()
        connection.close()

    # exceptions?
    def change_first_name(self, new_first_name: str) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (new_first_name, self.customer_id)
            update_script = '''UPDATE customer
                                SET first_name = %s
                                WHERE customer_id = %s;'''
            cursor.execute(update_script, insert_values)
        connection.commit()
        connection.close()

    # exceptions?
    def change_last_name(self, new_last_name: str) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (new_last_name, self.customer_id)
            update_script = '''UPDATE customer
                                SET last_name = %s
                                WHERE customer_id = %s;'''
            cursor.execute(update_script, insert_values)
        connection.commit()
        connection.close()
