# Deepfake Detection SaaS

A professional AI-powered image authenticity analyzer with freemium business model.

## Features

- **AI-powered Analysis**: Detect AI-generated images, deepfakes, and manipulations
- **Freemium Model**: 1 free scan per day, unlimited with Premium
- **Stripe Payments**: Secure subscription handling
- **User Management**: SQLite database for user tracking
- **Modern Web Interface**: FastAPI backend with responsive frontend

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Database**: SQLite
- **Payments**: Stripe
- **Hosting**: Strato (or any Python-compatible hosting)

## Setup

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set Stripe keys as environment variables
4. Run: `uvicorn app.main:app --reload`

## Deployment

Ready for deployment on Strato, Railway, or any Python hosting platform.

## License

Commercial SaaS product - All rights reserved.
