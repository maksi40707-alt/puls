# app.py
from flask import Flask, render_template, request, jsonify
import os, smtplib, json
from email.message import EmailMessage
from email.utils import make_msgid
import pathlib
from pathlib import Path

app = Flask(__name__)

BRAND_RED = "#dc2626"
INK = "#111827"
MUTED = "#6b7280"
BORDER = "#e5e7eb"
CARD = "#ffffff"
BG = "#f9fafb"

# Gmail из ENV
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_APP_PASS")
SENDER     = os.getenv("SENDER_EMAIL", GMAIL_USER)
ADMIN      = os.getenv("ADMIN_EMAIL", GMAIL_USER)

def send_email_gmail(to_addr: str, subject: str, text: str, html: str | None = None,
                     reply_to: str | None = None, inline_images: dict[str, bytes] | None = None):
    if not GMAIL_USER or not GMAIL_PASS:
        raise RuntimeError("ENV GMAIL_USER / GMAIL_APP_PASS не заданы")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = to_addr
    if reply_to:
        msg["Reply-To"] = reply_to

    # Plain text (обязательно как fallback)
    msg.set_content(text or "")

    if html:
        # Добавим альтернативную HTML-часть
        msg.add_alternative(html, subtype="html")
        # Встраиваем inline-картинки (CID)
        if inline_images:
            # последняя (HTML) часть — это альтернативный вариант
            html_part = msg.get_payload()[-1]
            for name, data_bytes in inline_images.items():
                cid = make_msgid(domain="puls.local")  # <random@puls.local>
                # заменим плейсхолдер {cid:name} на реальный cid без угловых скобок
                html_str = html_part.get_content()
                html_str = html_str.replace(f"cid:{name}", f"cid:{cid[1:-1]}")
                html_part.set_content(html_str, subtype="html")

                html_part.add_related(data_bytes, maintype="image", subtype="png", cid=cid)

    # Отправка (STARTTLS)
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(GMAIL_USER, GMAIL_PASS)
        smtp.send_message(msg)


@app.get("/")
def home():
    return render_template("index.html")

@app.post("/api/debug-dump")
def debug_dump():
    data = request.get_json(silent=True) or request.form.to_dict()

    print(">>> DEBUG DUMP (Formdaten als JSON):")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    user_email = data.get("email")

    # Текстовая версия (fallback, на случай клиента без HTML)
    text_fallback = (
        "Вітаємо!\n\n"
        "Дякуємо за заявку на безкоштовне тренування PULS у Вроцлаві.\n"
        f"Дитина: {data.get('childName','')}\n"
        f"Вік: {data.get('childAge','')}\n"
        f"Телефон: {data.get('phone','')}\n"
        f"Повідомлення: {data.get('message','')}\n\n"
        "Ми зв'яжемося з вами найближчим часом. ⚽"
    )

    # Готовим HTML с плейсхолдером cid:logo
    html_user = build_user_email_html(data, logo_cid="logo")

    # Читаем логотип как bytes
    logo_path = Path("static/tg_image_110262498-no-bg-preview (carve.photos).png")
    logo_bytes = logo_path.read_bytes() if logo_path.exists() else None

    # 1) Письмо пользователю
    if user_email:
        send_email_gmail(
            to_addr=user_email,
            subject="PULS — підтвердження заявки",
            text=text_fallback,
            html=html_user,
            reply_to=ADMIN,
            inline_images={"logo": logo_bytes} if logo_bytes else None
        )

    # 2) Письмо админу — можно оставить простым (или сделать свой админский HTML)
    admin_text = "Нова заявка PULS:\n\n" + json.dumps(data, ensure_ascii=False, indent=2)
    send_email_gmail(
        to_addr=ADMIN,
        subject="Нова заявка PULS",
        text=admin_text
    )

    return jsonify(ok=True, message="Заявка отримана! Email відправлено.", received=data), 200

def build_user_email_html(data, logo_cid=None):
    # logo_cid: строка вида "logo123@cid" или None (если вставляешь картинку по URL)
    logo_block = f'<img src="cid:{logo_cid}" width="56" height="56" style="display:block;border-radius:12px;" alt="PULS">' if logo_cid else ""
    child = (data.get('childName') or "").strip()
    age = (data.get('childAge') or "").strip()
    phone = (data.get('phone') or "").strip()
    msg = (data.get('message') or "").strip()

    return f"""\
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>PULS — підтвердження заявки</title>
  <style>
    /* инлайн-стили в <style> поддерживает большинство клиентов; ключевые — дублируем inline ниже */
    @media (prefers-color-scheme: dark) {{
      /* мягкая поддержка тёмной темы */
      body {{ background:#0b0f14 !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:{BG};">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{BG};padding:24px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="width:600px;max-width:100%;background:{CARD};border:1px solid {BORDER};border-radius:16px;overflow:hidden;">
          <!-- Header -->
          <tr>
            <td style="padding:20px 20px 0 20px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td width="64" valign="middle" style="width:64px;">{logo_block}</td>
                  <td valign="middle" style="padding-left:12px;">
                    <div style="font-weight:800;font-size:18px;line-height:1.2;color:{INK};">PULS Football School — Wrocław</div>
                    <div style="color:{MUTED};font-size:13px;line-height:1.4;">Діти 5–12 років</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Hero line -->
          <tr>
            <td style="padding:16px 20px 0 20px;">
              <div style="height:4px;width:100%;background:linear-gradient(90deg,{BRAND_RED},#ef4444);border-radius:999px;"></div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:20px;">
              <h1 style="margin:0 0 10px 0;font-size:20px;line-height:1.3;color:{INK};">Вітаємо!</h1>
              <p style="margin:0 0 12px 0;color:{INK};line-height:1.6;">
                Дякуємо за заявку на безкоштовне тренування <strong>PULS</strong> у Вроцлаві.
                Наш менеджер зв’яжеться з вами найближчим часом.
              </p>

              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:12px;border:1px solid {BORDER};border-radius:12px;">
                <tr>
                  <td style="padding:12px 14px;border-bottom:1px solid {BORDER};">
                    <div style="color:{MUTED};font-size:12px;">Дитина</div>
                    <div style="color:{INK};font-size:14px;font-weight:600;">{child or "—"}</div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 14px;border-bottom:1px solid {BORDER};">
                    <div style="color:{MUTED};font-size:12px;">Вік</div>
                    <div style="color:{INK};font-size:14px;font-weight:600;">{age or "—"}</div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 14px;border-bottom:1px solid {BORDER};">
                    <div style="color:{MUTED};font-size:12px;">Телефон</div>
                    <div style="color:{INK};font-size:14px;font-weight:600;">{phone or "—"}</div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 14px;">
                    <div style="color:{MUTED};font-size:12px;">Повідомлення</div>
                    <div style="color:{INK};font-size:14px;">{msg or "—"}</div>
                  </td>
                </tr>
              </table>

              <p style="margin:14px 0 0 0;color:{MUTED};font-size:13px;">Адреса тренувань: Wrocław, ul. Prosta 16</p>
              <p style="margin:4px 0 0 0;color:{MUTED};font-size:13px;">Instagram: @puls_football_school_wroclaw</p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:14px 20px;background:#fafafa;border-top:1px solid {BORDER};color:{MUTED};font-size:12px;text-align:center;">
              © {__import__('datetime').date.today().year} PULS Wrocław • Це автоматичний лист — відповідь не обов’язкова
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(debug=True)
