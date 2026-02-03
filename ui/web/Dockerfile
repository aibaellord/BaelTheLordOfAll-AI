# BAEL Web UI - Production Dockerfile
FROM node:20-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build
RUN npm run build

# Production image
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config for SPA routing
RUN echo 'server { \
    listen 3000; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
    try_files $uri $uri/ /index.html; \
    } \
    location /api { \
    proxy_pass http://bael:8000; \
    proxy_http_version 1.1; \
    proxy_set_header Upgrade $http_upgrade; \
    proxy_set_header Connection "upgrade"; \
    proxy_set_header Host $host; \
    proxy_cache_bypass $http_upgrade; \
    } \
    location /ws { \
    proxy_pass http://bael:8000; \
    proxy_http_version 1.1; \
    proxy_set_header Upgrade $http_upgrade; \
    proxy_set_header Connection "upgrade"; \
    } \
    }' > /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
