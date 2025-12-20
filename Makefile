include .env
export $(shell sed 's/=.*//' .env)

DOCKER_COMPOSE_FILE = docker-compose.yml

ifeq ($(ENV), local)
	DOCKER_COMPOSE_FILE = docker-compose.yml
else ifeq ($(ENV), dev)
	DOCKER_COMPOSE_FILE = docker-compose.yml
else
	DOCKER_COMPOSE_FILE = prod.docker-compose.yml
endif

dc-up:
	docker-compose -f $(DOCKER_COMPOSE_FILE) up -d --build

dc-up-with-logs:
	docker-compose -f $(DOCKER_COMPOSE_FILE) up --build

dc-down:
	docker-compose -f $(DOCKER_COMPOSE_FILE) down

git-update:
	@if [ "$(ENV)" = "dev" ]; then \
		git checkout dev; \
		GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa" git pull origin dev; \
	else \
		git checkout main; \
		GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa" git pull origin main; \
	fi

nginx-reload:
	sudo systemctl daemon-reload
	sudo nginx -t && sudo systemctl restart nginx

alembic-upgrade:
	docker exec app python3 alembic_cli.py upgrade

init-db:
	docker exec app python3 init_db.py

deploy:
	make git-update
	make dc-down
	make dc-up
	sleep 10 # wait for the container to start
	make alembic-upgrade
	make nginx-reload


# Ansible automation
ansible:
	ansible-playbook -i ansible/hosts ansible/playbook.yml