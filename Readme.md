Barbershop Management API

A professional, modular, and scalable RESTful API built with Django REST Framework for comprehensive barbershop management. Streamline operations with features for authentication, client and employee management, services, appointments, inventory, point of sale (POS), reporting, and role-based access control.

🚀 Overview
The Barbershop Management API is designed to manage all aspects of a barbershop with a robust, extensible, and secure backend. It integrates seamlessly with modern frontends (e.g., Angular with TailwindCSS) and supports multi-branch customization, advanced analytics, and high-performance operations.

✨ Key Features

🔐 User Authentication: Secure registration, login, and multi-factor authentication (MFA).
👥 Role-Based Access: Granular permissions for precise control over user access.
🧑‍💼 Client & Employee Management: Manage profiles, schedules, and assignments.
💇 Service Catalog: Organize and assign services to stylists.
📅 Appointment Scheduling: Real-time availability and booking validation.
📦 Inventory Tracking: Monitor products with low-stock alerts.
💳 Point of Sale (POS): Process sales and manage transactions.
📊 Reporting: Exportable reports in JSON, PDF, and Excel formats.
🏬 Branch Customization: Configure settings per branch with audit logging.
⚡ Performance: Optimized with Redis caching.
🛡️ Security: JWT tokens, rate limiting, and session management.
🧪 Testing: >92% test coverage with Pytest.


🛠️ Technologies



Technology
Version/Description



🐍 Python
3.13


🌐 Django
5.2


⚙️ Django REST Framework
API development


🥒 Celery
Asynchronous task processing


🧪 Pytest
Testing framework


🖼️ Pillow
Image handling


🗄️ Redis
Optional caching and Celery broker


🗃️ Database
PostgreSQL (recommended) or SQLite



📂 API Structure



Module
Functionality



auth_api
🔐 Authentication, MFA, user & permission management


clients_api
👤 Client profile management


employees_api
👷 Employee scheduling and management


services_api
💇 Service catalog management


appointments_api
📅 Appointment booking and management


inventory_api
📦 Product and inventory tracking


pos_api
💳 Point of sale and sales transactions


reports_api
📊 Analytical report generation


roles_api
🎭 Role and permission management


settings_api
⚙️ Branch configuration and audit logs



📥 Installation

Clone the repository:
git clone https://github.com/alexanderdelrosario/barbershop-api.git
cd barbershop-api/backend


Set up a virtual environment:
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows


Install dependencies:
pip install -r requirements.txt


Apply migrations:
python manage.py migrate


Create a superuser:
python manage.py createsuperuser


Run the server:
python manage.py runserver




⚙️ Configuration

📝 Update backend/settings.py or use environment variables for sensitive settings.
🥒 Configure Celery broker (e.g., Redis).
🗄️ Set up Redis for caching (recommended).
📧 Configure email for password recovery and notifications.
🌐 Enable CORS for separate frontend applications.


🖥️ Usage

Access the API via a frontend or tools like Postman.
Authenticate with JWT tokens for protected endpoints.
Perform CRUD operations for clients, employees, services, etc.
Schedule appointments, process sales, and generate reports.


🌐 Main Endpoints



Category
Example Endpoints



🔐 Auth
/api/auth/register/, /api/auth/login/, /api/auth/mfa/


👤 Clients
/api/clients/clients/


👷 Employees
/api/employees/employees/


💇 Services
/api/services/services/


📅 Appointments
/api/appointments/appointments/


📦 Inventory
/api/inventory/products/


💳 POS
/api/pos/sales/


📊 Reports
/api/reports/sales/, /api/reports/appointments/


🎭 Roles
/api/roles/roles/


⚙️ Settings
/api/settings/



🔒 Authentication & Security

JWT Tokens: Secure endpoint access.
MFA: TOTP-based multi-factor authentication.
Rate Limiting: Protection against brute-force attacks.
Session Control: Monitor and revoke active sessions.
Permissions: Granular role-based access control.


🧪 Testing & Coverage

Automated tests with Pytest and DRF utilities.
92%+ code coverage.
Run tests:pytest --cov=apps




🤝 Contributing
We welcome contributions! Follow these steps:

Fork the repository.
Create a feature branch: git checkout -b feature/your-feature.
Commit changes: git commit -m "Add your feature".
Push to the branch: git push origin feature/your-feature.
Open a pull request.

Please adhere to coding standards and include tests.

📜 License
This project is licensed under the MIT License.

📬 Contact
Alexander del Rosario  

📧 Email: alexanderdelrosarioperez@gmail.com  
🐙 GitHub: https://github.com/alexandevs2309/


⭐ Star this repository if you find it useful!
