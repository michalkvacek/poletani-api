#!/bin/bash

IMAGE_NAME="poletani/api"
TAG="latest"

DOCKER_REGISTRY="docker.kvacek.cz"
CONTAINER_IMAGE="$DOCKER_REGISTRY/$IMAGE_NAME:$TAG"

docker login $DOCKER_REGISTRY

docker build -t $CONTAINER_IMAGE .
docker push $CONTAINER_IMAGE
