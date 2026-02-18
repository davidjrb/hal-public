exports.handler = function (context, event, callback) {
  // Log inbound so you can see it in Twilio Logs if needed
  console.log("INBOUND:", JSON.stringify({
    from: event.From,
    to: event.To,
    body: event.Body,
    messageSid: event.MessageSid,
  }));

  // Return empty TwiML = no WhatsApp auto-reply
  const twiml = new Twilio.twiml.MessagingResponse();
  return callback(null, twiml);
};
