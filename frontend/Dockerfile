FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Dev-simple: chạy vite dev server. Production nên build + serve tĩnh (nginx).
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
