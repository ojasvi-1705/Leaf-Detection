import os
import smtplib
import random
import logging
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, session, flash
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
app.secret_key = "secret_key_for_session"

model = load_model('models/leafdetectionmodel.h5')
logging.info("Model loaded successfully.")


def preprocess_image(image_path):
    logging.info(f"Preprocessing image: {image_path}")
    img = load_img(image_path, target_size=(256, 256))
    img_array = img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        logging.warning("Unauthorized access attempt to index.")
        return redirect(url_for("login"))
    
    prediction = None
    image_path = None

    if request.method == "POST":
        file = request.files["leaf_image"]
        if file:
            os.makedirs("static", exist_ok=True)
            filepath = os.path.join("static", file.filename)
            file.save(filepath)
            logging.info(f"Image uploaded by {session['username']}: {filepath}")

            img = preprocess_image(filepath)
            result = model.predict(img)
            prediction = "Defective" if result[0][0] < 0.5 else "Healthy"
            image_path = filepath
            logging.info(f"Prediction by {session['username']}: {prediction}")

    return render_template("index.html", prediction=prediction, image_path=image_path, username=session["username"])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if os.path.exists("users.txt"):
            with open("users.txt", "r") as f:
                for line in f:
                    data = line.strip().split(",")
                    if len(data) == 3:
                        stored_user, stored_pass, _ = data
                        if stored_user == username and stored_pass == password:
                            session["username"] = username
                            logging.info(f"User logged in: {username}")
                            return redirect(url_for("index"))

        logging.warning(f"Failed login attempt for user: {username}")
        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]

        if os.path.exists("users.txt"):
            with open("users.txt", "r") as f:
                for line in f:
                    if line.strip().split(",")[0] == username:
                        logging.warning(f"Registration attempt with existing username: {username}")
                        return render_template("register.html", error="Username already exists")

        with open("users.txt", "a") as f:
            f.write(f"{username},{password},{email}\n")
        logging.info(f"New user registered: {username}")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form["email"]
        if os.path.exists("users.txt"):
            with open("users.txt", "r") as f:
                for line in f:
                    user_data = line.strip().split(",")
                    if len(user_data) == 3 and user_data[2] == email:
                        session["reset_email"] = email
                        otp = send_otp(email)
                        if otp:
                            session["otp"] = otp
                            return redirect(url_for("verify_otp"))
                        else:
                            logging.error(f"OTP sending failed for {email}")
                            return render_template("forgot.html", error="Failed to send OTP. Try again.")
        logging.warning(f"Password reset attempted for unknown email: {email}")
        return render_template("forgot.html", error="Email not found")
    return render_template("forgot.html")

EMAIL_ADDRESS = "ojasvi.gupta170504@gmail.com"
EMAIL_PASSWORD = "tsso puto zjuw uhkf"  # Use Gmail App Password

def send_otp(email):
    otp = str(random.randint(100000, 999999))
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = email
    msg['Subject'] = "OTP for Password Reset"

    body = f"Your OTP to reset password is: {otp}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        logging.info(f"Connecting to Gmail SMTP server to send OTP to {email}")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logging.info(f"OTP sent to {email} successfully")
        return otp
    except Exception as e:
        logging.error(f"Email sending failed: {str(e)}")
        return None
        
@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        user_otp = request.form["otp"]
        if user_otp == session.get("otp"):
            logging.info("OTP verified successfully.")
            return redirect(url_for("reset_password"))
        else:
            logging.warning("Invalid OTP entered.")
            return render_template("verify_otp.html", error="Invalid OTP")
    return render_template("verify_otp.html")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    # Ensure user has passed OTP and session has email stored
    if "reset_email" not in session:
        return redirect(url_for("forgot"))  # No email in session, send back to forgot password

    if request.method == "POST":
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        # Password match check
        if new_password != confirm_password:
            return render_template("reset_password.html", error="Passwords do not match")

        updated_lines = []
        with open("users.txt", "r") as f:
            for line in f:
                username, password, email = line.strip().split(",")

                # 👇 Update password for the matching email
                if email == session["reset_email"]:
                    updated_lines.append(f"{username},{new_password},{email}\n")
                else:
                    updated_lines.append(line)

        # Write updated data back to file
        with open("users.txt", "w") as f:
            f.writelines(updated_lines)

        # Optional logging
        logging.info(f"Password reset successful for: {session['reset_email']}")

        # Clean up session
        session.pop("otp", None)
        session.pop("reset_email", None)

        return redirect(url_for("login"))

    # GET request - show password reset form
    return render_template("reset_password.html")


@app.route("/logout")
def logout():
    logging.info(f"User logged out: {session.get('username')}")
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    print("Flask app is running at http://127.0.0.1:5000")
    app.run(debug=True)






