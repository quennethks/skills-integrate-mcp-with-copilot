# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install -r ../requirements.txt
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/register`                                                   | Create a student account and start a session                        |
| POST   | `/auth/login`                                                      | Log in and start a session                                          |
| POST   | `/auth/logout`                                                     | End the current session                                             |
| GET    | `/auth/me`                                                         | Get the authenticated user                                          |
| POST   | `/activities/{activity_name}/signup`                               | Sign up the authenticated student                                   |
| DELETE | `/activities/{activity_name}/unregister`                           | Unregister the authenticated student                               |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

User accounts and activity data are stored in memory, which means data will be reset when the server restarts. Set `SESSION_SECRET` to a long random value and `ADMIN_EMAILS` to a comma-separated list of administrator emails before deploying. Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS.
