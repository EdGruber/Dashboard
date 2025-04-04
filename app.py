from flask import Flask, render_template, request, redirect, session, abort
from db import init_db
from project import ProjectManager, TaskManager, UserManager, StatusManager, CommentManager
from functools import wraps
import psycopg2


app = Flask(__name__)
app.secret_key = 'your_secret_key' 

init_db()

#Постгре
def get_db_connection():
    connection = psycopg2.connect(
        dbname="project_management",
        user="postgres",
        password="eg",
        host="localhost",  
        port="5432"       
    )
    return connection

#Ограничение доступа
def role_required(roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                abort(403)  
            return func(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/home')
def home():
    if 'login' not in session:
        return redirect('/login')
    
    user_id = session.get('user_id')  
    user = UserManager.get_user_by_id(user_id)

    return render_template('home.html', fullname=user['fullname'], role=user['role'], position=user['position'])

#Авторизация
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']

        if UserManager.authorize_user(login, password): 
            UserManager.login_user(login) 
            return redirect('/') 
        else:
            message = "Неверный логин или пароль."
            return render_template('login.html', message=message)

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        fullname = request.form['fullname'] 
        position = request.form['position'] 

        try:
            UserManager.register_user(login, password, fullname, position) 
            message = "Вы успешно зарегистрировались. Теперь вы можете войти в систему."
            return render_template('registration.html', message=message)
        except Exception as e:
            message = str(e)
            return render_template('registration.html', message=message)

    return render_template('registration.html')

@app.route('/logout')
def logout():
    UserManager.logout_user() 
    return redirect('/login') 

@app.route('/')
def index():
    if 'login' not in session:
        return redirect('/login')

    return redirect('/home') 

#Пользователи
@app.route('/manage_users', methods=['GET', 'POST'])
@role_required(['admin'])
def manage_users():
    if 'login' not in session or session.get('role') not in ['admin']:
        return redirect('/login')

    users = UserManager.get_all_users()
    return render_template('manage_users.html', users=users)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@role_required(['admin'])
def edit_user(user_id):
    if 'login' not in session:
        return redirect('/login')

    user = UserManager.get_user_by_id(user_id) 

    if request.method == 'POST':
        # Обновление роли
        new_role = request.form['role']
        UserManager.update_user_role(user_id, new_role)

        # Обновление ФИО 
        change_fullname = request.form.get('change_fullname')
        if change_fullname:
            new_fullname = request.form.get('new_fullname')
            if new_fullname:
                UserManager.update_user_fullname(user_id, new_fullname)

         # Обновление должности 
        change_position = request.form.get('change_position')
        if change_position:
            new_position = request.form.get('new_position')
            if new_position:
                UserManager.update_user_position(user_id, new_position)

        # Обновление пароля
        change_password = request.form.get('change_password')
        if change_password:
            new_password = request.form.get('new_password')
            if new_password:
                UserManager.update_user_password(user_id, new_password)

        return redirect('/manage_users')

    return render_template('edit_user.html', user=user)

#Проекты
@app.route('/create_project', methods=['GET', 'POST'])
@role_required(['admin', 'project_manager'])
def create_project():
    if 'login' not in session:
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')

        ProjectManager.create_project(name, description)
        return redirect('/manage_projects')

    return render_template('create_project.html')

@app.route('/manage_projects', methods=['GET', 'POST'])
@role_required(['admin', 'project_manager'])
def manage_projects():
    if 'login' not in session:
        return redirect('/home')

    role = session.get('role')
    projects = ProjectManager.get_all_projects() 
    return render_template('manage_projects.html', projects=projects, role=role)

@app.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
@role_required(['admin', 'project_manager'])
def edit_project(project_id):
    if 'login' not in session:
        return redirect('/login')

    project = ProjectManager.get_project_by_id(project_id)

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        ProjectManager.update_project(project_id, name, description)
        return redirect('/manage_projects')

    return render_template('edit_project.html', project=project)

@app.route('/delete_project/<int:project_id>', methods=['POST'])
@role_required(['admin', 'project_manager'])
def delete_project(project_id):
    if TaskManager.has_tasks_for_project(project_id):
        error_message = "Невозможно удалить проект, так как к нему привязаны задачи."
        projects = ProjectManager.get_all_projects()
        return render_template('manage_projects.html', projects=projects, error_message=error_message)

    ProjectManager.delete_project(project_id)
    return redirect('/manage_projects')

#Задачи
@app.route('/create_task', methods=['GET', 'POST'])
@role_required(['admin', 'project_manager'])
def create_task():
    if 'login' not in session:
        return redirect('/login')

    users = UserManager.get_all_users()
    projects = ProjectManager.get_all_projects()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        specialist_id = request.form['specialist_id']
        project_id = request.form['project_id']

        TaskManager.create_task(title, description, specialist_id, project_id)
        return redirect('/manage_tasks')

    return render_template('create_task.html', users=users, projects=projects)

@app.route('/manage_tasks', methods=['GET', 'POST'])
def manage_tasks():
    if 'login' not in session:
        return redirect('/login')

    role = session.get('role')
    user_id = session.get('user_id')
    if role == 'specialist':
        tasks = TaskManager.get_tasks_for_specialist(user_id) 
    else:
        tasks = TaskManager.get_all_tasks() 
    users = UserManager.get_all_users()
    projects = ProjectManager.get_all_projects()
    statuses = StatusManager.get_all_statuses()

    return render_template('manage_tasks.html', tasks=tasks, users=users, projects=projects, role=role, statuses=statuses)

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@role_required(['admin', 'project_manager', 'specialist'])
def edit_task(task_id):
    if 'login' not in session:
        return redirect('/login')

    task = TaskManager.get_task_by_id(task_id)
    statuses = StatusManager.get_all_statuses()
    users = UserManager.get_all_users()
    projects = ProjectManager.get_all_projects()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', "")
        status_id = request.form['status_id']
        specialist_id = request.form.get('specialist_id', None)
        project_id = request.form['project_id']
        
        TaskManager.update_task(task_id, title, description, status_id, specialist_id, project_id)


        return redirect('/manage_tasks')

    return render_template('edit_task.html', task=task, statuses=statuses, users=users, projects=projects)

@app.route('/delete_task/<int:task_id>', methods=['POST'])
@role_required(['admin', 'project_manager'])
def delete_task(task_id):
    TaskManager.delete_task(task_id)
    return redirect('/manage_tasks')

#Комментарии
@app.route('/task/<int:task_id>/view_task', methods=['GET', 'POST'])
def view_task(task_id):
    if 'login' not in session:
        return redirect('/login')

    user_id = session.get('user_id') 
    role = session.get('role')

    task = TaskManager.get_task_by_id(task_id)
    statuses = StatusManager.get_all_statuses()
    users = UserManager.get_all_users()
    projects = ProjectManager.get_all_projects()
    
    comments = CommentManager.get_comments_by_task_id(task_id)

    if request.method == 'POST':
        comment_text = request.form['comment']
        if comment_text.strip():
            CommentManager.add_comment(task_id, user_id, comment_text)
        return redirect(f'/task/{task_id}/view_task')

    return render_template('view_task.html', task=task, comments=comments, role=role, statuses=statuses, users=users, projects=projects)

if __name__ == "__main__":
    app.run(debug=True)