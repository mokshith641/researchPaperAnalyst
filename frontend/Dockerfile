FROM node:24-alpine

WORKDIR /app

# Install dependencies first (will copy package.json when generated)
COPY package*.json ./

RUN npm install

# Copy application code
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
