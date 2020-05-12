from flask import Flask, render_template, request, redirect, session, flash, url_for, send_from_directory
from werkzeug.utils import secure_filename

from flaskext.mysql import MySQL
import hashlib
import datetime
import time
import os

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.secret_key = "mysecret123"

mysql = MySQL()

app.config['MYSQL_DATABASE_HOST']  = 'localhost'
app.config['MYSQL_DATABASE_USER']  = 'root'
app.config['MYSQL_DATABASE_PASSWORD']  = 'letmein1'
app.config['MYSQL_DATABASE_DB']  = 'insta'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql.init_app(app) 

@app.route('/')
def index():
    return render_template("home.html")

@app.route('/signup/', methods = ['POST', 'GET'])
def signup():
    if(request.method == "POST"):
        userd = request.form
        username = userd['username']
        password = userd['password']
        salt = '1ab'
        actual = password + salt
        stored_pass = hashlib.md5(actual.encode())

        conn = mysql.connect()
        cursor = conn.cursor()

        cursor.execute("select username from users")
        data = cursor.fetchall()

        flag = 0
        #to check if user already registered
        for d in data:
            if(d[0] == username):
                flag = 1
                break
        
        if(flag == 0):
            #for current time 
            date = datetime.datetime.now()
            print(date)

            cursor.execute("INSERT INTO users(username, password) VALUES(%s, %s)", (username, stored_pass.hexdigest()))
            conn.commit()
        elif(flag == 1):
            return "<script>alert('Username already taken! Try another one'); window.location = 'http://127.0.0.1:5000/signup/';</script>"    

        conn.commit()
        cursor.close()
        return redirect('/login/')
    return render_template('/signup.html')

@app.route('/login/', methods = ['POST', 'GET'])
def login():
    if(request.method == "POST"):
        userde = request.form
        username = userde['username']
        password = userde['password']
        p = password+'1ab'
        passcode = hashlib.md5(p.encode())
        
        conn = mysql.connect()
        cursor = conn.cursor()

        cursor.execute("select username, password from users")
        data = cursor.fetchall()

        for d in data:
            if(d[1] == passcode.hexdigest() and d[0] == username):
                session['logged_in'] = True
                session['username'] = username
                conn.commit()
                conn.commit()
                return redirect('/wall')
        conn.commit()
        cursor.close()
    return render_template('/login.html')

@app.route('/logout', methods = ['POST', 'GET'])
def logout():
    conn = mysql.connect()
    cursor = conn.cursor()
    if(request.method == "POST"):
        print('Delete')
        #Delete acc. from photos and users table
        #be careful
        query = "Delete from users where username = %s"
        cursor.execute(query, (session['username']))
        query = "Delete from photos where username = %s"
        cursor.execute(query, (session['username']))
    conn.commit()
    cursor.close()

    session.clear()
    return redirect('/')

@app.route('/wall/', methods = ['POST', 'GET'])
def wall():
    conn = mysql.connect()
    cursor = conn.cursor()
    username = session['username']
    query = ("Select pname, username, caption from photos where username = %s order by idphotos desc")
    cursor.execute(query, (username))
    data = cursor.fetchall()
    details = []
    for d in data:
        if(d[1] == username):
            details.append([d[0], d[1], d[2]])
    return render_template('wall.html', details = details)   

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

@app.route('/uploader', methods = ['POST', 'GET'])
def uploader():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            return "<script>alert('Please choose an image file'); window.location = 'http://127.0.0.1:5000/wall/';</script>"
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('Image uploaded')

            #insert photo details in photos table
            conn = mysql.connect()
            cursor = conn.cursor()
            username = session['username']
            caption = request.form['caption']
            cursor.execute("INSERT INTO photos(pname, username, caption) VALUES(%s, %s, %s)", (filename, username, caption))
            conn.commit()
            cursor.close()

            return redirect('/wall')
    return

@app.route('/search', methods = ['POST', 'GET'])
def search():
    if(request.method == "POST"):
        search = request.form['search']
        #hashtag = 1, user has requested hashtag query ; else profile query
        hashtag = 0
        if(search[0] == '#'):
            hashtag = 1
        
        conn = mysql.connect()
        cursor = conn.cursor()
        
        details = []
        hashtable = []

        if(hashtag == 0):
            query = ("Select pname, username, caption from photos where username = %s order by idphotos desc")
            cursor.execute(query, (search))
            data = cursor.fetchall()
            for d in data:
                if(d[1] == search):
                    details.append([d[0], d[1], d[2]])
        else:
            query = ("Select pname, username, caption from photos order by idphotos desc")
            cursor.execute(query)
            data = cursor.fetchall()
            for d in data:
                result = d[2].find(search)
                if(result != -1):
                    details.append([d[0], d[1], d[2]])

            #update on duplicate not working because of multiple primary key
            query = ("Update hashcount set count = count + 1 where name = %s")
            cursor.execute(query, (search))

            updated = cursor.rowcount
            if(int(updated) == 0):
                #hashtag is searched for the first time
                query = ("Insert into hashcount (name, count) Values (%s, %s)")
                cursor.execute(query, (search, int(1)))

        #store hashtag search count in decreasing order
        query = ("Select name, count from hashcount order by count desc")
        cursor.execute(query)
        data = cursor.fetchall()
        for d in data:
            hashtable.append((d[0], d[1]))
            
        conn.commit()
        cursor.close()

    return render_template('search.html', details = details, hashtable = hashtable)

@app.route('/profile/')
def profile():
    details = {
        'username' : session['username'],
    }
    return render_template('profile.html', details = details)

if __name__ == '__main__':
    app.run(debug = True)
