import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # get the id of user in session
    user_id = session["user_id"]

    # Get the user's cash balance from the "users" table // ensure to access the cash balance of the specific user
    cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

    # Get the list of stocks the user owns (symbol and shares) from the "OWNED" table.
    owned_stocks = db.execute(
        "SELECT symbol, stocks FROM OWNED WHERE user_id = ?", user_id
    )

    # Create an empty list to store stock data
    stocks = []

    # make a holder for the whole total, starts cash
    grand_total = cash

    # Iterate through the owned stocks
    for stock in owned_stocks:
        symbol = stock["symbol"]
        shares = stock["stocks"]
        if lookup(symbol):
            # Use the lookup function to get the current stock price
            price = lookup(symbol)["price"]

            # get the total value
            total = price * shares

            # add to grand_total
            grand_total += total

            # add info for each stock as a dictionary on the list i made
            stocks.append(
                {
                    "symbol": symbol,
                    "shares": shares,
                    "price": price,
                    "total_value": total,
                }
            )

    # Pass the data to the HTML template for rendering.
    return render_template(
        "index.html", cash=cash, stocks=stocks, grand_total=grand_total
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        # get id from the user in active session
        user_id = session["user_id"]

        # get value of symbol from form
        symbol = lookup(request.form.get("symbol"))

        shares_str = request.form.get("shares")

        # Check if the input is a valid integer
        if not shares_str.isdigit():
            return apology("Invalid share amount (must be a whole number)", 400)

        # Convert the valid integer string to an integer
        shares = int(shares_str)

        # validate both, if not then return apology
        if not symbol:
            return apology("unexistent symbol", 400)
        if not shares or shares < 1:
            return apology("invalid share amount", 400)

        # get cash from user db
        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        cash = cash[0]["cash"]

        # get the price per unit from the stock
        unit_price = symbol["price"]

        # calculate the total purchase amount
        total = unit_price * int(shares)

        # if there's enough cash show sucessfull
        if total <= cash:
            # update cash in users
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash - total, user_id)

            # modify owes db to add symbol bough
            db.execute(
                "INSERT OR IGNORE INTO OWNED (user_id, symbol) VALUES (?, ?)",
                user_id,
                symbol["symbol"],
            )

            # get value of the actual stock value
            actual_stocks = db.execute(
                "SELECT stocks FROM OWNED WHERE user_id = ? AND symbol = ?",
                user_id,
                symbol["symbol"],
            )

            if not actual_stocks:
                actual_stocks = 0
            else:
                actual_stocks = actual_stocks[0]["stocks"]

            # Calculate the new total number of shares
            new_stocks = actual_stocks + shares

            # If the user didn't own any shares, use INSERT to create a new record
            if actual_stocks == 0:
                db.execute(
                    "INSERT INTO OWNED (user_id, symbol, stocks) VALUES (?, ?, ?)",
                    user_id,
                    symbol["symbol"],
                    new_stocks,
                )
            else:
                # Otherwise, use UPDATE to update the existing record
                db.execute(
                    "UPDATE OWNED SET stocks = ? WHERE user_id = ? AND symbol = ?",
                    new_stocks,
                    user_id,
                    symbol["symbol"],
                )

            # add to transaction history
            db.execute(
                "INSERT INTO TRANSACTION_HISTORY(user_id, symbol, price, amount, type) VALUES (?, ?, ?, ?, ?)",
                user_id,
                symbol["symbol"],
                unit_price,
                shares,
                "buy",
            )

            flash("Purchase completed")
            return redirect("/")

        # return apology to user
        else:
            return apology("Not enough cash to finalize the purchase", 403)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # get the user id in session
    user_id = session["user_id"]

    # Get the sort & order parameter from the query string
    sort_by = request.args.get("sort", "timestamp")  # Default sorting by timestamp
    order_by = request.args.get("order", "asc")  # Default sorting order is ascending

    # Determine the SQL ORDER BY clause based on the sort and order parameters
    if sort_by == "symbol":
        order_by_clause = f"ORDER BY symbol {order_by}"
    elif sort_by == "price":
        order_by_clause = f"ORDER BY price {order_by}"
    elif sort_by == "amount":
        order_by_clause = f"ORDER BY amount {order_by}"
    else:
        order_by_clause = f"ORDER BY timestamp {order_by}"  # Default sorting

    # get the relevant data
    sells = db.execute(
        f"SELECT * FROM TRANSACTION_HISTORY WHERE user_id = ? AND type = ? {order_by_clause}",
        user_id,
        "sell",
    )
    buys = db.execute(
        f"SELECT * FROM TRANSACTION_HISTORY WHERE user_id = ? AND type = ? {order_by_clause}",
        user_id,
        "buy",
    )

    return render_template("history.html", sells=sells, buys=buys)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        # Get the user's input stock symbol
        user_symbol = request.form.get("symbol")

        # Retrieve the stock information using the lookup function
        stock_info = lookup(user_symbol)

        # Ensure the symbol brings out valid results
        if not stock_info:
            return apology("Symbol not found", 400)

        # Extract relevant information from the stock_info dictionary
        name = stock_info["name"]
        price = stock_info["price"]
        symbol = stock_info["symbol"]

        # Render the quoted.html template with the stock information
        return render_template("quoted.html", symbol=symbol, price=price, name=name)
    else:
        # If it's a GET request, render the quote.html template
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # save username and passwords
        username = request.form.get("username")
        existing_user = db.execute("SELECT * FROM users WHERE username = ?", username)

        if existing_user:
            return apology("Username already taken", 400)
        else:
            password = request.form.get("password")

            # ensure data was submitted
            if not username:
                return apology("must provide username", 400)
            # Ensure password and confirmation were submitted
            elif not password or not request.form.get("confirmation"):
                return apology("must provide password", 400)
            # Ensure password and confirmation are the same
            elif password != request.form.get("confirmation"):
                return apology("passwords don't match", 400)
            else:
                # get password hash
                password_hash = generate_password_hash(password)
                # save into the database
                db.execute(
                    "INSERT INTO users (username, hash) VALUES (?, ?)",
                    username,
                    password_hash,
                )
                return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    # get id from the session
    user_id = session["user_id"]

    if request.method == "POST":
        # get the symbol value from the form
        symbol = lookup(request.form.get("symbol"))

        # if no stock was submitted render apology
        if not symbol:
            return apology("no symbol", 400)

        # get value for shares they wanna sell
        shares = request.form.get("shares")

        # render apology if it isnt a positive integer
        if not shares.isdigit() or int(shares) <= 0:
            return apology("Invalid share number", 400)

        # check if user owns shares of that stock
        shares_owned = db.execute(
            "SELECT stocks FROM OWNED WHERE user_id = ? AND symbol = ?",
            user_id,
            symbol["symbol"],
        )

        # If the user doesn't own any shares of that stock, render apology
        if not shares_owned:
            return apology("You don't own any shares of that stock", 400)

        shares_owned = shares_owned[0]["stocks"]

        # If the user is trying to sell more shares than they own, render apology
        if int(shares) > shares_owned:
            return apology("Not enough shares of that stock", 400)

        # get the price of the symbol now
        price = symbol["price"]

        # calculate total selling value
        sell_total = price * int(shares)

        # add total to the user's bank account cash
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", sell_total, user_id)

        # get value fo the new shares
        new_shares = shares_owned - int(shares)

        if new_shares == 0:
            db.execute(
                "DELETE FROM OWNED WHERE user_id = ? AND symbol = ?",
                user_id,
                symbol["symbol"],
            )
        else:
            db.execute(
                "UPDATE OWNED SET stocks = ? WHERE user_id = ? AND symbol = ?",
                new_shares,
                user_id,
                symbol["symbol"],
            )

        # save to transactions
        db.execute(
            "INSERT INTO TRANSACTION_HISTORY(user_id, symbol, price, amount, type) VALUES (?, ?, ?, ?, ?)",
            user_id,
            symbol["symbol"],
            price,
            shares,
            "sell",
        )

        flash("Successfully sold")
        return redirect("/")

    else:
        # save into a dict list all the owned stocks
        owned_stocks = db.execute("SELECT symbol FROM OWNED WHERE user_id = ?", user_id)

        symbols = []

        # lookup the symbols to create an actual array
        for stock in owned_stocks:
            stock = lookup(stock["symbol"])
            symbols.append(stock["symbol"])

        return render_template("sell.html", symbols=symbols)
