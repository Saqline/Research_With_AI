import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(email: str,  subject: str, body: str):
    # SMTP server configuration
    smtp_host = "mail host"
    smtp_port = 587  # SSL/TLS port
    smtp_user = "hostmail"
    smtp_password = "pass"

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Send the email
    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()  # Secure the connection
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email, msg.as_string())
        server.quit()
        print("Verification email sent successfully")
    except Exception as e:
        print(f"Failed to send verification email: {e}")



def send_verification_email(email: str, verify_code: str):
    print("come1")
    # SMTP server configuration
    smtp_host = "mail host"
    smtp_port = 587  # SSL/TLS port
    smtp_user = "hostmail"
    smtp_password = "pass"
    print("come12")
    # Email content
    subject = "Your  Verification Code"
    body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }}
        .email-container {{
            max-width: 600px;
            margin: 20px auto;
            background-color: #ffffff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        .email-header {{
            background-color: #004a9f;
            padding: 30px;
            color: white;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }}
        .email-header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .email-body {{
            padding: 20px;
            text-align: center;
            font-size: 16px;
            line-height: 1.5;
            color: #333333;
        }}
        .verification-code {{
            background-color: #ffa500;
            color: #ffffff;
            font-size: 22px;
            font-weight: bold;
            padding: 15px 25px;
            border-radius: 5px;
            display: inline-block;
            margin: 20px 0;
        }}
        .footer {{
            background-color: #f4f4f4;
            padding: 30px;
            text-align: center;
            color: #777777;
            font-size: 14px;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        }}
        .footer p {{
            margin: 5px 0;
        }}
        .social-icons img {{
            width: 24px;
            height: 24px;
            margin: 0 5px;
            vertical-align: middle;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <h1>Verify Your Account</h1>
        </div>
        <div class="email-body">
            <p>Hi,</p>
            <p>You’re almost ready to get started. Use the verification code below to complete your sign-up process:</p>
            <div class="verification-code">{verify_code}</div>
            <p>This code will expire in 5 minutes.</p>
            <p>Thanks </p>
    
        </div>
        
    </div>
</body>
</html>
    """    # Create the email
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    # Send the email
    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()  # Secure the connection
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email, msg.as_string())
        server.quit()
        print("Verification email sent successfully")
    except Exception as e:
        print(f"Failed to send verification email: {e}")
