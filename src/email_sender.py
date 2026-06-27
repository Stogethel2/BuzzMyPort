"""ส่งอีเมลผ่าน Resend"""
import os
import resend


def send(html, subject):
    resend.api_key = os.environ["RESEND_API_KEY"]
    to = os.environ["REPORT_TO_EMAIL"]
    # from: ใช้ onboarding domain ของ Resend ได้เลยตอนทดสอบ เปลี่ยนเป็น domain ตัวเองภายหลัง
    # `or` ไม่ใช่ default ของ .get เพราะ GitHub Actions ใส่ env เป็น "" เมื่อ secret ไม่ถูกตั้ง
    sender = os.environ.get("REPORT_FROM_EMAIL") or "onboarding@resend.dev"
    return resend.Emails.send({"from": sender, "to": to, "subject": subject, "html": html})
