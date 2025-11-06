# Colby-Now-Merchandise
A full-stack web application that serves as an online marketplace for the Colby College community where students, staff, and faculty can buy, sell, and donate items.
 - This project uses a **Flask** backend to handle user authentication, product listings, and other business logic, with a standard **HTML**, **CSS**, and **JavaScript** frontend.

## Directory Structure

```
Colby-Now-Merchandise/
├── README.md
├── .env              # Environment variables (needs to be created)
├── .env.example      # Example environment variables
├── requirements.txt  # Project dependencies
├── users.db          # SQLite database (auto-generated on run)
└── src/
    ├── backend/
    │   ├── app.py        # Main Flask application factory
    │   ├── auth.py       # Authentication routes (signup, login, etc.)
    │   ├── main.py       # Core application routes (homepage, etc.)
    │   └── models.py     # SQLAlchemy database models
    └── frontend/
        ├── static/
        │   ├── css/
        │   │   └── style.css
        │   └── images/
        │       └── Screenshot 2025-11-05 at 6.01.34 PM.png
        └── templates/
            ├── add_item_detail_page.html
            ├── add_product_form.html
            ├── forgot_password.html
            ├── home.html
            ├── login.html
            ├── reset_password.html
            └── signup.html
```

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
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
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
python src/backend/app.py
```

The application will start in debug mode and be accessible at:

**http://127.0.0.1:5000**

When you first run the app, a `users.db` SQLite database file will be created in the project root.