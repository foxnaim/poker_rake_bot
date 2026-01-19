FROM node:18-alpine

WORKDIR /app

# Копируем package files
COPY package*.json ./

# Устанавливаем зависимости
RUN npm install

# Копируем исходный код
COPY . .

# Порт для React dev server
EXPOSE 3000

# Запускаем dev server
CMD ["npm", "start"]
