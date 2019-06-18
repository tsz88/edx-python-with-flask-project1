from flask import Flask, session
import application


def register_new_user(username, password, db):
    db.execute("INSERT INTO users (username, password) " +
               "VALUES (:username, :password)",
               {"username": username, "password": password})
    db.commit()


def authentication(username, password, db):
    idnumber = db.execute(
        "SELECT id FROM users WHERE (username = :username)" +
        " AND (password = :password)",
        {"username": username, "password": password}).fetchone()
    db.commit()
    if idnumber is None:
        return False
    else:
        session['user_id'] = idnumber
        return True
