# Gutenberg-Ingestion-API

We will be using this repository throughout the semester. Your job this week is to setup the continuous integration / continuous deployment (CI/CD) process between GitHub and DockerHub. Your responsibility throughout the semester is to ensure that this deployment process is always working. You may sometimes fail security scans and will need to fix the issues as needed. 

## Project Overview

The `Gutenberg-Ingestion-API` is a FastAPI application designed for the ingestion pipeline of the Gutenberg system. It processes user requests and passes them to Bytewax dataflows for processing. The application integrates with Kafka and Debezium to manage data flow and change data capture. The API also handles user management and authentication, connecting with the frontend Next.js application that users interact with.

When you create a resource using the API at `localhost:8000/docs`, the information is added to the database. Debezium captures this change and produces the information to a Kafka topic, which the dataflow repository's initial gateway dataflow consumes.

## Steps to Project Setup

1. **Setup the project locally**
    * Fork the repository to your GitHub account.
    * Clone the repository to your local machine.

2. **Setup the virtual environment**
    * Go into the project directory and create the virtual environment: `python3 -m venv venv` or `python -m venv venv`
    * Activate the virtual environment: `source venv/bin/activate`

3. **Create a local .env file with your [MailTrap](https://mailtrap.io/) SMTP settings**
    * Mailtrap allows you to view emails when you test the site manually. When running pytest, the system uses a Mock to simulate sending emails but doesn't actually send them. You will need to sign up for a free Mailtrap account. Check that when you register the *2nd user* that it sends a verification email. The first user is the admin user and doesn't require email verification.

4. **Run the project**
    * `docker compose up --build` <- you must have it running locally like this to run any commands. Open up multiple terminals for other commands. Press CTRL C to stop or CMD C on Mac to stop.
    * Set up PGAdmin at `localhost:5050` (see docker compose for login details). You need to add the server.
    * View logs for the app: `docker compose logs fastapi -f` <- do this in another window.
    * Run tests: `docker compose exec fastapi pytest` <- try running specific tests or tests in folders i.e. `docker compose exec fastapi pytest tests/test_services`

5. **Alembic**
    * When you run Pytest, it deletes the user table but doesn't remove the Alembic table. This causes Alembic to get out of sync and you won't be able to manually test the API.
    * To resolve this, drop the Alembic table and run the migration (`docker compose exec fastapi alembic upgrade head`) when you want to manually test the site through `http://localhost/docs`.
    * If you change the database schema, delete the Alembic migration, the Alembic table, and the users table. Then, regenerate the migration using the command: `docker compose exec fastapi alembic revision --autogenerate -m 'initial migration'`.
    * Since there is no real user data currently, you don't need to worry about database upgrades, but Alembic is still required to install the database tables.

6. **Dockerhub Setup**
    * Set the project up with all of the DockerHub info (dockerhub username and token) added to the production environment secret to enable the GitHub action to push to Dockerhub successfully.
    * Edit the `.github/workflows/production.yml` GitHub Action to change the Dockerhub repo on lines 76, 78, 85 from `kaw393939/is690_summer2024` to your own Dockerhub repo. Once you have these, you need to work to get the repo deploying to Dockerhub by pushing to GitHub and seeing that action turns green.

## Additional Information

- **Kafka & Debezium Integration:** This project uses Kafka and Debezium to handle data ingestion and change data capture. When a resource is created via the API, Debezium produces the change to a Kafka topic that the initial gateway dataflow consumes.
- **Kafka Web UI:** The Kafka web UI can be accessed at `localhost:8080` to view messages Debezium sends to Kafka.
- **API Documentation:** Visit `http://localhost:8000/docs` to interact with the API endpoints.
- **Frontend Integration:** The Gutenberg-Ingestion-API connects with the frontend Next.js application, managing user authentication and providing data to the frontend.
```