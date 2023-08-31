#!/bin/bash

IMAGE_NAME="poletani/api"
TAG="latest"

DOCKER_REGISTRY="docker.kvacek.cz"
CONTAINER_IMAGE="$DOCKER_REGISTRY/$IMAGE_NAME:$TAG"

docker login $DOCKER_REGISTRY
docker build -t $CONTAINER_IMAGE .
docker push $CONTAINER_IMAGE

# TODO: nahravat i config pro apache?


scp docker-compose.prod.yml michal@kvacek.cz:/var/www/poletani.cz/api/docker-compose.yml

ssh -t michal@kvacek.cz  << EOF
  cd /var/www/poletani.cz/api
  docker-compose pull
  docker-compose down --remove-orphans
  docker-compose up -d
  docker-compose exec -T api alembic upgrade head
EOF