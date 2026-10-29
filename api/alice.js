const PROTOCOL_VERSION = '1.0';
const MAX_RESPONSE_CHARS = 950;
const MAX_HISTORY_MESSAGES = 8; // 4 коротких обмена user/model
const GEMINI_TIMEOUT_MS = 3200;

const SYSTEM_INSTRUCTION = `Ты — дружелюбный русскоязычный помощник внутри голосового навыка Алисы.
Отвечай по-русски, естественно и кратко: обычно 1–4 предложения, без Markdown-таблиц, длинных списков и декоративных символов, которые неудобно озвучивать.
Если пользователь просит подробности, всё равно учитывай ограничения голосового ответа. Не утверждай, что у тебя есть доступ к интернету или данным в реальном времени, если это не предоставлено явно.`;

function aliceResponse(text, options = {}) {
  return {
    response: {
      text: truncateForAlice(text || 'Не получилось подготовить ответ. Попробуй ещё раз.'),
      end_session: Boolean(options.endSession),
    },
    session_state: { history: options.history || [] },
    version: PROTOCOL_VERSION,
  };
}

function truncateForAlice(value) {
  const text = String(value).replace(/\u0000/g, '').trim();
  if (text.length <= MAX_RESPONSE_CHARS) return text || 'Я здесь. Что хочешь узнать?';
  const shortened = text.slice(0, MAX_RESPONSE_CHARS - 1);
  const boundary = Math.max(shortened.lastIndexOf('. '), shortened.lastIndexOf('! '), shortened.lastIndexOf('? '));
  return (boundary > MAX_RESPONSE_CHARS * 0.65 ? shortened.slice(0, boundary + 1) : shortened.trimEnd() + '…').trim();
}

function readRequestBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string') return JSON.parse(req.body);
  return {};
}

function getUserText(body) {
  const request = body?.request || {};
  const text = request.original_utterance || request.command || request.payload?.text || '';
  return String(text).trim().slice(0, 4000);
}

function validHistory(input) {
  if (!Array.isArray(input)) return [];
  return input
    .filter((item) => item && ['user', 'model'].includes(item.role) && typeof item.text === 'string')
    .slice(-MAX_HISTORY_MESSAGES)
    .map((item) => ({ role: item.role, text: item.text.slice(0, 2000) }));
}

async function askGemini(userText, history) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) throw new Error('GEMINI_API_KEY is not configured');

  const model = process.env.GEMINI_MODEL || 'gemini-3.5-flash-lite';
  const contents = [
    ...history.map((item) => ({ role: item.role, parts: [{ text: item.text }] })),
    { role: 'user', parts: [{ text: userText }] },
  ];
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), GEMINI_TIMEOUT_MS);

  try {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
          contents,
          generationConfig: {
            temperature: 0.65,
            maxOutputTokens: 220,
          },
        }),
      },
    );

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      // Log only status/model; never log the key, full URL, or user prompt.
      console.error('Gemini API error:', response.status, model);
      throw new Error(`Gemini API returned ${response.status}`);
    }

    const answer = data?.candidates?.[0]?.content?.parts
      ?.map((part) => typeof part.text === 'string' ? part.text : '')
      .join('')
      .trim();

    if (!answer) throw new Error('Gemini returned an empty answer');
    return answer;
  } finally {
    clearTimeout(timeout);
  }
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method Not Allowed. Send a POST request.' });
  }

  let body;
  try {
    body = readRequestBody(req);
  } catch {
    return res.status(400).json({ error: 'Invalid JSON body' });
  }

  // Optional guard: set this after creating the skill in Yandex Dialogs.
  // Yandex sends session.skill_id with each request.
  const expectedSkillId = process.env.ALICE_SKILL_ID;
  const receivedSkillId = body?.session?.skill_id;
  if (expectedSkillId && receivedSkillId !== expectedSkillId) {
    return res.status(403).json(aliceResponse('Этот навык не настроен для такого запроса.'));
  }

  const text = getUserText(body);
  const sessionIsNew = Boolean(body?.session?.new);
  const history = sessionIsNew ? [] : validHistory(body?.state?.session?.history);

  if (!text) {
    return res.status(200).json(aliceResponse(
      'Привет! Я помощник на базе Gemini. Задай вопрос, попроси объяснить сложную тему или придумать идею.',
      { history },
    ));
  }

  if (/^(помощь|что ты умеешь|что ты можешь|help)$/i.test(text)) {
    return res.status(200).json(aliceResponse(
      'Я могу отвечать на вопросы, объяснять сложные темы, помогать с текстами, идеями и планированием. Просто скажи, что нужно.',
      { history },
    ));
  }

  if (/^(пока|до свидания|завершить|закончить|выход|хватит)$/i.test(text)) {
    return res.status(200).json(aliceResponse('Пока! Буду здесь, когда понадоблюсь.', {
      endSession: true,
      history: [],
    }));
  }

  try {
    const answer = await askGemini(text, history);
    const updatedHistory = [
      ...history,
      { role: 'user', text },
      { role: 'model', text: answer },
    ].slice(-MAX_HISTORY_MESSAGES);

    return res.status(200).json(aliceResponse(answer, { history: updatedHistory }));
  } catch (error) {
    if (error?.name === 'AbortError') {
      console.warn('Gemini request timed out');
    } else {
      console.error('Could not complete Gemini request:', error?.message || 'unknown error');
    }

    return res.status(200).json(aliceResponse(
      'Извини, Gemini сейчас отвечает слишком медленно или недоступен. Повтори вопрос, пожалуйста.',
      { history },
    ));
  }
}
