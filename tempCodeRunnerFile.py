
        username = request.form["username"]
        password = request.form["password"]

        if os.path.exists("users.txt"):
            with open("users.txt", "r") as f:
                for line in f:
                    if line.strip().split(",")[0] == username:
                        logging.warning(f"Attempted registration with existing username: {username}")
                        return render_template("register.html", error="Username already exists")

        with open("users.txt", "a") as f:
            f.write(f"{username},{password}\n")

        logging.info(f"New user registered: {username}")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/logout")
def logout():