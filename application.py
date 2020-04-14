import os

from flask import Flask, session, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

app = Flask(__name__)


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False

app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods = ["GET"])
def index():
    return render_template("index.html")

@login_required
@app.route("/books", methods = ["GET", "POST"])
def books():
    if request.method == "POST":
        if not request.form.get("search"):
            return "Must provide ISBN, title or author"
        search = request.form.get("search")
        books = db.execute("SELECT * FROM books WHERE title LIKE :search OR author LIKE :search OR isbn LIKE :search", {"search":("%"+search.lower()+"%")}).fetchall()
        if books is None:
            return "There is not matches for your request"
        return render_template("search.html", books = books, search = search)
    return render_template("index.html")

@app.route("/register", methods = ["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return "must provide username"
        if not request.form.get("password"):
            return "must provide password"
        if not request.form.get("password-confir"):
            return "must confirm your password"
        if request.form.get("password") != request.form.get("password-confir"):
            return "The passwords are not the same"
        username = request.form.get("username")
        usr = db.execute("SELECT * FROM users WHERE user_name =:user_name", {"user_name":username}).fetchone()
        

        if usr is not None:
            return "The username already exists"

        psw =  generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (user_name, hash) VALUES (:user_name, :hash)", {"user_name":username, "hash":psw})
        db.commit()
        return render_template("login.html")
        
    else:
        return render_template("register.html")

@app.route("/login", methods = ["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        #Check that the user has submitted the form with a username and a password
        if not request.form.get("username"):
            return "must provide username"
        if not request.form.get("password"):
            return "must provide password"
        
        username = request.form.get("username")
        usr = db.execute("SELECT * FROM users WHERE user_name = :user_name", {"user_name":username}).fetchone()
        psw = request.form.get("password")

        if usr is None and not check_password_hash(usr[2], psw):
            return "invalid username and/or password"
        
        session["user_id"] = usr[0]
        return render_template("index.html")
       
    else:
        return render_template("login.html")



@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()
    return render_template("login.html")


@app.route("/book/<book_isbn>", methods = ["GET"])
def book(book_isbn):
    book_info = db.execute("SELECT * FROM books JOIN books_review ON books.isbn = books_review.isbn WHERE books.isbn =:isbn", {"isbn":book_isbn}).fetchone()
    print(book_info)
    return render_template("info_book.html", book_info=book_info)
    
