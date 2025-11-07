# Colby-Now-Merchandise
<center> <img src="app/static/images/colbynow_merch_logo.png" width=300px></center>
A full-stack web application that serves as an online marketplace for the Colby College community where students, staff, and faculty can buy, sell, and donate items.
 - This project uses a **Flask** backend to handle user authentication, product listings, and other business logic, with a standard **HTML**, **CSS**, and **JavaScript** frontend.  

## Project Structure

```
Colby-Now-Merchandise/
├── README.md
├── .env                # Environment variables (needs to be created)
├── .env.example        # Example environment variables
├── requirements.txt    # Project dependencies
├── run.py              # Application entry point
├── instance/
│   └── users.db        # SQLite database (auto-generated on run)
└── app/
    ├── __init__.py     # Main Flask application factory
    ├── auth.py         # Authentication routes (signup, login, reset password, etc.)
    ├── main.py         # Core application routes (homepage, posting, item details, etc.)
    ├── models.py       # SQLAlchemy database models
    ├── static/
    │   ├── css/
    │   │   ├── auth.css
    │   │   ├── buy_item.css
    │   │   └── style.css
    │   ├── images/
    │   │   ├── bg-1.jpg
    │   │   ├── colby_logo.jpg
    │   │   ├── colbynow_merch_logo.png
    │   │   └── miller_library.jpg
    │   ├── js/
    │   │   └── auth.js
    │   └── uploads/    # User-uploaded item images (auto-generated)
    └── templates/
        ├── buy_item.html
        ├── forgot_password.html
        ├── home.html
        ├── item_details.html
        ├── login.html
        ├── post_new_item.html
        ├── reset_password.html
        └── signup.html
```

**Note:** The `.env` file (for environment variables) should be created in the root directory as described in the "Configure Environment Variables" section below. The `instance/` and `static/uploads/` directories are auto-generated when the application runs.

## Getting Started

Follow these instructions to get the project running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.x
*   `pip` package manager

### 1. Set Up the Environment

First, clone the repository and navigate into the project directory.

```bash
# Navigate to the project folder
cd /path/to/Colby-Now-Merchandise

# Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies

Install the required Python packages listed in the `requirements.txt` file using pip:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Run the following command to create a `.env` file from the example `.env` file in the root of the project directory:
```bash
cp .env.example .env
```

This file will store sensitive configuration details as shown below:
```
# .env
SECRET_KEY="your_super_secret_and_random_key"
MAIL_USERNAME="your-email@gmail.com"
MAIL_PASSWORD="your-gmail-app-password"
```
**Note:** For the `MAIL_PASSWORD`, it is highly recommended to use a Google App Password if you have 2-Factor Authentication enabled on your Google account.

### 4. Run the Application

With the virtual environment active and dependencies installed, run the main application file:

```bash
python run.py
```

The application will start in debug mode and be accessible at:

**http://127.0.0.1:5000**

When you first run the app, a `users.db` SQLite database file will be created in the `instance/` directory.