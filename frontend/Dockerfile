# Build stage
FROM node:20-alpine as build

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies with legacy peer deps and force
# Then explicitly install ajv-related packages to fix webpack schema-utils issue
RUN npm install --legacy-peer-deps --force && \
    npm install ajv@^8.12.0 ajv-keywords@^5.1.0 --legacy-peer-deps --force

# Copy source code
COPY . .

# Build argument for backend URL
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

# Build the app with increased memory
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
