# Atlas Web App - Industrial Infrastructure Portal

> **⚠️ WARNING: EDUCATIONAL AND RESEARCH USE ONLY**
> 
> This project contains intentional security vulnerabilities and patterns designed for red-teaming research, phishing simulation testing (e.g., with Evilginx), and cybersecurity education. 
> 
> **DO NOT deploy this application to a production environment.** 
> **DO NOT use this software for any unauthorized or illegal activities.**
> 
> The authors and contributors are not responsible for any misuse of this software. By using this repository, you agree to use it only in legal, ethical, and authorized environments.

## Overview

Atlas Web App is a simulated "Atlas Construction" industrial portal. It is built using Flask and is designed to demonstrate various security concepts, including:

- **Session and JWT handling**: Configured to show how session cookies and JWTs can be intercepted in MITM scenarios.
- **Insecure Defaults**: Demonstrates common misconfigurations in web applications.
- **Red-Teaming Scenarios**: Specifically tailored for use in controlled training environments for capturing credentials and session artifacts.

## Features

- **Flask Backend**: Core logic and API endpoints.
- **SQLite Database**: Local database for user credentials and role management.
- **Dockerized Environment**: Easily deployable using Docker and Docker Compose.
- **Insecure Configurations**: Includes CORS broad origins and relaxed cookie flags for demonstration purposes.

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Deployment

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd atlas-webapp
   ```

2. Start the container:
   ```bash
   docker-compose up --build
   ```

3. Access the portal:
   - URL: `http://localhost:5000` (or as configured in your environment)

## Project Structure

- `app.py`: Main Flask application containing logic and routes.
- `Dockerfile`: Instructions for building the application container.
- `docker-compose.yml`: Orchestration for the web service and its dependencies.
- `entrypoint.sh`: Startup script for the container service.

## Security Disclaimer

This application is **insecure by design**. It includes:

1. **Hardcoded Secrets**: Plaintext secret keys for sessions and JWTs.
2. **Missing Security Headers**: Some headers are intentionally omitted or relaxed.
3. **Broad CORS Policies**: Allows any origin to facilitate research into cross-origin attacks.

Utilize this project as a target for learning vulnerability assessment, penetration testing, and red-teaming methodologies.
