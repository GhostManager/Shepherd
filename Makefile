.PHONY: build run

IMAGE=rosscdh/shepherd-domains

build:
	docker build -t ${IMAGE}:latest .

run:
	echo ""