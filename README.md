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

You can copy `.env.example` to `.env` for Docker Compose and to `.env.properties` for Spring Boot (or export the variables). If you already have a database volume, use its existing credentials. Start Docker Desktop before running Docker commands.

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
localhost:5436
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
spring.datasource.url=jdbc:postgresql://localhost:5436/petify
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

## End-to-End Tests (TestNG)

The opt-in TestNG suite starts the backend on a random HTTP port and a disposable
PostgreSQL 15 container, then runs the real Flyway migrations. Java 17 and a running
Docker daemon are required; the first run downloads dependencies and container images.
No separately running backend, development database, or `.env` credentials are needed.

Run only the end-to-end suite on Windows:

```powershell
.\mvnw.cmd -Pe2e test-compile failsafe:integration-test failsafe:verify
```

On macOS or Linux:

```sh
./mvnw -Pe2e test-compile failsafe:integration-test failsafe:verify
```

The suite covers registration, login by username and email, duplicate registrations,
incorrect credentials, pet creation and retrieval, promotion from client to owner,
required pet fields, attempts to create pets for another user, and missing pets.
Each test creates its own users through HTTP; the application and database container
are stopped after the suite, including when assertions fail. No services or repositories
are mocked. The tests use the API's current `X-User-Id` convention for pet creation.

Reports are written to `target/failsafe-reports` (including TestNG HTML and XML).
Docker or application startup failures fail the suite rather than silently skipping it.
Normal `mvnw test` still runs JUnit and excludes these end-to-end tests. To run JUnit
and the end-to-end suite together, use `mvnw verify -Pe2e`; the existing JUnit context
test still requires its usual local database configuration.

## Stress Tests

Opt-in API stress tests use JUnit and Java's HTTP client. With the backend running
on port 8081 and at least one active public listing:

```sh
.\mvnw.cmd test -Pstress
.\mvnw.cmd test -Pstress "-Dstress.users=50" "-Dstress.requests=20"
```

Normal Maven tests exclude stress tests. Four tests cover public listings, active
listings, listing details, and clinics. Each test defaults to 20 concurrent workers
making 10 requests each (200 measured requests per endpoint, plus setup requests).
Every request must return HTTP 200 and valid JSON with the expected shape or listing
ID. A failed request fails the test. Each request has a 10-second timeout and each
load phase has a two-minute deadline.

The terminal shows successful request counts and total elapsed time; JUnit reports
are in `target/surefire-reports`. This simplified suite does not calculate latency
percentiles, write CSV reports, or test login. `stress.users` (1–200),
`stress.requests` (1–1000), and `stress.baseUrl` are the only settings; the old
duration and workload settings no longer apply.

If the test reports that it cannot reach the backend, start Docker Desktop,
copy `.env.example` to `.env`, set your local database credentials, then run
`docker compose up -d` and `.\mvnw.cmd spring-boot:run`. Wait for the
`Started PetifyApplication` message before running stress tests in another terminal.
The database port is 5436 and the API port is 8081.

## Database

The project uses PostgreSQL as its primary database.

The `sql` directory contains:

| File | Purpose |
|---|---|
| `ddl.sql` | Database schema definitions |
| `dml.sql` | Initial or sample data |

The application also includes Flyway for version-controlled database migrations.

A recommended migration structure is:

```text
src/main/resources/db/migration/
├── V1__initial_schema.sql
├── V2__seed_reference_data.sql
└── V3__add_new_feature.sql
```

Once a Flyway migration has been applied, avoid editing it. Create a new migration for future schema changes.

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
- Host port `5436`
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
filters are real. There are no Mockito mocks, stubs, or Testcontainers.
JUnit runs the tests; all response assertions use MockMvc.

Create a dedicated empty PostgreSQL database and configure its connection in
PowerShell (replace the example credentials):

```powershell
$env:PETIFY_TEST_DB_URL = "jdbc:postgresql://localhost:5432/petify_test"
$env:PETIFY_TEST_DB_USERNAME = "petify_test"
$env:PETIFY_TEST_DB_PASSWORD = "your-test-password"
.\mvnw.cmd "-Dtest=ApiMvcTest" test
```

Use only a dedicated test database: Flyway runs the real migrations and seed
scripts at startup. The `mvc-test` profile excludes local/remote connection
settings, and this test disables the optional environment-file import. Each
test runs in a transaction that rolls back its data afterward; startup migrations
and seed data remain. These tests do not verify transaction commit behavior.

The suite covers signup/login, duplicate registration, authentication failures,
favorites, clinic lookup, admin access, and invalid request input. No Docker is
needed when PostgreSQL is already running. The selected command excludes the
legacy `PetifyApplicationTests` smoke test, which uses the normal app configuration.

Use `./mvnw` on macOS/Linux or `mvn` if Maven is installed. If the Windows wrapper
fails with `Cannot index into a null array`, run the same arguments using an
installed or cached `mvn.cmd`. Results are in `target/surefire-reports`.

## Academic Context

Petify was developed as a full-stack project for the **Databases** course at the Faculty of Computer Science and Engineering (FINKI).

Project page: [Petify – Databases course project](https://develop.finki.ukim.mk/projects/petify)


## Author

**Veronika Ilioska**

GitHub: [veronika-ilioska](https://github.com/veronika-ilioska)

## License

This project was created for educational purposes.
