from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'obito_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    history = db.relationship('History', backref='user', lazy=True)

class Webtoon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    cover_image = db.Column(db.String(100), nullable=False)
    chapters = db.relationship('Chapter', backref='webtoon', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content_images = db.Column(db.Text, nullable=False) # Comma separated URLs
    webtoon_id = db.Column(db.Integer, db.ForeignKey('webtoon.id'), nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='chapter', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    webtoon_id = db.Column(db.Integer, db.ForeignKey('webtoon.id'), nullable=False)
    last_read = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---

@app.route('/')
def index():
    # Recently Added Logic
    webtoons = Webtoon.query.order_by(Webtoon.created_at.desc()).all()
    
    user_history = []
    if current_user.is_authenticated:
        # User ki reading history (Recently Viewed)
        history_records = History.query.filter_by(user_id=current_user.id).order_by(History.last_read.desc()).limit(5).all()
        for rec in history_records:
            user_history.append(Webtoon.query.get(rec.webtoon_id))
            
    return render_template('index.html', webtoons=webtoons, history=user_history)

@app.route('/webtoon/<int:webtoon_id>')
def webtoon(webtoon_id):
    webtoon = Webtoon.query.get_or_404(webtoon_id)
    return render_template('webtoon.html', webtoon=webtoon)

@app.route('/read/<int:chapter_id>', methods=['GET', 'POST'])
def read(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    images = chapter.content_images.split(',')
    
    # Save History if user is logged in
    if current_user.is_authenticated:
        existing_hist = History.query.filter_by(user_id=current_user.id, webtoon_id=chapter.webtoon.id).first()
        if existing_hist:
            existing_hist.last_read = datetime.utcnow()
        else:
            new_hist = History(user_id=current_user.id, webtoon_id=chapter.webtoon.id)
            db.session.add(new_hist)
        db.session.commit()

    # Comment Logic
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        comment_text = request.form.get('comment')
        new_comment = Comment(content=comment_text, user_id=current_user.id, chapter_id=chapter.id)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('read', chapter_id=chapter.id))

    return render_template('read.html', chapter=chapter, images=images)

# --- Admin Upload System ---
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        flash("Only Obito (Admin) can access this!")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        desc = request.form.get('desc')
        # Simplified image handling (URL for now)
        cover = request.form.get('cover_url') 
        
        new_webtoon = Webtoon(title=title, description=desc, cover_image=cover)
        db.session.add(new_webtoon)
        db.session.commit()
        flash('Webtoon Added!')
        
    return render_template('admin.html')

# --- Contact Owner System ---
@app.route('/contact', methods=['POST'])
def contact():
    email = request.form.get('email')
    msg = request.form.get('message')
    # Yaha backend me email send karne ka code aayega (SMTP)
    print(f"ISSUE REPORTED BY {email}: {msg}") # Console me dikhega abhi ke liye
    flash('Message sent to Owner!')
    return redirect(url_for('index'))

# --- Login System (Mock for Demo, Google Auth requires API Keys) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Demo Login Logic (Real me Google OAuth use hoga)
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            # Auto Register for demo
            user = User(email=email, name="User", is_admin=True if email=="admin@gmail.com" else False)
            db.session.add(user)
            db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
