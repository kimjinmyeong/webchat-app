# Web Chat App

This is a simple example of a multi-user single-room real-time web chat application built with aiohttp and asyncio. It allows multiple users to join a chat room and exchange messages in real-time.

## ScreenShots
<img src="https://github.com/kimjinmyeong/webchat-app/assets/84405002/9f9df036-52fd-48a5-aad7-3d97562a973a" alt="이미지" width="500" height="300">

<img src="https://github.com/kimjinmyeong/webchat-app/assets/84405002/930e8955-5b4d-4adf-bd52-6bdfe3c8bd6d" alt="이미지" width="500" height="300">


## Features

- Real-time communication using WebSocket
- Single chat room for all users

## Requirements

- Python 3.7 or higher
- aiohttp
- asyncio
- redis-py
- docker

## Installation

1. Clone the repository:

```shell
git clone https://github.com/kimjinmyeong/webchat-app.git
```

2. Change into the project directory:

```shell
cd webchat-app
```

3. Build the Docker image:

```shell
docker compose build
```

## Usage

1. Run the application using Docker Compose:

```shell
docker compose up
```

2. Open your web browser and visit `http://localhost:8080` to access the chat application.

3. Enter your username and start chatting!

## Project Structure

The project consists of the following files:

- `server.py`: The main server file that handles HTTP requests, WebSocket connections, and message broadcasting.
- `templates/index.html`: The HTML template for the home page.
- `templates/error.html`: The HTML template for the error page.
- `templates/chat.html`: The HTML template for the chat room.

