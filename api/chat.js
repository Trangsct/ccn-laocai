// Vercel Edge Function — proxy gọi Google Gemini API
// Bảo vệ GEMINI_API_KEY ở phía server, không lộ key trên client.
//
// Endpoint: POST /api/chat
// Body: { messages: [{role: 'user'|'model', text: string}, ...] }
// Response: { reply: string }
//
// Setup: thêm env var GEMINI_API_KEY vào Vercel project trước khi deploy.
// (Dashboard → Settings → Environment Variables, hoặc `vercel env add GEMINI_API_KEY production`)

import { CHATBOT_CONTEXT } from './chatbot-context.js';

export const config = { runtime: 'edge' };

const MODEL = 'gemini-2.0-flash';
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`;

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


export default async function handler(req) {
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' },
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

  // Giới hạn 20 lượt gần nhất để tránh request quá lớn
  const truncated = messages.slice(-20);

  // Convert sang Gemini "contents" format
  const contents = truncated.map(m => ({
    role: m.role === 'user' ? 'user' : 'model',
    parts: [{ text: String(m.text || '').slice(0, 4000) }],
  }));

  const payload = {
    contents,
    systemInstruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
    generationConfig: {
      temperature: 0.4,
      topP: 0.9,
      maxOutputTokens: 1024,
    },
    safetySettings: [
      { category: 'HARM_CATEGORY_HARASSMENT', threshold: 'BLOCK_ONLY_HIGH' },
      { category: 'HARM_CATEGORY_HATE_SPEECH', threshold: 'BLOCK_ONLY_HIGH' },
      { category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold: 'BLOCK_ONLY_HIGH' },
      { category: 'HARM_CATEGORY_DANGEROUS_CONTENT', threshold: 'BLOCK_ONLY_HIGH' },
    ],
  };

  try {
    const upstream = await fetch(`${GEMINI_URL}?key=${apiKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!upstream.ok) {
      const errText = await upstream.text();
      return new Response(
        JSON.stringify({ error: `Gemini API lỗi ${upstream.status}`, detail: errText.slice(0, 500) }),
        { status: upstream.status, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const data = await upstream.json();
    const reply = data?.candidates?.[0]?.content?.parts?.[0]?.text || 'Xin lỗi, tôi chưa thể trả lời câu hỏi này.';

    return new Response(JSON.stringify({ reply }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (e) {
    return new Response(
      JSON.stringify({ error: 'Lỗi kết nối Gemini API', detail: String(e).slice(0, 300) }),
      { status: 502, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
