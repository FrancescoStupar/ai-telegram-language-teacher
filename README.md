# AI Language Teacher deployed on Telegram

This project showcases an AI-driven language learning bot built using various technologies and APIs. The bot interacts with users via Telegram, providing language learning assistance through text and voice messages. Below are the key features and technical highlights of the project.

## Key Features

1. **Language Selection and Personalization**:
    - Users can select their preferred language from a variety of options.
    - The bot adapts to the user's language proficiency and personalizes responses accordingly.


2. **Text and Voice Message Handling**:
    - The bot processes both text and voice messages, providing appropriate responses.
    - Voice messages are transcribed using OpenAI's Whisper model.


3. **AI-Powered Conversations**:
    - Utilizes OpenAI's GPT-4 for generating conversational responses.
    - The bot maintains context using LangChain's ConversationBufferMemory.


4. **Text-to-Speech (TTS) Integration**:
    - Supports multiple TTS services including Google TTS and IBM Watson TTS.
    - Converts AI responses into audio messages in the user's selected language.


5. **Quiz and Vocabulary Testing**:
    - Users can take vocabulary quizzes to test their knowledge.
    - The bot tracks quiz scores and provides feedback.


6. **Subscription Management**:
    - Integrates with Stripe for handling user subscriptions.
    - Manages user access based on subscription status.


7. **Data Management and Analytics**:
    - Uses Redis for storing user data and tracking usage statistics.
    - Provides a dashboard for viewing user engagement metrics.


## Technologies Used

- **Programming Language**: Python
- **Web Framework**: Flask
- **APIs**: OpenAI, Google TTS, IBM Watson TTS, Stripe
- **Database**: Redis
- **Messaging Platform**: Telegram (using pyTelegramBotAPI)
- **Audio Processing**: FFmpeg, Pydub
- **Environment Management**: Python-dotenv