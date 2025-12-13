# Video Transcriber

Video Transcriber is a Django-based backend service for transcribing video files using multiple AI providers. It exposes a RESTful API for managing transcription jobs, user authentication, and retrieving results. The project is designed for extensibility, supporting multiple transcription providers and easy integration with frontend or other backend services.

## Features

- **Django** backend with Django REST Framework (DRF) for API endpoints
- **User authentication** (session and token-based)
- **Transcription support** for OpenAI and AssemblyAI providers
- **Asynchronous task processing** with Celery
- **SQLite** as the default database (easily switchable)
- **Extensible provider architecture** for adding new LLM/transcription services
- **Testing** with pytest
- **Modern Python packaging** with [uv](https://github.com/astral-sh/uv)


## Installation

1. **Clone the repository:**
   ```sh
   git clone <your-repo-url>
   cd video_transcriber
   ```

2. **Install dependencies using uv:**
   ```sh
   uv pip install -r pyproject.toml
   ```

3. **Apply migrations:**
   ```sh
   cd src
   python manage.py migrate
   ```

4. **Create a superuser (optional):**
   ```sh
   python manage.py createsuperuser
   ```

5. **Run the development server:**
   ```sh
   python manage.py runserver
   ```

6. **Start Celery worker (for async tasks):**
   ```sh
   celery -A backend worker --loglevel=info --pool=solo
   ```

## Usage

- Access the API at `http://localhost:8000/api/v1/`
- Authenticate using the provided authentication endpoints
- Submit video file for transcription
- Retrieve transcription results via the API

## Supported Transcription Providers

- **OpenAI** (see `transcriber/llms/open_ai.py`)
- **AssemblyAI** (see `transcriber/llms/assembly_ai.py`)

Providers are managed via the `transcriber/llms/providers.py` registry. Add new providers by implementing the base interface in `base.py`.

## Testing

- Run tests with pytest:
  ```sh
  pytest
  ```

## Development

- All source code is under the `src/` directory.
- Django settings are in `src/backend/settings.py`.
- API logic is in `src/api/`.
- Transcription logic and provider integrations are in `src/transcriber/llms/`.

## Contributing

Contributions are welcome! Please open issues or submit pull requests for new features, bug fixes, or improvements.

## License

[MIT License](LICENSE)
