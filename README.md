# Odoo Contabilidade - Docker Compose Setup

Este projeto facilita a implantação do Odoo usando Docker, Nginx e PostgreSQL.

## 1. Pré-requisitos

- **Docker Desktop** instalado e em execução no seu sistema.

## 2. Clonando o repositório

```bash
git clone https://github.com/Brunno-Bocardo/odoo-contabilidade.git
cd odoo-contabilidade
```

## 3. Subindo os containers

Para iniciar todos os serviços em segundo plano:
```bash
docker compose up -d
```

## 4. Acessando o Odoo

Após subir os containers, acesse o sistema pelo navegador:
```
http://localhost/web/login
```

## 5. Comandos úteis do Docker

- **Parar containers:**
	```bash
	docker compose down
	```
- **Reiniciar todos os serviços:**
	```bash
	docker compose restart
	```
- **Verificar status dos containers:**
	```bash
	docker ps
	```

## 6. Dicas úteis

- Para criar novos módulos, crie um diretório em `addons`. Depois, adicione no `odoo.conf`, no parâmetro `addons_path`, o caminho até o diretório criado. Ficará dessa forma: `addons_path = /mnt/extra-addons,/mnt/extra-addons/<custom-addons>`
- Certifique-se de que as portas 80 (Nginx) e 5432 (PostgreSQL) estejam livres no seu sistema.
- Para facilitar o desenvolvimento e depuração, utilize a extensão ["Odoo Debug"](https://chromewebstore.google.com/detail/odoo-debug/hmdmhilocobgohohpdpolmibjklfgkbi) disponível para o navegador Chrome/Firefox. Ela adiciona funcionalidades extras à interface do Odoo, como modo debug, visualização de IDs e menus avançados. 


