Gun Rental and Shooting Range Management System
This project aims to create a database system supporting the operations of a gun rental and shooting range service. 
The system is designed to manage customer reservations for firearms.

The product is a web-based application providing user interface that allows interaction with the database.
Customers are able to register, reserve equipment, book shooting sessions, and manage their accounts through a web platform.

Requirements
bcrypt==4.2.1
blinker==1.9.0
click==8.1.7
Flask==3.1.0
Flask-WTF==1.2.2
itsdangerous==2.2.0
Jinja2==3.1.4
MarkupSafe==3.0.2
psycopg2==2.9.10
Werkzeug==3.1.3
WTForms==3.2.1

How to download:
If you don't have it, install git on your maschine.
enter folder you want to store this project and enter:
git clone https://github.com/avalanche-pwn/bazy_projekt.git

How to  creat container using docker desktop : 
Create .txt files in db folder
user.txt and add user name
pwd.txt and add user password
pwd_back.txt and add password to communicate with backend

docker-compose build
docker-compose up

Installing Backend Libraries
To install backend libraries (e.g., Flask), you can use pip. Here’s an example for Flask:
pip install flask
To install the full list of required libraries, use the requirements.txt file that is included in the project:
pip install -r requirements.txt

Database Restore
To restore the database from a backup, use the following command:
psql -U <your-db-user> -d <your-db-name> -f <backup-file-path>

Running the Application
Once your database schema is set up and the application is running, navigate in your browser to start using the web application.
You will be able to:
Register and log in as a user.
Reserve firearms or ammunition.
Manage your reservations.

