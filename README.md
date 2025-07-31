# 🤖 AI Chatbot with Persistent Memory

A smart conversational AI chatbot built with Streamlit that remembers your conversations across sessions. Features dual memory storage (cloud + local) with comprehensive error handling.

## ✨ Features

- **Persistent Memory**: Remembers conversations across sessions
- **Dual Storage System**: Cloud storage (Mem0) with local fallback
- **Error Resilient**: Comprehensive error handling and graceful degradation
- **User Management**: Multiple user contexts with isolated memories
- **Real-time Chat**: Powered by Groq's fast AI models
- **Memory Management**: Clear and view stored memories
- **API Testing**: Built-in connection testing tools

## 🛠️ Technologies Used

- **Frontend**: Streamlit
- **AI Model**: Groq API (Llama3-8B)
- **Memory Storage**: Mem0 (cloud) + Local Pickle storage
- **Backend**: Python 3.8+
- **Environment**: python-dotenv
- **HTTP Client**: requests

## 📋 Prerequisites

- Python 3.8 or higher
- Groq API account and API key
- (Optional) Mem0 API account for cloud storage

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd chatbot-memory-app
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
MEM0_API_KEY=your_mem0_api_key_here  # Optional
```

### 5. Get API Keys

#### Groq API Key (Required):
1. Visit [Groq Console](https://console.groq.com/)
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy and paste into `.env` file

#### Mem0 API Key (Optional):
1. Visit [Mem0 Platform](https://mem0.ai/)
2. Sign up for an account
3. Generate API key
4. Add to `.env` file

### 6. Run the Application
```bash
streamlit run main.py
```

The app will open in your browser at `http://localhost:8501`

## 📁 Project Structure

```
chatbot-memory-app/
├── main.py              # Main Streamlit application
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
├── memory_storage.pkl   # Local memory storage (auto-generated)
└── README.md           # This file
```

## 🔧 Configuration

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Your Groq API key for AI responses |
| `MEM0_API_KEY` | No | Mem0 API key for cloud memory storage |

### Memory Storage Options
1. **Mem0 Cloud**: Requires API key, persistent across devices
2. **Local Storage**: Automatic fallback, stores in `memory_storage.pkl`

## 💻 Usage

1. **Start Chatting**: Enter your message and click "Send"
2. **User Management**: Change User ID in sidebar for different contexts
3. **Memory Management**: Clear memories using sidebar button
4. **API Testing**: Use "Test Groq API Connection" to verify setup
5. **View Memories**: Check "Memory Status" section for stored data

## 🐛 Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'mem0'"
- **Solution**: The app automatically falls back to local storage
- **Optional Fix**: `pip install mem0ai`

#### "HTTP 400 Error"
- **Cause**: Invalid API key or model issues
- **Solution**: 
  1. Verify GROQ_API_KEY in `.env`
  2. Use "Test API Connection" button
  3. Generate new API key if needed

#### "Connection Error"
- **Cause**: Network or API endpoint issues
- **Solution**: Check internet connection and try again

#### Empty Responses
- **Cause**: API quota exceeded or model issues
- **Solution**: Check Groq console for usage limits

### Debug Information
- Check the "Memory Status & Debug Info" section in the app
- View console logs for detailed error messages
- Verify environment variables are loaded correctly

## 🔒 Security Notes

- Never commit `.env` files to version control
- Keep API keys secure and rotate them regularly
- Local memory files contain conversation data - handle appropriately

## 📈 Performance

- **Response Time**: ~1-3 seconds per message
- **Memory Limit**: Unlimited local storage, check Mem0 limits for cloud
- **Concurrent Users**: Single-user application (Streamlit limitation)

## 🛣️ Roadmap

- [ ] Multi-user support
- [ ] Conversation export/import
- [ ] Custom AI model selection
- [ ] Advanced memory search
- [ ] Conversation analytics
- [ ] Docker deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 Dependencies

```txt
streamlit>=1.28.0
python-dotenv>=1.0.0
requests>=2.31.0
mem0ai>=0.1.0  # Optional
```

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter any issues:

1. Check the troubleshooting section above
2. Verify all environment variables are set correctly
3. Test API connection using built-in testing tool
4. Check console logs for detailed error messages

## 🏷️ Version

**Current Version**: 1.0.0
- ✅ Full error handling implementation
- ✅ Dual memory storage system
- ✅ Comprehensive API integration
- ✅ User-friendly interface

---

**Built with ❤️ using Streamlit and Groq AI**