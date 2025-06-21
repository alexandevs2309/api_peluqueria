Barbershop Management API
A professional, modular, and scalable RESTful API built with Django REST Framework for comprehensive barbershop management. It supports user authentication, client and employee management, services, appointments, inventory, point of sale (POS), reporting, role-based access control, and advanced configuration.
Table of Contents

Overview
Key Features
Technologies
API Structure
Installation
Configuration
Usage
Main Endpoints
Authentication & Security
Testing & Coverage
Contributing
License
Contact

Overview
The Barbershop Management API provides a robust solution for managing all aspects of a barbershop, including user authentication, role-based permissions, client and employee management, service catalogs, appointment scheduling, inventory tracking, POS operations, and customizable reporting. Designed for seamless integration with modern frontends (e.g., Angular with TailwindCSS), it is extensible and optimized for performance.
Key Features

User Management: User registration, login, multi-factor authentication (MFA), and session management.
Role-Based Access Control: Granular permissions to control access for different user roles.
Client & Employee Management: Advanced tools for managing client profiles and employee schedules.
Service Catalog: Comprehensive management of services and stylist assignments.
Appointment Scheduling: Real-time availability validation and booking.
Inventory Management: Product tracking with low-stock alerts.
Point of Sale (POS): Integrated system for sales and product transactions.
Reporting: Exportable analytical reports in JSON, PDF, and Excel formats.
Branch Customization: Per-branch configuration and audit logging.
Performance Optimization: Caching with Redis for faster response times.
Security: Rate limiting, JWT-based authentication, and detailed session control.
Testing: Extensive unit and integration tests with >92% coverage.

Technologies

Python 3.13
Django 5.2
Django REST Framework
Celery for asynchronous task processing
Pytest for testing
Pillow for image handling
Redis (optional, for caching and Celery broker)
PostgreSQL or SQLite for database
JWT for authentication

API Structure



Module
Functionality



auth_api
Authentication, MFA, user management, permissions


clients_api
Client profile management


employees_api
Employee and stylist management, scheduling


services_api
Service catalog management


appointments_api
Appointment booking and management


inventory_api
Product and inventory tracking


pos_api
Point of sale and sales transactions


reports_api
Analytical report generation


roles_api
Role and permission management


settings_api
General and per-branch configuration, audit logs


Installation

Clone the repository:git clone https://github.com/alexanderdelrosario/barbershop-api.git
cd barbershop-api/backend


Set up a virtual environment:python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows


Install dependencies:pip install -r requirements.txt


Apply database migrations:python manage.py migrate


Create a superuser:python manage.py createsuperuser


Start the development server:python manage.py runserver



Configuration

Update sensitive settings in backend/settings.py or use environment variables.
Configure Celery broker (e.g., Redis).
Set up Redis for caching (recommended).
Configure email settings for password recovery and notifications.
Enable CORS for separate frontend applications.

Usage

Access the API via a frontend or tools like Postman.
Authenticate using JWT tokens to access protected endpoints.
Perform CRUD operations for clients, employees, services, and more.
Schedule appointments, process sales, and generate reports.

Main Endpoints



Category
Endpoint Examples



Auth
/api/auth/register/, /api/auth/login/, /api/auth/mfa/


Clients
/api/clients/clients/


Employees
/api/employees/employees/


Services
/api/services/services/


Appointments
/api/appointments/appointments/


Inventory
/api/inventory/products/


POS
/api/pos/sales/


Reports
/api/reports/sales/, /api/reports/appointments/


Roles
/api/roles/roles/


Settings
/api/settings/


Authentication & Security

JWT Tokens: Secure authentication for all protected endpoints.
Multi-Factor Authentication: TOTP-based MFA for enhanced security.
Rate Limiting: Protection against brute-force attacks.
Session Management: Detailed control and revocation of active sessions.
Granular Permissions: Role-based access control for precise authorization.

Testing & Coverage

Automated tests using Pytest and DRF testing utilities.
Code coverage exceeds 92%.
Run tests with:pytest --cov=apps


Execute tests before deployment or major changes.

Contributing
Contributions are welcome! Please follow these steps:

Fork the repository.
Create a feature branch (git checkout -b feature/your-feature).
Commit changes (git commit -m "Add your feature").
Push to the branch (git push origin feature/your-feature).
Open a pull request.

Ensure code quality by adhering to best practices and including tests.
License
This project is licensed under the MIT License.
Contact
Alexander del Rosario  

Email: alexanderdelrosarioperez@gmail.com  
GitHub: github.com/alexanderdelrosario

