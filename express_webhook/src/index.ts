// src/index.ts (VERSIÓN FINAL COMPLETA - VERIFICACIÓN + RECEPCIÓN DE MENSAJES)

import express, { Request, Response } from 'express';
// Usamos require para máxima compatibilidad
const celery = require('celery-node');

// --- 1. CONFIGURACIÓN ---
// ¡IMPORTANTE! Este token debe ser EXACTAMENTE el mismo que se pone en la página de Meta.
const VERIFY_TOKEN = "1234567"; 

// --- 2. CLIENTE CELERY ---
const client = celery.createClient(
  'redis://localhost:6379/0', 
  'redis://localhost:6379/0'  
);

const app = express();
app.use(express.json());

// --- 3. RUTA DE VERIFICACIÓN (Maneja las peticiones GET) ---
// Meta envía una petición GET a esta ruta para verificar el webhook.
app.get('/webhook', (req: Request, res: Response) => {
    console.log("Recibida petición de verificación de webhook...");

    // Extraemos los parámetros que envía Meta
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    // Verifica que el modo sea 'subscribe' y que el token coincida.
    if (mode === 'subscribe' && token === VERIFY_TOKEN) {
        console.log("¡VERIFICACIÓN EXITOSA! Respondiendo al challenge.");

        res.status(200).send(challenge);
    } else {

        console.error("Fallo en la verificación. Tokens no coinciden o modo incorrecto.");
        res.sendStatus(403); // Forbidden
    }
});

// --- 4. RUTA DE RECEPCIÓN DE MENSAJES (Maneja las peticiones POST) ---
app.post('/webhook', (req: Request, res: Response) => {
    console.log('--- Nuevo Mensaje de WhatsApp Recibido ---');
    console.log('Payload completo:', JSON.stringify(req.body, null, 2));

    const body = req.body;

    if (body.object === 'whatsapp_business_account' && body.entry && body.entry.length > 0) {
        const entry = body.entry[0];
        const changes = entry.changes[0];
        const value = changes.value;
        const message = value.messages?.[0]; 

        if (message) {
            const userId = message.from; // Número del usuario
            const messageType = message.type; // 'text', 'audio', etc.
            
            let taskPayload: any = { user_id: userId, type: messageType };

            if (messageType === 'text') {
                taskPayload.content = message.text.body;
            } else if (messageType === 'audio') {
                taskPayload.media_id = message.audio.id; // Pasa el ID del audio a Python
            } else {
                console.log(`Mensaje de tipo no soportado ('${messageType}'). Ignorando.`);
                return res.sendStatus(200);
            }
            
            // Crea y envia la tarea a nuestro worker de Python
            const task = client.createTask('process_feedback_task');
            task.applyAsync([taskPayload]);
            console.log('Tarea encolada para Celery:', taskPayload);
        } else {
            console.log("Notificación recibida, pero no contenía un mensaje de usuario.");
        }
    } else {
        console.log("Payload recibido, pero no es del tipo esperado de WhatsApp.");
    }
    
    // Responde a WhatsApp inmediatamente con un 200 OK para que sepa que se recibio el evento.
    res.sendStatus(200);
});


// --- 5. INICIAR EL SERVIDOR ---
const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Servidor Webhook listo y escuchando en http://localhost:${PORT}`);
    console.log(`URL pública de ngrok debería apuntar aquí.`);
});