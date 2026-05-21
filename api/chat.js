// Vercel Edge Function — proxy gọi Google Gemini API (chỉ dùng free tier)
// Bảo vệ GEMINI_API_KEY ở phía server, không lộ key trên client.
//
// Endpoint: POST /api/chat
// Body: { messages: [{role: 'user'|'model', text: string}, ...] }
// Response: { reply: string, usedModel: 'flash-lite'|'flash', fallback?: true }
//
// Free-tier strategy:
// - Primary: gemini-2.5-flash-lite (1000 RPD free, rate quota cao nhất)
// - Fallback: gemini-2.5-flash (250 RPD free, quota tách biệt, lưu cho khi primary 429/503)
// Cả 2 đều thuộc free tier — không phát sinh chi phí.

import { CHATBOT_CONTEXT } from './chatbot-context.js';

export const config = { runtime: 'edge' };

const PRIMARY_MODEL = 'gemini-2.5-flash-lite';
const FALLBACK_MODEL = 'gemini-2.5-flash';

// HTTP status cần fallback sang model thứ 2 (upstream rate limit / overload)
const FALLBACK_STATUSES = new Set([429, 500, 502, 503, 504]);

const SYSTEM_INSTRUCTION = `Bạn là **Trợ lý thông tin Khu công nghiệp và Cụm công nghiệp tỉnh Lào Cai**, do Sở Công Thương tỉnh Lào Cai phát triển.

NHIỆM VỤ: Trả lời các câu hỏi liên quan đến 21 Khu công nghiệp, 23 Cụm công nghiệp đã thành lập và 32 Cụm công nghiệp quy hoạch trên địa bàn tỉnh Lào Cai (sau sáp nhập với Yên Bái ngày 1/7/2025), dựa trên cơ sở dữ liệu cung cấp dưới đây.

QUY TẮC TRẢ LỜI:
1. Luôn dùng tiếng Việt trang trọng, văn phong hành chính phù hợp cổng thông tin nhà nước.
2. Nếu câu hỏi nằm trong dữ liệu, trả lời chính xác, trích nguồn Quyết định / số liệu cụ thể nếu có.
3. Nếu câu hỏi vượt ngoài dữ liệu (giá thuê đất hiện tại, thủ tục đầu tư chi tiết, danh sách doanh nghiệp đang tuyển...), nói rõ "Thông tin này không có trong cơ sở dữ liệu công khai. Đề nghị liên hệ Sở Công Thương tỉnh Lào Cai (02163.857.863) hoặc Ban Quản lý các Khu công nghiệp tỉnh."
4. Phân biệt rõ Cụm công nghiệp vs Khu công nghiệp khi tên trùng (Đông Phố Mới, Bắc Duyên Hải, Minh Quân, Y Can, Đông An, Thịnh Hưng, Việt Hồng).
5. Trả lời ngắn gọn, có cấu trúc (gạch đầu dòng nếu cần). Tránh trả lời quá dài (>400 từ) trừ khi user yêu cầu chi tiết.
6. KHÔNG bịa thông tin. Nếu không chắc, nói "Tôi không có thông tin cụ thể về điều này".

CƠ SỞ DỮ LIỆU:

${CHATBOT_CONTEXT}`;


async function callGemini(model, truncated, apiKey) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
  const contents = truncated.map(m => ({
    role: m.role === 'user' ? 'user' : 'model',
    parts: [{ text: String(m.text || '').slice(0, 4000) }],
  }));
  const payload = {
    contents,
    systemInstruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
    generationConfig: { temperature: 0.4, topP: 0.9, maxOutputTokens: 1024 },
    safetySettings: [
      { category: 'HARM_CATEGORY_HARASSMENT', threshold: 'BLOCK_ONLY_HIGH' },
      { category: 'HARM_CATEGORY_HATE_SPEECH', threshold: 'BLOCK_ONLY_HIGH' },
      { category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold: 'BLOCK_ONLY_HIGH' },
      { category: 'HARM_CATEGORY_DANGEROUS_CONTENT', threshold: 'BLOCK_ONLY_HIGH' },
    ],
  };
  try {
    const upstream = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!upstream.ok) {
      const errText = await upstream.text();
      return { ok: false, status: upstream.status, error: `Gemini ${model} lỗi ${upstream.status}`, detail: errText.slice(0, 500) };
    }
    const data = await upstream.json();
    const reply = data?.candidates?.[0]?.content?.parts?.[0]?.text || '';
    if (!reply) {
      return { ok: false, status: 502, error: `Gemini ${model} trả về rỗng` };
    }
    return { ok: true, status: 200, reply };
  } catch (e) {
    return { ok: false, status: 0, error: `Lỗi kết nối Gemini ${model}`, detail: String(e).slice(0, 300) };
  }
}


export default async function handler(req) {
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405, headers: { 'Content-Type': 'application/json' },
    });
  }

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return new Response(
      JSON.stringify({ error: 'Chưa cấu hình GEMINI_API_KEY trên máy chủ. Vui lòng liên hệ quản trị viên.' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }

  let body;
  try {
    body = await req.json();
  } catch (e) {
    return new Response(JSON.stringify({ error: 'JSON không hợp lệ' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const messages = Array.isArray(body.messages) ? body.messages : [];
  if (messages.length === 0) {
    return new Response(JSON.stringify({ error: 'Thiếu messages' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }
  const truncated = messages.slice(-20);

  // Thử primary trước
  const primary = await callGemini(PRIMARY_MODEL, truncated, apiKey);
  if (primary.ok) {
    return new Response(JSON.stringify({ reply: primary.reply, usedModel: 'flash-lite' }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  }

  // Fallback sang model thứ 2 nếu primary gặp rate limit / upstream error
  const shouldFallback = FALLBACK_STATUSES.has(primary.status) || primary.status === 0;
  if (shouldFallback) {
    const fb = await callGemini(FALLBACK_MODEL, truncated, apiKey);
    if (fb.ok) {
      return new Response(
        JSON.stringify({ reply: fb.reply, usedModel: 'flash', fallback: true, fallbackReason: `${PRIMARY_MODEL} lỗi ${primary.status}` }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }
    // Cả 2 đều fail — trả lỗi primary kèm thông tin fallback
    return new Response(
      JSON.stringify({ error: primary.error, detail: primary.detail, fallbackTried: true, fallbackError: fb.error }),
      { status: primary.status || 502, headers: { 'Content-Type': 'application/json' } }
    );
  }

  // Lỗi non-fallback của primary (vd 400/401/403)
  return new Response(
    JSON.stringify({ error: primary.error, detail: primary.detail }),
    { status: primary.status || 502, headers: { 'Content-Type': 'application/json' } }
  );
}
