# Clippy - Autonomous Video Repurposing Agent 🎬✂️

> Transform long-form content into viral short clips across YouTube Shorts, TikTok, and Instagram Reels with AI-powered automation.

## 🌟 Features

- **🎥 Automated Video Processing**: Download, transcribe, and analyze content
- **🤖 AI-Powered Highlight Detection**: Find viral moments using offline LLM analysis
- **✂️ Smart Clip Generation**: Create optimized clips with subtitles and effects
- **📱 Multi-Platform Publishing**: Automated posting to YouTube Shorts, TikTok, Instagram Reels
- **📊 Performance Analytics**: Track engagement and optimize content strategy
- **🔒 Privacy-First**: Offline AI processing, local data storage
- **💰 Cost-Efficient**: Designed for free-tier and local deployment
## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- FFmpeg
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd clippy
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download AI models** (first run will download automatically)
   ```bash
   python -c "from src.ai.llm_analyzer import LLMAnalyzer; LLMAnalyzer({'model_name': 'orca-mini-3b-gguf2-q4_0.gguf'})"
   ```

4. **Configure settings**
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your platform credentials
   ```

5. **Run Clippy**
   ```bash
   # Process a single video
   python main.py --url "https://youtube.com/watch?v=VIDEO_ID"
   
   # Start scheduler mode
   python main.py --scheduler
   
   # Batch process multiple videos
   python main.py --batch videos.txt
   ```

## 🔧 Configuration

Edit `config.yaml` to customize:

```yaml
video:
  download_quality: "720p"
  clip_duration_min: 30
  clip_duration_max: 60

platforms:
  youtube:
    enabled: true
    client_id: "your-client-id"
    client_secret: "your-client-secret"
  
  tiktok:
    enabled: true
    username: "your-username"
    password: "your-password"
  
  instagram:
    enabled: true
    username: "your-username" 
    password: "your-password"

ai:
  model_name: "orca-mini-3b-gguf2-q4_0.gguf"
  highlight_threshold: 0.7
```

## 🎯 Usage Examples

### Single Video Processing
```bash
python main.py --url "https://youtube.com/watch?v=dQw4w9WgXcQ"
```

### Batch Processing
Create `videos.txt`:
```
https://youtube.com/watch?v=VIDEO1
https://youtube.com/watch?v=VIDEO2
https://youtube.com/watch?v=VIDEO3
```

Run batch:
```bash
python main.py --batch videos.txt
```

### Scheduler Mode
```bash
python main.py --scheduler
```

### Analytics and Optimization
```bash
python main.py --analytics
```

## 🏗️ Architecture

```
clippy/
├── main.py                    # Entry point and CLI
├── config.yaml               # Configuration file
├── src/
│   ├── core/                  # Core processing modules
│   │   ├── video_processor.py      # Video download & transcription
│   │   ├── content_analyzer.py     # AI-powered content analysis
│   │   └── platform_manager.py    # Multi-platform coordination
│   ├── ai/                    # AI and machine learning
│   │   ├── llm_analyzer.py         # Offline LLM analysis
│   │   ├── engagement_tracker.py   # Performance analytics
│   │   └── optimization_engine.py  # Strategy optimization
│   ├── platforms/            # Platform-specific handlers
│   │   ├── youtube_shorts.py      # YouTube Shorts API
│   │   ├── tiktok_poster.py       # TikTok automation
│   │   └── instagram_reels.py     # Instagram Reels API
│   └── utils/                # Utilities and helpers
│       ├── config.py              # Configuration management
│       ├── file_handler.py        # File operations
│       └── scheduler.py           # Task scheduling
└── data/                     # Local data storage
    ├── videos/               # Downloaded videos
    ├── clips/               # Generated clips
    └── analytics/           # Performance data
```

## 🔐 Platform Setup

### YouTube Shorts
1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing one

2. **Enable YouTube Data API v3**
   - Go to APIs & Services → Library
   - Search for "YouTube Data API v3" and enable it

3. **Create OAuth 2.0 Credentials**
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → "OAuth 2.0 Client IDs"
   - Configure OAuth consent screen if prompted
   - Select "Desktop application" as application type
   - Download the JSON credentials file

4. **Add credentials to your project**
   - Save the downloaded JSON file as `youtube_credentials.json` in your clippy folder
   - The config.yaml already references this file

### TikTok
1. Add username/password to `config.yaml`
2. First run will require manual 2FA verification
3. Session cookies will be saved for future use

### Instagram Reels
1. Add username/password to `config.yaml`
2. Enable "Less Secure Apps" or use App Password
3. Consider using a dedicated business account

## 📊 Analytics & Optimization

Clippy includes powerful analytics to optimize your content strategy:

- **Performance Tracking**: Engagement rates, views, likes across platforms
- **Trend Analysis**: Identify best-performing content types and posting times
- **AI Optimization**: Automatically adjust content strategy based on performance
- **Viral Prediction**: Score clips for viral potential before posting

## 🐳 Docker Deployment

### Quick Start with Docker
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f clippy

# Stop
docker-compose down
```

### Production Deployment
```bash
# Run with database and caching
docker-compose --profile with-database --profile with-redis up -d
```

## 🔧 Advanced Configuration

### Custom AI Models
```yaml
ai:
  model_name: "custom-model.gguf"
  model_path: "/path/to/models"
  gpu_acceleration: true
```

### Webhook Integration
```yaml
webhooks:
  enabled: true
  success_url: "https://your-app.com/webhook/success"
  error_url: "https://your-app.com/webhook/error"
```

### Advanced Scheduling
```yaml
scheduler:
  max_videos_per_day: 10
  posting_times:
    youtube: ["09:00", "15:00", "20:00"]
    tiktok: ["12:00", "17:00", "21:00"]
    instagram: ["10:00", "14:00", "19:00"]
```

## 🛠️ Development

### Setup Development Environment
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Code formatting
black src/
flake8 src/
```

### Adding New Platforms
1. Create new platform handler in `src/platforms/`
2. Implement required methods: `post_video()`, `get_stats()`
3. Add platform configuration to `config.yaml`
4. Register platform in `platform_manager.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## � License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Legal Notice

- Respect platform terms of service
- Ensure you have rights to content you're repurposing
- Use automation responsibly to avoid account restrictions
- Consider rate limiting for platform compliance

## 🆘 Support

- 📖 [Documentation](./docs/)
- 🐛 [Issue Tracker](./issues)
- 💬 [Discussions](./discussions)
- 📧 Email: support@clippy-agent.com

## 🙏 Acknowledgments

- OpenAI Whisper for transcription
- GPT4All for offline LLM processing
- FFmpeg for video processing
- All the amazing open-source libraries that make this possible

---

**Made with ❤️ for content creators who want to maximize their reach across platforms**

Contributions welcome! Please read CONTRIBUTING.md for guidelines.
