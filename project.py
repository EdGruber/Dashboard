import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import os

#Постгре
def get_db_connection():
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)
    
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT', '5432')
    )

#Проекты
class ProjectManager:
    @staticmethod
    def get_all_projects():
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM projects")
                return cursor.fetchall()
    
    @staticmethod
    def create_project(name, description):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO projects (name, description) VALUES (%s, %s)",
                    (name, description)
                )
                conn.commit()

    @staticmethod
    def update_project(project_id, name, description):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE projects SET name = %s, description = %s WHERE id = %s",
                    (name, description, project_id)
                )
                conn.commit()

    @staticmethod
    def get_project_by_id(project_id):
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT id, name, description FROM projects WHERE id = %s", (project_id,))
                return cursor.fetchone()
        
    @staticmethod
    def delete_project(project_id):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                conn.commit()
            
#Задачи
class TaskManager:
    @staticmethod
    def get_all_tasks():
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        tasks.id AS task_id,
                        tasks.title AS task_title,
                        tasks.description AS task_description,
                        users.fullname AS specialist_name,
                        statuses.name AS status_name,
                        projects.name AS project_name
                    FROM tasks
                    LEFT JOIN users ON tasks.specialist_id = users.id
                    LEFT JOIN statuses ON tasks.status_id = statuses.id
                    LEFT JOIN projects ON tasks.project_id = projects.id
                """)
                return cursor.fetchall()
            
    @staticmethod
    def get_tasks_for_specialist(specialist_id):
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        tasks.id AS task_id,
                        tasks.title AS task_title,
                        tasks.description AS task_description,
                        users.fullname AS specialist_name,
                        statuses.name AS status_name,
                        projects.name AS project_name
                    FROM tasks
                    LEFT JOIN users ON tasks.specialist_id = users.id
                    LEFT JOIN statuses ON tasks.status_id = statuses.id
                    LEFT JOIN projects ON tasks.project_id = projects.id
                    WHERE tasks.specialist_id = %s
                """, (specialist_id,))
                return cursor.fetchall()
            
    @staticmethod
    def add_comment(task_id, user_id, comment_text):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO comments (task_id, user_id, comment)
                    VALUES (%s, %s, %s)
                """, (task_id, user_id, comment_text))
                conn.commit()
    
    @staticmethod
    def get_task_by_id(task_id):
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT tasks.*, specialist.fullname AS specialist_fullname 
                    FROM tasks 
                    LEFT JOIN users AS specialist ON tasks.specialist_id = specialist.id
                    WHERE tasks.id = %s
                """, (task_id,))
                return cursor.fetchone()

    @staticmethod
    def has_tasks_for_project(project_id):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE project_id = %s", (project_id,))
                count = cursor.fetchone()[0]
                return count > 0
    
    @staticmethod
    def create_task(title, description, specialist_id, project_id):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM statuses WHERE name = 'открыта'")
                status_id = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO tasks (title, description, status_id, specialist_id, project_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (title, description, status_id, specialist_id, project_id))
                conn.commit()

    @staticmethod
    def update_task(task_id, title, description, status_id, specialist_id, project_id):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE tasks
                    SET title = %s, description = %s, status_id = %s, specialist_id = %s, project_id = %s
                    WHERE id = %s
                """, (title, description, status_id, specialist_id, project_id, task_id))
                conn.commit()

    @staticmethod
    def delete_task(task_id):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM comments WHERE task_id = %s", (task_id,))
                cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
                conn.commit()

    @staticmethod
    def get_all_statuses():
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM statuses")
                return cursor.fetchall()

#Комментарии
class CommentManager:
    @staticmethod
    def get_comments_by_task_id(task_id):
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        comments.id AS comment_id,
                        comments.comment AS comment_text,
                        users.fullname AS author_name,
                        users.position AS author_position
                    FROM comments
                    LEFT JOIN users ON comments.user_id = users.id
                    WHERE comments.task_id = %s
                    ORDER BY comments.id ASC
                """, (task_id,))
                return cursor.fetchall()

    @staticmethod
    def add_comment(task_id, user_id, comment_text):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO comments (task_id, user_id, comment)
                    VALUES (%s, %s, %s)
                """, (task_id, user_id, comment_text))
                conn.commit()
 
#Пользователи           
class UserManager:
    @staticmethod
    def get_all_users():
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, fullname, login, role, position FROM users")
                users = cursor.fetchall()
                return [user for user in users if user[0] is not None]

    @staticmethod
    def authorize_user(login, password):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT password FROM users WHERE login = %s", (login,))
                user = cursor.fetchone()
                if user and check_password_hash(user[0], password):
                    return True
                return False

    @staticmethod
    def register_user(login, password, fullname, position):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                hashed_password = generate_password_hash(password)  # Хешируем пароль
                cursor.execute("""
                    INSERT INTO users (login, password, fullname, position, role)
                    VALUES (%s, %s, %s, %s, %s)
                """, (login, hashed_password, fullname, position, 'specialist'))  # Роль по умолчанию — 'specialist'
                conn.commit()
    
    @staticmethod
    def login_user(login):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, role FROM users WHERE login = %s", (login,))
                user = cursor.fetchone()

                if user:
                    session['user_id'] = user[0]
                    session['role'] = user[1]
                    session['login'] = login

    @staticmethod
    def logout_user():
        session.clear()
    
    @staticmethod
    def get_all_users():
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT id, fullname, login, role, position FROM users")
                return cursor.fetchall()

    @staticmethod
    def update_user_role(user_id, new_role):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET role = %s
                    WHERE id = %s
                """, (new_role, user_id))
                conn.commit()

    @staticmethod
    def update_user_password(user_id, new_password):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                hashed_password = generate_password_hash(new_password)  # Хешируем новый пароль
                cursor.execute("""
                    UPDATE users
                    SET password = %s
                    WHERE id = %s
                """, (hashed_password, user_id))
                conn.commit()

    @staticmethod
    def update_user_fullname(user_id, new_fullname):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET fullname = %s
                    WHERE id = %s
                """, (new_fullname, user_id))
                conn.commit()
    
    @staticmethod
    def update_user_position(user_id, new_position):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET position = %s
                    WHERE id = %s
                """, (new_position, user_id))
                conn.commit()
    
    @staticmethod
    def get_user_by_id(user_id):
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT id, fullname, login, role, position FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if user:
                    return user
                return None
            
class StatusManager:
    @staticmethod
    def get_all_statuses():
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT id, name FROM statuses")
                return cursor.fetchall()
