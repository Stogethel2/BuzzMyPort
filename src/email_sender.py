"""ส่งอีเมลผ่าน Resend"""
import os
import resend


def send(html, subject):
    resend.api_key = os.environ["RESEND_API_KEY"]
    to = os.environ["REPORT_TO_EMAIL"]
    # from: ใช้ onboarding domain ของ Resend ได้เลยตอนทดสอบ เปลี่ยนเป็น domain ตัวเองภายหลัง
    sender = os.environ.get("REPORT_FROM_EMAIL", "onboarding@resend.dev")
    return resend.Emails.send({"from": sender, "to": to, "subject": subject, "html": html})
