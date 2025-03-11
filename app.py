import numpy as np
import os
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from tensorflow.keras.applications.xception import preprocess_input
import tensorflow as tf
from flask import Flask , request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import requests
from huggingface_hub import hf_hub_download

app = Flask(__name__)
app.secret_key = '123'  # Change this to a secure key
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///users.db'
#load_dotenv()
#app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Define User model for database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

# Create database
with app.app_context():
    db.create_all()

# Routes for Authentication
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        # Check if username or email already exists
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful, please log in', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

repo_id = "nallaroshini/BreathScan"  # Replace with your actual repo ID
filename = "Breath-Scan.h5"
model_path = hf_hub_download(repo_id=repo_id, filename=filename)
model = tf.keras.models.load_model(model_path)

@app.route('/home1')
def index():
    return render_template("home.html")

@app.route('/home')
def home():
    return render_template("index.html")

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/precautions')
def precautions():
    return render_template('precautions.html')

@app.route('/trends')
def trends():
    return render_template('trends.html')

# Add this Records model for storing upload details
class Records(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    result = db.Column(db.String(150), nullable=False)

# Create the records table in the database
with app.app_context():
    db.create_all()

@app.route('/predict',methods=["POST"])
def predict():
    first_name = request.form.get('first_name')  # Get the user's first name from the form
    last_name = request.form.get('last_name')    # Get the user's last name from the form
    file = request.files['image']
    if file:
        basepath=os.path.dirname(__file__)
        print('current path : ', basepath)
        filepath= os.path.join(basepath,'static/uploads',file.filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        print('file path : ', filepath)
        file.save(filepath)
        img = load_img(filepath, target_size=(299,299))
        x=img_to_array(img)
        x=np.expand_dims(x,axis=0)
        x = preprocess_input(x)  # Normalize the image

        pred=np.argmax(model.predict(x),axis=1)
        index=['Covid-19', 'Lung Opacity', 'Normal', 'Viral Pneumonia']
        result=index[pred[0]]

        # Store result in the records table
        new_record = Records(first_name=first_name, last_name=last_name, result=result)
        db.session.add(new_record)
        db.session.commit()
        text = "the person is diagnosed with : " + str(result)
        return render_template("index.html",result=text)
    
if _name_ == '_main_':
    port = int(os.environ.get("PORT", 10000))  # Default to 10000 for local testing
    app.run(host='0.0.0.0', port=port)
