import os
from twilio.rest import Client

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token  = os.environ["TWILIO_AUTH_TOKEN"]

# For Twilio Sandbox, this is typically whatsapp:<YOUR_TWILIO_NUMBER>
from_wa = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:<YOUR_TWILIO_NUMBER>")
to_wa   = os.environ["TWILIO_WHATSAPP_TO"]  # e.g. whatsapp:+15551234567

client = Client(account_sid, auth_token)

msg = client.messages.create(
    body="<YOUR_USER> test: it works ✅",
    from_=from_wa,
    to=to_wa,
)

print("Queued message SID:", msg.sid)
