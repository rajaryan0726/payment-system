from typing import Optional
from pydantic import BaseModel


class WebhookAck(BaseModel):
    status: str = "ok"
    event_id: str
    message: str = "Webhook received and verified successfully"
    duplicate: bool = False
