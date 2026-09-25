# Petify Backend

The backend REST API for **Petify**, a full-stack platform for managing pet listings, owners, clients, reviews, favorites, and veterinary clinic workflows.

This repository contains the server-side application built with **Java**, **Spring Boot**, and **PostgreSQL**. It handles authentication, authorization, business logic, validation, data persistence, and communication with the Petify frontend.

## Features

### Authentication and authorization

- User registration and login
- Stateless authentication
- Secure password hashing with BCrypt
- Role-based endpoint protection
- Support for administrator and client accounts
- Account status management

### Users and pet owners

- Manage client profiles
- Add and manage pets
- Associate pets with their owners
- Store pet information, metadata, and documents
- Maintain owner and client relationships

### Pet listings

- Create and manage pet-related listings
- Store pricing and location information
- Control listing visibility
- Track listing availability
- Browse listing details through REST endpoints
- Administrator moderation of listings

### Favorites

- Add listings to a user's favorites
- Remove listings from favorites
- Retrieve a user's saved listings

### Reviews

- Submit reviews as authenticated users
- Retrieve reviews for owners or listings
- Enforce review authorship and relationships
- Store ratings and comments

### Veterinary clinics

- Submit veterinary clinic applications
- Review clinic applications as an administrator
- Approve or reject applications
- Separate pending applications from active clinic records

### Administrator functionality

- Manage registered clients
- Block or activate accounts
- Moderate listings
- Review veterinary clinic applications
- Access protected administration endpoints

## Technologies

- **Java 17**
- **Spring Boot 4**
- **Spring Web MVC**
- **Spring Security**
- **Spring Data JPA**
- **Hibernate**
- **PostgreSQL**
- **Flyway**
- **Maven**
- **HikariCP**
- **Lombok**
- **Docker Compose**
- **BCrypt**
- **JWT-based authentication**

## Related Repository

This repository contains the backend application.

The frontend is available here:

