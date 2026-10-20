# CIRUS — Makefile
.PHONY: help demo eval test seed clean docker-demo

PYTHON ?= python

help:
	@echo CIRUS — Cloud Incident Remediation & Policy Engine
	@echo.
	@echo Available commands:
	@echo   make demo     - Seed 3 realistic demo incidents and start services
	@echo   make eval     - Run benchmark evaluation harness with 10 test cases
	@echo   make test     - Run backend test suite (32 tests)
	@echo   make seed     - Populate SQLite database with 3 demo incidents
	@echo   make clean    - Remove local build and cache directories

seed:
	$(PYTHON) backend/scripts/demo_incidents.py

eval:
	$(PYTHON) backend/scripts/eval_harness.py

test:
	pytest backend/tests/

demo: seed
	@echo =====================================================================
	@echo Demo incidents successfully loaded into the database!
	@echo 1. AWS S3 Bucket Public Access Block (inc-demo-001-s3)
	@echo 2. Security Group Port 22 Open (inc-demo-002-firewall)
	@echo 3. Unencrypted RDS Database (inc-demo-003-db)
	@echo.
	@echo Starting services via docker-compose...
	@echo Access Web UI: http://localhost:3000/dashboard
	@echo Access API:    http://localhost:8000/docs
	@echo =====================================================================
	docker-compose up --build

clean:
	-rmdir /s /q .pytest_cache
	-rmdir /s /q backend\.pytest_cache
