# Makefile para API Peluquería

up:
	docker compose -f docker-compose.prod.yml up -d

down:
	docker compose -f docker-compose.prod.yml down

build:
	docker compose -f docker-compose.prod.yml build

restart:
	docker compose -f docker-compose.prod.yml restart

logs:
	docker compose -f docker-compose.prod.yml logs -f

migrate:
	docker compose -f docker-compose.prod.yml exec web python manage.py migrate

createsuperuser:
	docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

shell:
	docker compose -f docker-compose.prod.yml exec web python manage.py shell

collectstatic:
	docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

check:
	docker compose -f docker-compose.prod.yml exec web python manage.py check --deploy

backup:
	docker exec -t api_peluqueria-master-db-1 pg_dump -U $$DB_USER $$DB_NAME > backup.sql