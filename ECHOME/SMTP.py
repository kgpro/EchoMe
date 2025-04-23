import smtplib
from email.mime.multipart import MIMEMultipart  # Changed from EmailMessage
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from django.conf import settings

def send_email_with_attachment(file_info, to_email,time ,time_diffrance, subject=None, body=None):
    """Send email with attachment using Gmail SMTP"""

    # Email configuration
    gmail_user = 'echhouss@gmail.com'
    gmail_pass = settings.GMAIL_PASSWORD

    # Default subject and body
    if not subject:
        subject = "🔓 Your Decrypted File is Attached!"

    if not body:
        body = f"""Dear Recipient,

Please find your decrypted file attached to this email:

📎 Attachment:
     File name: attachment{file_info['ext']}
     Storage time: {time}
     Security: End to End AES-256 encrypted
You have messaged {time_diffrance}.

Coming Soon:
▸ MAINNET: Migrating to mainnet soon
▸ WhatsApp Integration: Receive files directly via WhatsApp
▸ Instagram DM: Secure file delivery via Instagram
▸ Social Auth: Secure logins via Meta/Google
▸ Mobile Apps: Android/iOS applications

 Questions? Reply to this email.

Best regards,
TEAM ECHOUS
"""

    # Create multipart message
    msg = MIMEMultipart()  # Changed from EmailMessage
    msg['Subject'] = subject.replace('\n', ' ').strip()
    msg['From'] = gmail_user
    msg['To'] = to_email

    # Attach body text
    msg.attach(MIMEText(body, 'plain'))  # Properly attach text part

    # Attach file
    attachment = MIMEApplication(
        file_info['bytes'],
        _subtype=file_info['ext'].lstrip('.')
    )
    filename = f"attachment{file_info['ext']}"
    attachment.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(attachment)  # Now works with multipart

    # Send email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.send_message(msg)
        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

