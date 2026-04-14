================================================================
  GymConnect — uGym & Power Zone Membership Website
  README — Setup & Run Instructions
================================================================

This file explains how to set up and run the GymConnect website
on your local machine. Instructions are provided for both
Windows and Mac.

----------------------------------------------------------------
  REQUIREMENTS
----------------------------------------------------------------

Make sure you have the following installed before starting:

  - Python 3.x        https://www.python.org/downloads/
  - pip               (comes with Python automatically)
  - MySQL             https://dev.mysql.com/downloads/mysql/
  - MySQL Workbench   https://dev.mysql.com/downloads/workbench/
    (or any MySQL client you prefer)

----------------------------------------------------------------
  STEP 1 — SET UP THE DATABASE
----------------------------------------------------------------

1. Open MySQL Workbench (or your MySQL client).

2. Create a new database called:

     gymconnect_db

   You can do this by running the following SQL query:

     CREATE DATABASE gymconnect_db;

3. Import the database dump file included in the project folder:

     File > Open SQL Script > select the .sql file provided
     Then click the lightning bolt icon to run it.

   This will create the required tables automatically.

4. Open app.py (or wherever the database connection is set)
   and make sure the credentials match your MySQL setup:

     DB_USER     = 'root'         
     DB_PASSWORD = 'MarsApp123!' 
     DB_NAME     = 'mars_gym'

----------------------------------------------------------------
  STEP 2 — OPEN TERMINAL / COMMAND PROMPT
----------------------------------------------------------------

  WINDOWS:
    Press  Windows + R  and type  cmd  then press Enter.
    OR search for "Command Prompt" in the Start menu.

  MAC:
    Press  Cmd + Space  and type  Terminal  then press Enter.

----------------------------------------------------------------
  STEP 3 — NAVIGATE TO THE PROJECT FOLDER
----------------------------------------------------------------

  In the terminal, use the cd command to go to the folder
  where you saved the project.

  EXAMPLE (Windows):
    cd C:\Users\YourName\Downloads\GymConnect

  EXAMPLE (Mac):
    cd /Users/YourName/Downloads/GymConnect

  TIP: You can drag and drop the folder into the terminal
  window after typing "cd " and it will fill in the path.

----------------------------------------------------------------
  STEP 4 — CREATE A VIRTUAL ENVIRONMENT
----------------------------------------------------------------

  A virtual environment keeps the project dependencies
  separate from the rest of your system.

  WINDOWS:
    python -m venv venv
    venv\Scripts\activate

  MAC:
    python3 -m venv venv
    source venv/bin/activate

  You should now see (venv) at the start of your terminal line.
  This means the virtual environment is active.

----------------------------------------------------------------
  STEP 5 — INSTALL DEPENDENCIES
----------------------------------------------------------------

  Run the following command to install all required packages:

  WINDOWS:
    pip install -r requirements.txt

  MAC:
    pip3 install -r requirements.txt

  This will install Flask, SQLAlchemy, and anything else
  the project needs.

  If there is no requirements.txt, install manually:

  WINDOWS:
    pip install flask flask-sqlalchemy pymysql

  MAC:
    pip3 install flask flask-sqlalchemy pymysql

----------------------------------------------------------------
  STEP 6 — RUN THE WEBSITE
----------------------------------------------------------------

  WINDOWS:
    python app.py

  MAC:
    python3 app.py

  You should see something like this in the terminal:

    * Running on http://127.0.0.1:5001
    * Press CTRL+C to quit

----------------------------------------------------------------
  STEP 7 — OPEN IN BROWSER
----------------------------------------------------------------

  Open your web browser and go to:

    http://localhost:5001

  The GymConnect website should now be running.

----------------------------------------------------------------
  STOPPING THE SERVER
----------------------------------------------------------------

  To stop the website, go back to the terminal and press:

    CTRL + C

  To deactivate the virtual environment when you're done:

    WINDOWS:  venv\Scripts\deactivate
    MAC:      deactivate
