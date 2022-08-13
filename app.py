from flask import Flask,render_template,request,redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from datetime import datetime
from flask_admin.contrib.sqla import ModelView
import os
from flask_login import LoginManager, UserMixin,login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///postdata.db'
app.config['SECRET_KEY'] = os.urandom(24) #セッション情報を暗号化するための設定

page_contents_num = 10

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

class Title(db.Model):
    __tablename__ = 'Title_table'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(30), nullable=False)
    detail = db.Column(db.Text(255), nullable=False)
    post_date = db.Column(db.DateTime, nullable=False ,default=datetime.now)

class Thread(db.Model):
  __tablename__ = 'Thread_table'
  id = db.Column(db.Integer, primary_key=True)
  Title_id =db.Column(db.Integer)
  user = db.Column(db.String(20), nullable=False)
  title = db.Column(db.String(30), nullable=False)
  detail = db.Column(db.Text(255), nullable=False)
  post_date = db.Column(db.DateTime, nullable=False, default=datetime.now)

class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(50), nullable=False, unique=True)
	password = db.Column(db.String(25))

#ログイン機能のためのおまじないのようなモノ
@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))

@app.route('/',methods=['GET','POST'])
def index():
    if request.method == 'GET':
      #ページ番号1に飛ばす
      return redirect('/1')

    if request.method == 'POST':
      user = request.form.get('user')
      title = request.form.get('title')
      detail = request.form.get('detail')
      post_date = datetime.now()
      title_post = Title(user=user, title=title, detail=detail, post_date=post_date)
      db.session.add(title_post)
      db.session.flush()
      thread_post = Thread(user=user, title=title,
      detail=detail, post_date=post_date, Title_id=title_post.id)
      db.session.add(thread_post)
      db.session.commit()
      return redirect('/')

@app.route('/<int:page_num>',methods=['GET','POST'])
def page(page_num):
  if request.method == 'GET':
    posts = Title.query.order_by(desc(Title.post_date)).all()
    #この方法だと全てのデータを取ってくるので手間がかかりそうではあるので適宜修正したほうがいいかもしれない
    posts = posts[page_contents_num*(page_num-1):page_contents_num*(page_num)]
    is_login = current_user.is_authenticated
    current_page = page_num
    return render_template('index.html',posts=posts,is_login=is_login,current_page=current_page)
  if request.method == 'POST':
    #検索機能
    keyword = request.form.get('keyword')
    posts = Title.query.order_by(desc(Title.post_date)).filter(Title.title.like(f'%{keyword}%')).limit(page_contents_num)
    #つなげて使うことで順番に指定した要素を取り出すことができる
    print(type(posts))
    is_login = current_user.is_authenticated
    current_page = page_num
    return render_template('index.html',posts=posts,is_login=is_login,current_page=current_page)

@app.route('/signup', methods=['GET', 'POST'])
@login_required
def signup():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        # Userのインスタンスを作成
        user = User(username=username, password=generate_password_hash(password, method='sha256'))
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    else:
        return render_template('signup.html')

@app.route('/login',methods=['GET','POST'])
def login():
  if request.method == "POST":
      username = request.form.get('username')
      password = request.form.get('password')
      # Userテーブルからusernameに一致するユーザを取得
      user = User.query.filter_by(username=username).first()
      if check_password_hash(user.password, password):
          login_user(user)
          return redirect('/')
  else:
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@app.route('/post')
def post():
  return render_template('post.html')

@app.route('/delete/<int:id>')
def delete_thread(id):
    post = Title.query.get(id)
    #タイトルに付随するスレッドを全て削除する
    #この機能を用いて本人のスレッドごと削除してもらう
    threads = Thread.query.filter_by(Title_id=id).all()
    for thread in threads:
      db.session.delete(thread)
    db.session.delete(post)
    db.session.commit()
    return redirect('/')

@app.route('/delete_comment/<int:Title_id>/<int:id>/')
def delete_comment(Title_id,id):
    comments = Thread.query.filter_by(Title_id=Title_id).all()
    for comment in comments:
      if comment.id == id:
        db.session.delete(comment)
    print('削除します')
    db.session.commit()
    print('削除しました')
    return redirect(f'/thread/{Title_id}')

@app.route('/thread/<int:id>')
def thread(id):
    comments = Thread.query.filter_by(Title_id=id).all()
    is_login = current_user.is_authenticated
    return  render_template('thread.html',comments=comments,is_login=is_login)

@app.route('/thread/comment',methods=['POST'])
def comment():
  Title_id = request.form.get('Title_id')
  user = request.form.get('user')
  title = request.form.get('title')
  detail = request.form.get('detail')
  post_date = datetime.now()
  thread_post = Thread(user=user, title=title,
  detail=detail, post_date=post_date, Title_id=Title_id)
  db.session.add(thread_post)
  print('データを追加します')
  db.session.commit()
  print('データを追加しました')
  #スレッドの方のデータベースに新しいコメントを付け足す
  return redirect(f'/thread/{Title_id}')

if __name__ == '__main__':
    app.run()
