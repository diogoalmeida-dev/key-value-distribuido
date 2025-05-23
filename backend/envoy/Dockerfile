# backend/envoy/Dockerfile
FROM envoyproxy/envoy:v1.28-latest

USER root
RUN apt-get update \
 && apt-get install -y curl \
 && rm -rf /var/lib/apt/lists/*

USER envoy
