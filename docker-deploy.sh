#!/bin/bash

# Ensure the database file exists so Docker binds a file instead of creating a directory
touch db.sqlite3

# Ensure media and backups directories exist
mkdir -p media
mkdir -p backups

echo "Starting Docker deployment..."
# Build and start the container
docker-compose up -d --build

echo "Deployment successful! The application is running on port 8000."
