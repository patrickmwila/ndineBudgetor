# ndineBudgetor

A personal finance tracking web application built with Flask and Bootstrap.

## Features

- Track income and expenses
- Categorize transactions
- View financial overview
- Mobile-responsive design
- Simple and intuitive interface

## Dependencies

### System Requirements

#### For Latest Ubuntu (22.04+)
```bash
# Update package list
sudo apt update

# Install Python 3 and pip
sudo apt install python3 python3-pip python3-venv

# Install required system packages
sudo apt install build-essential libssl-dev libffi-dev python3-dev
```

#### For Ubuntu 18.04 LTS
```bash
# Update package list
sudo apt update

# Install Python 3.7 (minimum required version)
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.7 python3.7-venv python3.7-dev

# Install pip for Python 3.7
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3.7 get-pip.py

# Install required system packages
sudo apt install build-essential libssl-dev libffi-dev
```

### Python Dependencies

#### For Latest Ubuntu (22.04+)
Use the current requirements.txt:
```
Flask==2.3.3
Flask-SQLAlchemy==3.1.1
SQLAlchemy==2.0.21
Flask-Login==0.6.2
Werkzeug==2.3.7
python-dotenv==1.0.0
Flask-WTF==1.1.1
email-validator==2.0.0
```

#### For Ubuntu 18.04 LTS
Create a file named `requirements_18.04.txt`:
```
Flask==2.0.1
Flask-SQLAlchemy==2.5.1
SQLAlchemy==1.4.23
Flask-Login==0.5.0
Werkzeug==2.0.1
python-dotenv==0.19.0
Flask-WTF==0.15.1
email-validator==1.1.3
```

## Configuration

### Environment Variables

The application uses environment variables for configuration. Create a `.env` file in the root directory with the following variables:

```bash
# Database Configuration
SQLALCHEMY_DATABASE_URI=sqlite:///budget.db

# Application Security
SECRET_KEY=your-secret-key-here

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Default Admin Configuration
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secure-password-here
ADMIN_DEFAULT_CURRENCY=ZMW
```

> **Note**: Never commit your `.env` file to version control. A `.env.example` file is provided as a template.

## Installation

1. Create a virtual environment:
```bash
# For Latest Ubuntu
python3 -m venv venv

# For Ubuntu 18.04
python3.7 -m venv venv
```

2. Activate the virtual environment:
```bash
source venv/bin/activate
```

3. Install requirements:
```bash
# For Latest Ubuntu
pip install -r requirements.txt

# For Ubuntu 18.04
pip install -r requirements_18.04.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to `http://localhost:5000`

## Production Deployment (Ubuntu 18.04)

1. Install and configure Nginx:
```bash
sudo apt install nginx
```

2. Install Gunicorn:
```bash
pip install gunicorn==20.0.4
```

3. Create a systemd service file:
```bash
sudo nano /etc/systemd/system/ndineBudgetor.service
```

Add the following content (adjust paths as needed):
```ini
[Unit]
Description=Gunicorn instance to serve ndineBudgetor
After=network.target

[Service]
User=your_username
Group=www-data
WorkingDirectory=/path/to/ndineBudgetor
Environment="PATH=/path/to/ndineBudgetor/venv/bin"
ExecStart=/path/to/ndineBudgetor/venv/bin/gunicorn --workers 3 --bind unix:ndineBudgetor.sock -m 007 app:app

[Install]
WantedBy=multi-user.target
```

4. Configure Nginx:
```bash
sudo nano /etc/nginx/sites-available/ndineBudgetor
```

Add the following content:
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        include proxy_params;
        proxy_pass http://unix:/path/to/ndineBudgetor/ndineBudgetor.sock;
    }

    location /static {
        alias /path/to/ndineBudgetor/static;
    }
}
```

5. Enable the site and restart services:
```bash
sudo ln -s /etc/nginx/sites-available/ndineBudgetor /etc/nginx/sites-enabled
sudo systemctl restart nginx
sudo systemctl start ndineBudgetor
sudo systemctl enable ndineBudgetor
```

## Development

- Built with Flask
- Uses SQLite database
- Bootstrap 5 for responsive design
- Custom CSS for styling
- JavaScript for interactive features

## Troubleshooting

### Common Issues on Ubuntu 18.04

1. If you encounter SSL errors:
```bash
pip install --upgrade pip setuptools wheel
```

2. If SQLAlchemy gives compatibility errors:
```bash
pip install SQLAlchemy==1.4.23
```

3. If Flask-SQLAlchemy shows version conflicts:
```bash
pip install Flask-SQLAlchemy==2.5.1
```

## License

MIT License
