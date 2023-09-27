import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///birthdays.db")

# send month value to do dropdown
months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Save values from form into variables
        name = request.form.get("name")
        # Get value for birthday
        day = request.form.get("day")
        month = request.form.get("month")
        # change the month string to int
        month_int = (
            months.index(month) + 1
        )  # Adding 1 to match your expected month format

        # save birthday into db
        db.execute(
            "INSERT INTO birthdays (name, day, month) VALUES (?, ?, ?)",
            name,
            day,
            month_int,
        )
        return redirect("/")

    else:
        # Display the entries in the database on index.html
        # send people on database
        birthdays = db.execute("SELECT * FROM birthdays")
        return render_template("index.html", birthdays=birthdays, months=months)


@app.route("/delete", methods=["POST"])
def delete():
    id = request.form.get("id")
    if id:
        db.execute("DELETE FROM birthdays WHERE id = ?", id)
    return redirect("/")
