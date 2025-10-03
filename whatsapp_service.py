# whatsapp_service.py - Servicio WhatsApp con clases profesionales
# REFACTORIZACIÓN CONTROLADA - LOGS MÍNIMOS

import os
import json
import requests
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Configuración logging controlado
logger = logging.getLogger(__name__)

@dataclass
class WhatsAppConfig:
    """Configuración centralizada de WhatsApp"""
    api_token: str
    phone_number_id: str
    base_url: str = "https://graph.facebook.com/v18.0"
    
    @property
    def messages_url(self) -> str:
        return f"{self.base_url}/{self.phone_number_id}/messages"
    
    @property
    def headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

class MessageSender(ABC):
    """Interface para diferentes tipos de mensajes"""
    
    @abstractmethod
    def send(self, to_number: str, config: WhatsAppConfig) -> bool:
        pass

class TextMessage(MessageSender):
    """Mensajes de texto simples"""
    
    def __init__(self, message: str):
        self.message = message
    
    def send(self, to_number: str, config: WhatsAppConfig) -> bool:
        data = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": self.message}
        }
        return self._send_request(data, config)
    
    def _send_request(self, data: Dict, config: WhatsAppConfig) -> bool:
        try:
            response = requests.post(config.messages_url, headers=config.headers, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error enviando mensaje: {str(e)[:30]}")
            return False

class ButtonMessage(MessageSender):
    """Mensajes con botones de respuesta rápida"""
    
    def __init__(self, body_text: str, buttons: List[str]):
        self.body_text = body_text
        self.buttons = buttons[:3]  # WhatsApp max 3 buttons
    
    def send(self, to_number: str, config: WhatsAppConfig) -> bool:
        button_components = [
            {
                "type": "reply",
                "reply": {
                    "id": f"btn_{i+1}",
                    "title": button[:20]  # Character limit
                }
            }
            for i, button in enumerate(self.buttons)
        ]
        
        data = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": self.body_text},
                "action": {"buttons": button_components}
            }
        }
        return self._send_request(data, config)
    
    def _send_request(self, data: Dict, config: WhatsAppConfig) -> bool:
        try:
            response = requests.post(config.messages_url, headers=config.headers, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error enviando botones: {str(e)[:30]}")
            return False

class ListMessage(MessageSender):
    """Mensajes con lista de opciones"""
    
    def __init__(self, header_text: str, body_text: str, list_items: List[str]):
        self.header_text = header_text
        self.body_text = body_text
        self.list_items = list_items[:10]  # WhatsApp max 10 items
    
    def send(self, to_number: str, config: WhatsAppConfig) -> bool:
        rows = [
            {
                "id": f"option_{i+1}",
                "title": item[:24],  # Character limit
                "description": ""
            }
            for i, item in enumerate(self.list_items)
        ]
        
        data = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": self.header_text},
                "body": {"text": self.body_text},
                "action": {
                    "button": "Ver opciones",
                    "sections": [{
                        "title": "Seleccione una opción",
                        "rows": rows
                    }]
                }
            }
        }
        return self._send_request(data, config)
    
    def _send_request(self, data: Dict, config: WhatsAppConfig) -> bool:
        try:
            response = requests.post(config.messages_url, headers=config.headers, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error enviando lista: {str(e)[:30]}")
            return False

class WhatsAppService:
    """Servicio principal de WhatsApp - Elimina if/else anidados"""
    
    def __init__(self):
        self.config = WhatsAppConfig(
            api_token=os.getenv('WHATSAPP_API_TOKEN'),
            phone_number_id=os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        )
    
    def send_text(self, to_number: str, message: str) -> bool:
        """Envía mensaje de texto simple"""
        return TextMessage(message).send(to_number, self.config)
    
    def send_buttons(self, to_number: str, body_text: str, buttons: List[str]) -> bool:
        """Envía mensaje con botones"""
        return ButtonMessage(body_text, buttons).send(to_number, self.config)
    
    def send_list(self, to_number: str, header: str, body: str, items: List[str]) -> bool:
        """Envía mensaje con lista"""
        return ListMessage(header, body, items).send(to_number, self.config)
    
    def is_configured(self) -> bool:
        """Verifica si el servicio está configurado correctamente"""
        return bool(self.config.api_token and self.config.phone_number_id)

# Instancia global del servicio
whatsapp_service = WhatsAppService()