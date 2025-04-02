# Project Overview

This project is a web application for a **messenger** built using **Python 3.12.3**. It utilizes the following major
dependencies:

- **Flask**: A lightweight WSGI web application framework for request handling and routing.
- **Jinja2**: A powerful templating engine for dynamic HTML rendering.
- **Werkzeug**: A WSGI utility library for building web servers.
- **pymongo**: A Python driver for MongoDB, enabling database integration.
- **Flask-SocketIO**: Adds WebSocket support to Flask for real-time communication.
- **click**: A package for creating command-line interfaces.

## Features

- **Messaging System**: Real-time messaging functionality using WebSockets.
- **Templating**: Dynamic rendering of HTML pages powered by Jinja2.
- **Database Integration**: Uses MongoDB for storing user data, messages, and other application-related information.
- **CLI Tools**: Command-based scripts powered by `click` for administrative tasks.
- **Front-end**: Built using a combination of **HTML**, **JavaScript**, and **CSS** for a responsive user interface.
- **WebSocket Support**: Enables instant message transmission and real-time updates with Flask-SocketIO.

## Prerequisites

To run this project, ensure you have the following installed:

1. **Python 3.12.3**
2. **pip**, the Python package manager.
3. **MongoDB**, the NoSQL database.

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Setup any environment variables needed for configuration. Example:
   ```bash
   export FLASK_APP=app.py
   export FLASK_ENV=development
   export MONGO_URI=<your-mongo-connection-uri>
   ```

4. Run MongoDB locally or ensure your MongoDB connection URI points to the correct database instance.

## Running the Application

1. Start the Flask development server:
   ```bash
   flask run
   ```

2. Open the application in your browser at `http://127.0.0.1:5000`.

