# Twilio WhatsApp Phishing Detection Bot (Flask)

This is a Flask app that receives WhatsApp messages via a Twilio webhook, detects URLs / phishing keywords, calls your existing `POST /check-url` API, and can save a report to MongoDB (Atlas) when the user replies `YES`.

## 1. Install

From `whatsapp_bot/`:

```bash
pip install -r requirements.txt
```

Create your environment variables:

```bash
cp .env.example .env
```

Edit `.env`:
- `API_BASE_URL` should point to your backend that implements `POST /check-url`
- `MONGODB_URI` should be your MongoDB Atlas connection string
- (Optional) `MONGODB_DB` and `MONGODB_COLLECTION` to control where reports are stored
- Set `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` (required only if you enable signature validation)

## 2. Run locally

```bash
python app.py
```

Your server starts on `http://localhost:5000` by default (or `PORT` from `.env`).

## 3. Expose webhook to Twilio

Twilio needs a public HTTPS URL. Use `ngrok`:

```bash
ngrok http 5000
```

Take the `https://xxxxx.ngrok-free.app` URL.

## 4. Configure Twilio WhatsApp Sandbox

In Twilio Console (WhatsApp Sandbox):
- Set the webhook URL for incoming messages to:
  - `https://<ngrok-url>/webhook`
- Make sure it targets POST requests.

## 5. Test

Send a WhatsApp message to your sandbox number:
- If you send a message with a URL, the bot will call your `POST /check-url` API.
- If it returns `suspicious` or `malicious`, the bot asks: `Do you want to report this scam? Reply YES`
- When the user replies `YES`, the bot saves `message_text + url` (plus status/reason) into your MongoDB `reports` collection.

## Notes

- Signature validation is off by default. To enable it, set:
  - `ENABLE_SIGNATURE_VALIDATION=true`
- If signature validation is enabled, Twilio requires the webhook URL to match exactly how it is registered.

