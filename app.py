from flask import Flask, render_template, request, redirect, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key"
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# SQLite URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'database.db')
db = SQLAlchemy(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))
    profile_pic = db.Column(db.String(120))  # stores filename
    comments = db.relationship('Comment', back_populates='user')


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    likes = db.relationship('Like', backref='post')
    comments = db.relationship('Comment', back_populates='post')


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(300))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='comments')
    post = db.relationship('Post', back_populates='comments')


# --- ROUTES ---
@app.route('/')
def home():
    posts = Post.query.all()
    return render_template("index.html", posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        profile_pic = None
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_pic = filename

        new_user = User(username=username, password=password, profile_pic=profile_pic)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect('/')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/post', methods=['POST'])
def post():
    content = request.form['content']
    user_id = session.get('user_id')
    if user_id:
        new_post = Post(content=content, user_id=user_id)
        db.session.add(new_post)
        db.session.commit()
    return redirect('/')


@app.route('/like/<int:post_id>')
def like(post_id):
    user_id = session.get('user_id')
    if user_id:
        like = Like(user_id=user_id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
    return redirect('/')


@app.route('/comment/<int:post_id>', methods=['POST'])
def comment(post_id):
    user_id = session.get('user_id')
    if user_id:
        content = request.form['content']
        new_comment = Comment(content=content, user_id=user_id, post_id=post_id)
        db.session.add(new_comment)
        db.session.commit()
    return redirect('/')


@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return "User not found", 404

    posts = Post.query.filter_by(user_id=user_id).all()
    total_likes = sum(len(post.likes) for post in posts)
    total_comments = sum(len(post.comments) for post in posts)

    return render_template(
        'profile.html',
        user=user,
        posts=posts,
        total_likes=total_likes,
        total_comments=total_comments
    )


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)