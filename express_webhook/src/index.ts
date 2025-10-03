// express_webhook/src/index.ts (Lógica de encuesta iniciada por usuario)

import express, { Request, Response } from 'express';
const celery = require('celery-node');

const VERIFY_TOKEN = "testing_elder_survey_2025"; // Token actualizado

const client = celery.createClient(
  'redis://localhost:6379/0',
  'redis://localhost:6379/0'
);

const app = express();
app.use(express.json());

// Ruta de Verificación (sin cambios)
app.get('/webhook', (req: Request, res: Response) => {
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];
    if (mode === 'subscribe' && token === VERIFY_TOKEN) {
        console.log("¡VERIFICACIÓN EXITOSA!");
        res.status(200).send(challenge);
    } else {
        res.sendStatus(403);
    }
});

// Ruta de Recepción de Mensajes (LÓGICA ACTUALIZADA)
app.post('/webhook', (req: Request, res: Response) => {
    console.log('--- Nuevo Mensaje Recibido ---');
    console.log('Payload completo:', JSON.stringify(req.body, null, 2));

    // Enviar el payload completo de WhatsApp tal como llega
    // Python ya sabe cómo procesarlo
    const task = client.createTask('tasks.process_whatsapp_message');
    task.applyAsync([req.body]);  // Enviar payload original completo
    console.log('Payload completo enviado a Celery');
    
    res.sendStatus(200);
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Servidor Webhook listo y escuchando en http://localhost:${PORT}`);
});