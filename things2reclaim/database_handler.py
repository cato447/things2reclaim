import sqlite3


class UploadedTasksDB:
    def __init__(self, filename):
        self.conn: sqlite3.Connection = sqlite3.connect(filename)
        self.__create_tables()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.conn.close()

    def __create_tables(self):
        sql_statements = [
            """CREATE TABLE IF NOT EXISTS uploaded_tasks (
                id integer primary key,
                things_task_id varchar(36) NOT NULL UNIQUE
            )
            """
        ]
        cursor = self.conn.cursor()
        for statement in sql_statements:
            cursor.execute(statement)

        self.conn.commit()

    def add_uploaded_task(self, task_id: str):
        insert_statement = "INSERT INTO uploaded_tasks(things_task_id) VALUES(?)"
        cursor = self.conn.cursor()
        cursor.execute(insert_statement, [task_id])
        self.conn.commit()

    def get_all_uploaded_tasks(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM uploaded_tasks")
        rows = cursor.fetchall()
        return [things_id for (_, things_id) in rows]

    def remove_uploaded_task(self, task_id: str):
        delete_statement = "DELETE FROM uploaded_tasks WHERE things_task_id = ?"
        cursor = self.conn.cursor()
        cursor.execute(delete_statement, (task_id,))
        self.conn.commit()
