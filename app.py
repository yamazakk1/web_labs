import random
import re
from flask import Flask, render_template, request, make_response, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from faker import Faker

fake = Faker('ru_RU')

app = Flask(__name__)
application = app

app.config['SECRET_KEY'] = 'your-secret-key-here-change-it-in-production'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  
login_manager.login_message = 'Для доступа к этой странице необходимо авторизоваться.' 
login_manager.login_message_category = 'warning'

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

users = {
    '1': User('1', 'user', 'qwerty')  
}

def get_user(user_id):
    return users.get(str(user_id))

def authenticate_user(username, password):
    for user in users.values():
        if user.username == username and user.password == password:
            return user
    return None

@login_manager.user_loader
def load_user(user_id):
    return get_user(user_id)


images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
              '2d2ab7df-cdbc-48a8-a936-35bba702def5',
              '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
              'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
              'cab5b7f2-774e-4884-a200-0c0180fa777f']

def generate_comments(replies=True):
    comments = []
    for i in range(random.randint(1, 3)):
        comment = { 'author': fake.name(), 'text': fake.text() }
        if replies:
            comment['replies'] = generate_comments(replies=False)
        comments.append(comment)
    return comments

def generate_post(i):
    return {
        'title': fake.word(),
        'text': fake.paragraph(nb_sentences=100),
        'author': fake.name(),
        'date': fake.date_time_between(start_date='-2y', end_date='now'),
        'image_id': f'{images_ids[i]}.jpg',
        'comments': generate_comments()
    }

posts_list = sorted([generate_post(i) for i in range(5)], key=lambda p: p['date'], reverse=True)

def validate_phone(phone):

    cleaned = re.sub(r'[^\d+]', '', phone)

    invalid_chars = re.findall(r'[^\d\s\(\)\-\.\+]', phone)
    if invalid_chars:
        return False, None, "Недопустимый ввод. В номере телефона встречаются недопустимые символы."

    digits = re.sub(r'\D', '', phone)
    digit_count = len(digits)

    expected_digits = None
    if phone.startswith('+7') or phone.startswith('8'):
        expected_digits = 11
    else:
        expected_digits = 10

    if digit_count != expected_digits:
        return False, None, f"Недопустимый ввод. Неверное количество цифр. (Ожидается {expected_digits}, получено {digit_count})"

    if digit_count == 11:
        number_digits = digits[-10:]
    else:
        number_digits = digits
    
    formatted = f"8-{number_digits[0:3]}-{number_digits[3:6]}-{number_digits[6:8]}-{number_digits[8:10]}"
    
    return True, formatted, None

@app.route('/counter')
def counter():

    visit_count = session.get('visit_count', 0)
    visit_count += 1
    session['visit_count'] = visit_count
    
    return render_template('counter.html', title='Счетчик посещений', visit_count=visit_count)

@app.route('/login', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        flash('Вы уже авторизованы!', 'info')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'  
        
        user = authenticate_user(username, password)
        
        if user:
            login_user(user, remember=remember)
            flash(f'Добро пожаловать, {username}! Вы успешно вошли в систему.', 'success')

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль.', 'danger')
    
    return render_template('login.html', title='Вход')

@app.route('/logout')
@login_required
def logout():

    logout_user()
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html', title='Секретная страница')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/posts')
def posts():
    return render_template('posts.html', title='Посты', posts=posts_list)

@app.route('/posts/<int:index>')
def post(index):
    p = posts_list[index]
    return render_template('post.html', title=p['title'], post=p)

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')

@app.route('/request-info')
def request_info():
    url_params = request.args.to_dict()
    headers = dict(request.headers)
    cookies = request.cookies.to_dict()
    
    return render_template('request_info.html', 
                         title='Информация о запросе',
                         url_params=url_params,
                         headers=headers,
                         cookies=cookies)

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    auth_data = None
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        auth_data = {'username': username, 'password': password}
        
        response = make_response(render_template('auth.html', 
                                                title='Авторизация',
                                                auth_data=auth_data))
        response.set_cookie('username', username, max_age=3600)
        return response
    
    return render_template('auth.html', title='Авторизация', auth_data=auth_data)

@app.route('/phone', methods=['GET', 'POST'])
def phone():
    result = None
    error = None
    phone_number = ''
    
    if request.method == 'POST':
        phone_number = request.form.get('phone', '')
        is_valid, formatted, error_msg = validate_phone(phone_number)
        
        if is_valid:
            result = formatted
        else:
            error = error_msg
    
    return render_template('phone.html', 
                         title='Проверка номера телефона',
                         phone_number=phone_number,
                         result=result,
                         error=error)

if __name__ == '__main__':
    app.run(debug=True)