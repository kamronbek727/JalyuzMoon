export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ ok: false });

  const TG_TOKEN = process.env.TG_TOKEN;
  const ADMIN_CHAT_ID = process.env.ADMIN_CHAT_ID;

  const { order } = req.body || {};
  if (!TG_TOKEN || !ADMIN_CHAT_ID) {
    return res.status(500).json({ ok: false, error: "Env sozlanmagan" });
  }
  if (!order) return res.status(400).json({ ok: false, error: "Order yo‘q" });

  const items = (order.items || []).map(i => `▫️ ${i.name} x ${i.qty}`).join("\n");
  const text =
`Yangi buyurtma
Ism: ${order.client_name}
Tel: ${order.client_phone}
Manzil: ${order.region}, ${order.address}

Mahsulotlar:
${items}

Jami: ${order.total}`;

  const r = await fetch(`https://api.telegram.org/bot${TG_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: ADMIN_CHAT_ID, text })
  });

  const j = await r.json();
  if (!j.ok) return res.status(500).json({ ok: false, error: j.description });

  return res.json({ ok: true });
}