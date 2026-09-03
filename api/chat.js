// Vercel Edge Function — proxy gọi Google Gemini API (chỉ dùng free tier)
// Bảo vệ GEMINI_API_KEY ở phía server, không lộ key trên client.
//
// Endpoint: POST /api/chat
// Body: { messages: [{role: 'user'|'model', text: string}, ...] }
// Response: { reply: string, usedModel: '<tên model đã dùng>', fallback?: true }
//
// Chọn model (Bạn chốt 03/9/2026: LUÔN ưu tiên bản Flash cao nhất, chỉ Flash, không dùng Pro):
// thử lần lượt từ bản mới nhất xuống. Bản chưa mở cho khóa API này trả 404 → tự bỏ qua,
// nên khi Google ra bản mới chỉ cần thêm 1 dòng vào đầu MODELS, không sợ hỏng chatbot.
// Bản cuối trong danh sách là bản nhẹ đã chạy ổn định, giữ làm lưới an toàn cho hạn mức free tier.
// Tất cả đều thuộc free tier — không phát sinh chi phí.

import { CHATBOT_CONTEXT } from './chatbot-context.js';

export const config = { runtime: 'edge' };

const MODELS = [
  'gemini-3.8-flash',        // bản cao nhất hiện tại (03/9/2026)
  'gemini-3.7-flash',
  'gemini-2.5-flash',
  'gemini-2.5-flash-lite',   // lưới an toàn: hạn mức free cao nhất
];

// HTTP status cần chuyển sang model kế tiếp: 404 = bản chưa mở cho khóa này; còn lại là quá tải / hết hạn mức
const FALLBACK_STATUSES = new Set([404, 429, 500, 502, 503, 504]);

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

  // Thử lần lượt từ bản Flash cao nhất xuống; bản nào 404 (chưa mở) hoặc quá tải thì sang bản kế tiếp
  let dauTien = null;
  const daThu = [];
  for (const model of MODELS) {
    const kq = await callGemini(model, truncated, apiKey);
    if (kq.ok) {
      const body = { reply: kq.reply, usedModel: model };
      if (daThu.length) {
        body.fallback = true;
        body.fallbackReason = daThu.map(x => `${x.model} lỗi ${x.status}`).join('; ');
      }
      return new Response(JSON.stringify(body), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      });
    }
    if (!dauTien) dauTien = kq;
    // Lỗi do khóa/nội dung (400/401/403) thì đổi model cũng vô ích — dừng luôn
    if (!(FALLBACK_STATUSES.has(kq.status) || kq.status === 0)) {
      return new Response(
        JSON.stringify({ error: kq.error, detail: kq.detail, usedModel: model }),
        { status: kq.status || 502, headers: { 'Content-Type': 'application/json' } }
      );
    }
    daThu.push({ model, status: kq.status });
  }

  // Mọi bản đều không dùng được
  return new Response(
    JSON.stringify({
      error: dauTien.error, detail: dauTien.detail, fallbackTried: true,
      fallbackError: daThu.map(x => `${x.model}: ${x.status}`).join('; '),
    }),
    { status: dauTien.status || 502, headers: { 'Content-Type': 'application/json' } }
  );
}