[Petify Frontend](https://github.com/veronika-ilioska/petify-frontend)

## Architecture

The project follows a layered architecture:

```text
Controller
    ↓
Service
    ↓
Repository
    ↓
PostgreSQL
```

### Controller layer

Receives HTTP requests, validates request data, and returns JSON responses.

### Service layer

Contains the application business logic, authorization checks, validation rules, and transactional operations.

### Repository layer

Uses Spring Data JPA to access and modify data stored in PostgreSQL.

### Domain layer

Contains the entities and relationships used to represent users, pets, listings, reviews, favorites, and veterinary clinics.

### Security layer

Handles authentication, password hashing, authorization, security filters, CORS, and protected routes.

## Project Structure

```text
petify-backend/
├── .mvn/
├── sql/
│   ├── ddl.sql
│   └── dml.sql
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/petify/petify/
│   │   └── resources/
│   └── test/
├── docker-compose.yml
├── mvnw
├── mvnw.cmd
├── pom.xml
└── README.md
```

The exact package structure under `src/main/java` may contain packages such as:

```text
config/
controller/
dto/
model/
repository/
security/
service/
```

## Prerequisites

Before running the application, install:

- **Java 17**
- **Docker Desktop**, or a local PostgreSQL installation
- **Git**

Maven does not need to be installed separately because the repository includes the Maven Wrapper.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/veronika-ilioska/petify-backend.git
cd petify-backend
```

### 2. Configure environment variables

Create a `.env` file in the project root for the local PostgreSQL container:

```env
DB_LOCAL_USERNAME=postgres
DB_LOCAL_PASSWORD=your_password
DB_LOCAL_NAME=petify
```

Do not commit real passwords or secrets to GitHub.

### 3. Start PostgreSQL with Docker Compose

```bash
docker compose up -d
```

The included Docker Compose configuration starts PostgreSQL on:

```text
localhost:5433
```

The database data is stored in a Docker volume so that it remains available after the container stops.

To check whether the container is running:

```bash
docker compose ps
```

To stop it:

```bash
docker compose down
```

To stop it and remove the stored database volume:

```bash
docker compose down -v
```

## Spring Configuration

Configure the Spring datasource in `src/main/resources/application.properties` or through environment variables.

Example local configuration:

```properties
spring.datasource.url=jdbc:postgresql://localhost:5433/petify
spring.datasource.username=${DB_LOCAL_USERNAME}
spring.datasource.password=${DB_LOCAL_PASSWORD}

spring.jpa.hibernate.ddl-auto=validate
spring.jpa.show-sql=false

spring.flyway.enabled=true
spring.flyway.locations=classpath:db/migration

server.port=8080
```

For deployed environments, prefer environment variables:

```properties
spring.datasource.url=${DATABASE_URL}
spring.datasource.username=${DATABASE_USERNAME}
spring.datasource.password=${DATABASE_PASSWORD}
```

The exact variable names should match the configuration used by the application.

## Security Configuration

The backend uses stateless authentication and protected routes.

Sensitive values such as token-signing secrets should be stored outside the source code:

```env
JWT_SECRET=replace_with_a_long_random_secret
JWT_EXPIRATION=86400000
```

A production JWT secret should be long, random, and never committed to the repository.

## Run the Application

### Windows

```bash
mvnw.cmd spring-boot:run
```

### macOS or Linux

```bash
./mvnw spring-boot:run
```

The API will normally be available at:

```text
http://localhost:8080
```

## Build the Project

### Windows

```bash
mvnw.cmd clean package
```

### macOS or Linux

```bash
./mvnw clean package
```

The generated JAR file will be stored in:

```text
target/
```

Run the packaged application with:

```bash
java -jar target/petify-0.0.1-SNAPSHOT.jar
```

## Run Tests

### Windows

```bash
mvnw.cmd test
```

### macOS or Linux

```bash
./mvnw test
```

### UI tests with Testcontainers

The Selenium UI suite starts an isolated PostgreSQL 15 container, builds and launches
the backend against it, and starts the sibling `petify-frontend` Vite project. Flyway
loads test-only seed data from `src/test/resources/db/test-seed` into the temporary
database. Docker, Java,
Node.js, Chrome or Firefox, and an installed frontend (`npm ci` in
`../petify-frontend`) are required.

From this repository:

```bash
python -m venv ui-tests/.venv
ui-tests/.venv/bin/python -m pip install -r ui-tests/requirements.txt
ui-tests/.venv/bin/python -m pytest ui-tests
```

To run against applications you have already started, use
`ui-tests/.venv/bin/python -m pytest ui-tests --external-stack`. In that mode,
`PETIFY_BASE_URL` and `PETIFY_API_URL` select the frontend and backend URLs
(defaults: `http://localhost:5173` and `http://localhost:8081`). Start the
external backend with the test seed location enabled, for example by passing
`--spring.flyway.locations=classpath:db/migration,filesystem:$PWD/src/test/resources/db/test-seed`
from this repository. Use an isolated test database for that mode.

Add `--record-video` to save an mp4 of each test (Chrome only, needs `ffmpeg`) as
`ui-tests/videos/<file>__<test>.<outcome>.mp4`, plus `all-tests.mp4` joining them in
run order. While recording, the page is sized to 1920x1000 (change it with
`--video-size WIDTHxHEIGHT`), and a bar along the bottom shows the test name and result.
`--video-dir DIR` changes the output directory.

## Database

The project uses PostgreSQL as its primary database.

The `sql` directory contains:

| File | Purpose |
|---|---|
| `ddl.sql` | Database schema definitions |
| `dml.sql` | Initial or sample data |

The application also includes Flyway for version-controlled database migrations.
Normal application runs load only `src/main/resources/db/migration`, which contains
schema and data-transformation migrations. Test runs also load
`src/test/resources/db/test-seed`, which contains sample accounts, clinics, pets,
and listings. The test seed files are not packaged in the application JAR.

The migration structure is:

```text
src/main/resources/db/migration/
├── V1__initial_schema.sql
└── ...schema migrations...
src/test/resources/db/test-seed/
├── V2__Insert_initial_data.sql
└── ...sample and UI test data...
```

**Existing databases:** Earlier versions ran the sample migrations from the main
location, including data inserts in V10. At startup, the backend recognizes this
specific legacy Flyway history and repairs it automatically before migration.
Unrelated migration errors still stop startup. The repair changes migration
history only; it does not remove sample rows already inserted. Review those rows
and their dependent records before any cleanup. New databases need no repair.

After updating a local checkout, run `./mvnw clean spring-boot:run` once so old
migration files copied into `target/classes` cannot be loaded from a stale build.

After a migration has been applied, avoid editing it in later releases; add a new
migration for future schema changes.

## API Requests

The backend exposes RESTful endpoints that exchange JSON data.

A typical protected request uses an authorization header:

```http
Authorization: Bearer <token>
```

Example login request:

```http
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

The exact routes and payloads depend on the controllers and DTOs defined in the project.

## Frontend Integration

For local development, the frontend usually runs at:

```text
http://localhost:5173
```

The backend CORS configuration must allow requests from this origin.

For deployment, add the deployed frontend address to the allowed origins instead of using a wildcard.

The frontend should use the backend base URL through an environment variable:

```env
VITE_API_BASE_URL=http://localhost:8080
```

## Docker Compose Database Configuration

The included `docker-compose.yml` uses:

- PostgreSQL 15 Alpine
- Host port `5433`
- Container port `5432`
- Environment-based database credentials
- A persistent Docker volume
- A PostgreSQL health check

This configuration starts only the local database. The Spring Boot application is run separately through Maven or the packaged JAR.

## Deployment

The backend can be deployed to platforms such as Render, Railway, Fly.io, or another Java-compatible hosting service.

Typical deployment settings:

```text
Build command:
./mvnw clean package -DskipTests

Start command:
java -jar target/petify-0.0.1-SNAPSHOT.jar
```

Required production environment variables may include:

```env
DATABASE_URL=
DATABASE_USERNAME=
DATABASE_PASSWORD=
JWT_SECRET=
FRONTEND_URL=
```

On some platforms, PostgreSQL connection URLs need to be converted to JDBC format:

```text
jdbc:postgresql://host:5432/database
```


## MockMvc tests (real application components)

`ApiMvcTest` uses Spring MVC Test with `@SpringBootTest` and
`@AutoConfigureMockMvc`. Services, repositories, password hashing, and security
filters are real. Testcontainers starts an isolated PostgreSQL 15 database,
and Flyway applies the real migrations and seed scripts. There are no Mockito
mocks or stubs. JUnit runs the tests; response assertions use MockMvc.

With Docker running, use:

```bash
./mvnw clean -Dtest=ApiMvcTest test
```

On Windows, run `.\mvnw.cmd clean "-Dtest=ApiMvcTest" test`. The `mvc-test` profile
excludes local/remote database settings, and the test disables the optional
environment-file import. `@ServiceConnection` supplies the container's connection
details to Spring. Each test runs in a transaction that rolls back its data
afterward; startup migrations and seed data remain. These tests do not verify
transaction commit behavior.

The suite covers signup/login, duplicate registration, authentication failures,
favorites, clinic lookup, admin access, and invalid request input. The selected
command runs only `ApiMvcTest`; `PetifyApplicationTests` has its own PostgreSQL
container and can run with the full Maven test suite.

Use `mvn` if Maven is installed. Results are in `target/surefire-reports`.

## Academic Context

Petify was developed as a full-stack project for the **Databases** course at the Faculty of Computer Science and Engineering (FINKI).

Project page: [Petify – Databases course project](https://develop.finki.ukim.mk/projects/petify)


## Author

**Veronika Ilioska**

GitHub: [veronika-ilioska](https://github.com/veronika-ilioska)

## License

This project was created for educational purposes.
