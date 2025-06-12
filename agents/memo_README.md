# MEMO: AI Memory Management System

An AI-based system for managing and retrieving relevant memories.

## 📖 Description

MEMO is a Python-based AI system that uses OpenAI and Qdrant to manage and retrieve relevant memories based on user queries. It provides a simple interface for interacting with the AI and retrieving responses based on stored memories.

## ✨ Features

- **AI Memory Management**: Uses OpenAI and Qdrant to manage and retrieve relevant memories based on user queries.
- **Environment Variable Configuration**: Allows for easy configuration through environment variables.

## 🛠️ Tech Stack

**Backend:**
- Python
- OpenAI
- Qdrant

**Tools:**
- python-dotenv

## 📋 Prerequisites

- Python 3.6+
- pip

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/shivansh-2003/memo.git
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 💡 Usage

### Chat with memories

This example shows how to use the `chat_with_memories` function to retrieve a response based on a user message and stored memories.

```Python
message = 'Hello, world!'
response = chat_with_memories(message)
print(response)
```

## 📁 Project Structure

```
qdrant_mem0.py
bacic_memo.py
requirements.txt
app.py
```

- **qdrant_mem0.py**: Handles the configuration and interaction with Qdrant.
- **bacic_memo.py**: Handles the basic memory management without Qdrant.
- **requirements.txt**: Contains the list of Python dependencies.
- **app.py**: Main application file that handles AI memory management.

## 🔧 Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
MODEL_CHOICE
QDRANT_URL
QDRANT_API_KEY
```

## 🤝 Contributing

- Fork the repository
- Create a new branch
- Make your changes
- Submit a pull request

## 📄 License

MIT License

## 👤 Author

shivansh-2003


---

⭐ Don't forget to star this repository if you found it helpful!
