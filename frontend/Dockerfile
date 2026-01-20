FROM node:18-alpine

WORKDIR /app

# Копируем package files
COPY package*.json ./

# Устанавливаем зависимости (с cache bust)
RUN npm install && npm install axios react-router-dom recharts

# Копируем исходный код
COPY . .

# Порт для React dev server
EXPOSE 3000

# Запускаем dev server
CMD ["npm", "start"]
