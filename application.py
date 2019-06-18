import os

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
            return render_template("search.html", username=username)
        else:
            return render_template("login.html",
                                   error="Bad username or password.")
    else:
        return render_template("login.html")


@app.route("/")
def main():
    return redirect(url_for("login"))
