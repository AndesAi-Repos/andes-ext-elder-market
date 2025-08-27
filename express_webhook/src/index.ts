// express_webhook/src/index.ts (Lógica de encuesta iniciada por usuario)

import express, { Request, Response } from 'express';
const celery = require('celery-node');

const VERIFY_TOKEN = "1234567"; // <-- ¡No olvides poner tu token!

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

    const message = req.body.entry?.[0]?.changes?.[0]?.value?.messages?.[0];

    if (message) {
        const userId = message.from;
        const messageType = message.type;
        
        // Creamos un payload base que enviaremos a Python
        let taskPayload: any = { user_id: userId, type: messageType };

        // Extraemos la información relevante según el tipo de mensaje
        if (messageType === 'text') {
            taskPayload.content = message.text.body;
        } else if (messageType === 'audio') {
            taskPayload.media_id = message.audio.id;
        } else if (messageType === 'interactive' && message.interactive?.type === 'button_reply') {
            // Si el usuario presiona un botón, nos interesa el texto del botón
            taskPayload.content = message.interactive.button_reply.title;
        } else {
            console.log(`Mensaje de tipo no soportado ('${messageType}'). Ignorando.`);
            return res.sendStatus(200);
        }
        
        // Enviamos la tarea a nuestro worker de Python
        const task = client.createTask('process_feedback_task');
        task.applyAsync([taskPayload]);
        console.log('Tarea encolada para Celery:', taskPayload);
    }
    
    res.sendStatus(200);
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Servidor Webhook listo y escuchando en http://localhost:${PORT}`);
});