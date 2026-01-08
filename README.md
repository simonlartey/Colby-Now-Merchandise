# Mule-Mart

**Authors**: Francis O’Hara Aidoo, Rose Agyapong, Ninh Giang Nguyen, Simon Lartey

<p align="center">
  <img src="app/static/images/Mule Mart Logo V10 (Transparent).svg" width="600">
</p>

[![CI](https://github.com/mule-mart/mule-mart/actions/workflows/run_tests.yml/badge.svg)](https://github.com/mule-mart/mule-mart/actions/workflows/run_tests.yml)
[![Lint](https://github.com/mule-mart/mule-mart/actions/workflows/lint.yml/badge.svg)](https://github.com/mule-mart/mule-mart/actions/workflows/lint.yml)
![Python](https://img.shields.io/badge/python-3.x-blue)

👉 Live App: https://mulemart.com/  
👉 Live Demo: [Watch here](https://drive.google.com/file/d/1hK4I7gq76e5CHXErsHI6UwAylSC5V6pP/view?usp=sharing)

- A dedicated online marketplace for the Colby College community to buy, sell, and donate items, featuring AI-powered semantic search capabilities and real-time chat.
- This project currently uses a Flask backend to handle user authentication, product listings, and other business logic, with a standard HTML, CSS, and JavaScript frontend.

## Table of Contents
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Contributing](#contributing)
- [License](#license)

---

## Key Features

### Authentication and Security
- Secure sign-up and login for verified users (restricted to Colby College email addresses)
- Google OAuth authentication
- Password reset and account recovery

### Buyer Features
- Browse all available listings with images and prices
- View detailed item pages before purchasing
- Filter and sort items by category
- Semantic search for meaning-based item discovery
- Add, edit, and remove items from favorites
- Place orders with custom offers and meetup details
- Track order status (pending, approved, completed)

### Seller Features
- Create and manage item listings
- View incoming order requests
- Approve or cancel orders
- Mark items as sold after successful exchange

### Communication
- Real-time chat between buyers and sellers
- Inbox view with unread message counts
- Persistent conversation history

### User Experience
- Landing page with platform overview
- Profile page with editable user information and statistics
- Favorites page for saved items
- Revamped My Orders and My Listings dashboards

### Intelligent Search
- A major technical extension of this project is semantic search, implemented using SentenceTransformer embeddings. Instead of relying solely on keyword matching, the system retrieves conceptually related items based on meaning. 

---

## Screenshots

### Authentication
| Login | Sign Up |
|:---:|:---:|
| <img src="app/static/images/screenshots/login.png" width="400"> | <img src="app/static/images/screenshots/signup.png" width="400"> |

### Marketplace
| Feed | Buy Page |
|:---:|:---:|
| <img src="app/static/images/screenshots/home_feed.png" width="400"> | <img src="app/static/images/screenshots/buy_page.png" width="400"> |

| Item Details | Place Order |
|:---:|:---:|
| <img src="app/static/images/screenshots/item_details.png" width="400"> | <img src="app/static/images/screenshots/place_order.png" width="400"> |

| Post Item |
|:---:|
| <img src="app/static/images/screenshots/post_item.png" width="400"> |

### User Dashboard
| Profile | My Orders |
|:---:|:---:|
| <img src="app/static/images/screenshots/profile.png" width="400"> | <img src="app/static/images/screenshots/my_orders.png" width="400"> |

| My Listings | Favorites |
|:---:|:---:|
| <img src="app/static/images/screenshots/my_listings.png" width="400"> | <img src="app/static/images/screenshots/favorites.png" width="400"> |

### Communication
| Inbox & Chat |
|:---:|
| <img src="app/static/images/screenshots/inbox_chat.png" width="400"> |

---

## CI/CD Pipeline

The project uses GitHub Actions to enforce code quality and deployment reliability.

CI/CD workflow:
1. Run linting and automated tests by pytest
2. Enforce 95% test coverage 
3. Deploy to Heroku only if all checks pass

---

## Tech Stack
### Backend
- **Framework:** Python, Flask
- **Database ORM:** SQLAlchemy, Flask-Migrate
- **Authentication:** Flask-Login, Flask-Dance (Google OAuth)
- **Email:** Flask-Mail
### Frontend
- **Core:** HTML5, CSS3, JavaScript (ES6+)
- **Framework:** Bootstrap 5
### Data & Infrastructure
- **Database:** SQLite (Local), PostgreSQL (Production)
- **Object Storage:** AWS S3 (via Boto3) for profile & item images
- **Containerization:** Docker
- **Deployment:** Heroku
### Search & AI
- **Semantic Search:** SentenceTransformer, PyTorch, NumPy
### Quality Assurance
- **Testing:** Pytest, pytest-cov
- **Linting:** Black
- **CI/CD:** GitHub Actions

---
## Project structure

```
Mule-Mart/
    ├── .dockerignore
    ├── .env.example
    ├── .github/
    │   ├── ISSUE_TEMPLATE/
    │   │   ├── bug-report.yml
    │   │   └── feature-request.yml
    │   ├── pull_request_template.md
    │   └── workflows/
    │       ├── lint.yml
    │       └── run_tests.yml
    ├── .gitignore
    ├── .python-version
    ├── Dockerfile
    ├── LICENSE
    ├── Procfile
    ├── README.md
    ├── app/
    │   ├── __init__.py
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── auth_routes.py
    │   │   ├── chat_routes.py
    │   │   ├── items_routes.py
    │   │   ├── orders_routes.py
    │   │   ├── responses.py
    │   │   └── users_routes.py
    │   ├── auth.py
    │   ├── main.py
    │   ├── models.py
    │   ├── services/
    │   │   ├── auth_service.py
    │   │   ├── storage_service.py
    │   │   └── user_service.py
    │   ├── static/
    │   │   ├── css/
    │   │   ├── images/
    │   │   └── js/
    │   ├── templates/
    │   └── utils/
    │       ├── __init__.py
    │       ├── search_utils.py
    │       └── validators.py
    ├── boot.sh
    ├── migrations/
    ├── requirements.txt
    ├── run.py
    ├── scripts/
    │   ├── backfill_embeddings.py
    │   └── verify_search.py
    └── tests/
        ├── conftest.py
        ├── test_api.py
        ├── test_auth.py
        ├── test_chat_and_inbox.py
        ├── test_chat_extra.py
        ├── test_main_and_orders.py
        ├── test_main_extra.py
        ├── test_search_utils.py
        └── test_validators_and_models.py
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
cd /path/to/Mule-Mart

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


### 4. Initialize the Database
Run the following command to set up the database tables:
```bash
flask db upgrade
```
*Note: If you have an existing `users.db` from a previous version and encounter errors, delete the `instance/users.db` file and run the command again.*

### 5. Run the Application

With the virtual environment active and dependencies installed, run the main application file:

```bash
python run.py
```

The application will start in debug mode and be accessible at:

**http://127.0.0.1:5000**

When you first run the app, a `users.db` SQLite database file will be created in the `instance/` directory.

### 6. Development Tools

**Running Tests**
To run the automated test suite:
```bash
pytest
```

**Code Linting**
To check code formatting:
```bash
black .
```

## Running with Docker

Alternatively, you can run the application using Docker.

### 1. Build the Docker Image
```bash
docker build -t mule-mart .
```

### 2. Run the Container
You need to pass the environment variables to the container. You can use the `.env` file you created.
```bash
docker run --name mule-mart -p 8000:8000 --env-file .env mule-mart
```
The application will be accessible at **http://localhost:8000**.

### 3. Data Persistence (Optional)
To persist the SQLite database and uploaded images, mount the `instance` and `app/static/images` directories:
```bash
docker run --name mule-mart -p 8000:8000 --env-file .env \
    -v $(pwd)/instance:/app/instance \
    -v $(pwd)/app/static/images:/app/app/static/images \
    mule-mart
```

## Contributing
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
Distributed under the MIT License. See `LICENSE` for more information.
