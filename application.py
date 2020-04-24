import os

from flask import Flask, session, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import requests

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
            return render_template("register.html", pswNotSame = True)

        username = request.form.get("username")
        usr = db.execute("SELECT * FROM users WHERE user_name =:user_name", {"user_name":username}).fetchone()
        

        if usr is not None:
            return render_template("register.html", usernameExist = True)

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
        
        if usr is None or not check_password_hash(usr[2], psw):
            return render_template("login.html", invalidPsw = True)
        
        session["user_id"] = usr[0]
        return render_template("index.html")
       
    else:
        return render_template("login.html")



@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()
    return render_template("login.html")


@app.route("/book/<book_isbn>/<review>", methods = ["GET"])
def book(book_isbn, review):
    book_info = db.execute("SELECT * FROM books WHERE books.isbn =:isbn", {"isbn":book_isbn}).fetchone()
    reviews = db.execute("SELECT b.review, users.user_name, b.rating FROM books_review AS b\
                          JOIN users ON users.id_user = b.id_user\
                          JOIN books ON books.isbn = b.isbn WHERE books.isbn =:isbn", {"isbn":book_isbn}).fetchall()
    
    rev_count = goodreads(book_isbn)[0]
    avg_rating = goodreads(book_isbn)[1]
    print(reviews)
    if reviews is None or reviews == []:
        any_reviews = False
    else:
        any_reviews = True
    return render_template("info_book.html", book_info=book_info, reviews=reviews, rev_count=rev_count, avg=avg_rating, any_reviews=any_reviews, reviewExists=review)
    
@app.route("/review", methods = ["GET","POST"])
def review():
    if request.method == "POST":
        book = request.form.get("isbn")
        rate = request.form.get("rate")
        review = request.form.get("review")
        usr = session["user_id"]
        check_usr_review = db.execute("SELECT * FROM books_review AS b JOIN users ON users.id_user = b.id_user WHERE b.id_user =:id", {"id": usr}).fetchall()
        if check_usr_review is not None:
            return book(book, True)
        else:
            db.execute("INSERT INTO books_review (review, isbn, id_user, rating) VALUES (:review, :isbn, :id_user, :rating)", {"review": review, "isbn": book, "id_user": usr, "rating": rate})
            db.commit
            return book(book)
    else:
        return render_template("book.html")

@app.route("/api/<isbn>", methods = ["GET"])
def api(isbn):
    rows = dict(db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone())
    rows["review_count"] = goodreads(isbn)[0]
    rows["average_score"] = goodreads(isbn)[1]
    return rows

def goodreads(isbn):
    KEY ="G62mcEA3YwZRgW09SH0gA"
    goodRead = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns":isbn})
    rev_count = goodRead.json()['books'][0]['work_ratings_count']
    avg_rating = goodRead.json()['books'][0]['average_rating']
    return (rev_count, avg_rating)