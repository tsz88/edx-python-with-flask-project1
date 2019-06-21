import os
import requests
import json

from flask import Flask, session, request, redirect, url_for, render_template
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import auth


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

error = None


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if len(username) == 0:
            error = "Empty username field."
            return render_template("register.html", error=error)
        if len(password) == 0:
            error = "Empty password field."
            return render_template("register.html", error=error)
        auth.register_new_user(username, password, db)
        return redirect(url_for("login"))


@app.route("/login",  methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if auth.authentication(username, password, db):
            return redirect(url_for("search"))
        else:
            return render_template("login.html",
                                   error="Bad username or password.")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session['user_id'] = None
    return render_template("login.html")


@app.route("/")
def main():
    return redirect(url_for("login"))


@app.route("/search", methods=["GET", "POST"])
def search():
    if session["user_id"] is None:
        return redirect(url_for("login"))
    if request.method == "GET":
        return render_template("search.html")

    title_fragment = request.form.get("title")

    if len(title_fragment) > 0:
        result_list = db.execute(
            "SELECT * FROM books WHERE title ILIKE '%" + title_fragment +
            "' OR title ILIKE '" + title_fragment + "%'").fetchall()
        book_list = []
        for book_tuple in result_list:
            book = parse_book_tuple_to_dictionary(book_tuple)
            book_list.append(book)
        return render_template("search.html", book_list=book_list)
    else:
        return render_template("search.html", error="No title specified.")


@app.route("/book/<int:book_id>")
def get_one_book(book_id, error=None):
    book_tuple = db.execute(
        "SELECT * FROM books WHERE books.id = :book_id",
        {"book_id": book_id}).fetchone()
    review_tuple_list = db.execute(
        "SELECT reviews.rating, reviews.opinion, reviews.user_id, " +
        "users.username FROM reviews JOIN users " +
        "ON reviews.user_id = users.id WHERE book_id = :book_id",
        {"book_id": book_id}).fetchall()
    book = parse_book_tuple_to_dictionary(book_tuple)
    review_list = []
    for review_tuple in review_tuple_list:
        review_list.append(get_all_review_info(review_tuple))

    # goodreads review avg and counter
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "HOX0NyHyNRNnfolsBkOMOA",
                               "isbns": book["isbn"]}).json()
    gr_review_count = res["books"][0]["reviews_count"]
    gr_avg_rating = res["books"][0]["average_rating"]

    if session['user_id'] is not None:
        return render_template("book_details.html", book=book,
                               review_list=review_list, error=error,
                               avg_rating=gr_avg_rating,
                               rev_count=gr_review_count)
    else:
        redirect(url_for("login"))


@app.route("/book/<int:book_id>/add_review", methods=["POST"])
def add_review(book_id):
    if session['user_id'] is None:
        redirect(url_for("login"))
    new_rating = request.form.get("new-rating")
    new_opinion = request.form.get("new-opinion")
    user_id = session.get('user_id')[0]
    # search if review is new or already one exists by user
    if db.execute("SELECT * FROM reviews WHERE reviews.user_id = :id",
                  {"id": user_id}).rowcount > 0:
        return get_one_book(book_id,
                            error="One book -- one review.")
    else:
        db.execute(
            "INSERT INTO reviews (rating, opinion, user_id, book_id) VALUES " +
            "(:new_rating, :new_opinion, :user_id, :book_id)",
            {"new_rating": new_rating, "new_opinion": new_opinion,
             "user_id": session['user_id'][0], "book_id": book_id}
        )
        db.commit()
        return redirect(url_for("get_one_book", book_id=book_id))


def parse_book_tuple_to_dictionary(book_tuple):
    book = {"id": book_tuple[0], "isbn": book_tuple[1],
            "title": book_tuple[2], "author": book_tuple[3],
            "year": book_tuple[4]}
    return book


def get_all_review_info(review_tuple):
    review = {
        "rating": review_tuple[0],
        "opinion": review_tuple[1],
        "user_id": review_tuple[2],
        "user_name": review_tuple[3]
    }
    return review
