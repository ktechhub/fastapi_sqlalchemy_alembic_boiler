from app.core.config import settings

logo_url = "https://www.ktechhub.com/assets/logo.13616b6b.png"


def get_basic_template(title, subject, salutation, message):
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
      background-color: #f4f4f4;
    }}
    .email-container {{
      max-width: 600px;
      margin: 0 auto;
      background-color: #ffffff;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      border-radius: 8px;
      overflow: hidden;
    }}
    .header {{
      background-color: #5800FF;
      color: #ffffff;
      padding: 20px;
      text-align: center;
    }}
    .header h1 {{
      margin: 0;
    }}
    .content {{
      padding: 20px;
    }}
    .content h2 {{
      text-align: center;
      color: #0096FF;
    }}
    .content p {{
      color: #333333;
      line-height: 1.6;
    }}
    .cta-button {{
      display: inline-block;
      padding: 10px 20px;
      margin-top: 20px;
      background-color: #00D7FF;
      color: #ffffff;
      text-decoration: none;
      border-radius: 4px;
    }}
    .footer {{
      background-color: #72FFFF;
      color: #333333;
      text-align: center;
      padding: 10px;
      font-size: 14px;
    }}
    .footer img {{
      max-width: 150px;
      margin-top: 10px;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <h1>{title}</h1>
    </div>
    <div class="content">
      <h2>{subject}</h2>
      <p>{salutation}</p>
      {message}<br>
      <p>Regards,</p>
      <p>{settings.APP_NAME.upper()} Team</p>
    </div>
    <div class="footer">
      <img src="{logo_url}" alt="{settings.APP_NAME} Logo">
      <p>&copy; 2025 {settings.DOMAIN}. All rights reserved.</p>
    </div>
  </div>
</body>
</html>
"""
    return html


def get_welcome_email_template(name):
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to {settings.DOMAIN}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f4f4;
        }}
        
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
            font-weight: 300;
        }}
        
        .header p {{
            font-size: 16px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px 30px;
        }}
        
        .welcome-message {{
            font-size: 18px;
            margin-bottom: 20px;
            color: #2c3e50;
        }}
        
        .description {{
            font-size: 16px;
            color: #555;
            margin-bottom: 30px;
            line-height: 1.8;
        }}
        
        .features {{
            background-color: #f8f9fa;
            padding: 25px;
            border-radius: 6px;
            margin-bottom: 30px;
        }}
        
        .features h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        
        .features ul {{
            list-style: none;
            padding: 0;
        }}
        
        .features li {{
            padding: 8px 0;
            color: #555;
            position: relative;
            padding-left: 25px;
        }}
        
        .features li:before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: #27ae60;
            font-weight: bold;
        }}
        
        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            text-align: center;
            transition: transform 0.2s ease;
        }}
        
        .cta-button:hover {{
            transform: translateY(-2px);
        }}
        
        .footer {{
            background-color: #2c3e50;
            color: white;
            text-align: center;
            padding: 30px 20px;
        }}
        
        .footer img {{
            max-width: 120px;
            margin-bottom: 15px;
        }}
        
        .footer p {{
            font-size: 14px;
            opacity: 0.8;
        }}
        
        .social-links {{
            margin-top: 20px;
        }}
        
        .social-links a {{
            color: white;
            text-decoration: none;
            margin: 0 10px;
            opacity: 0.8;
            transition: opacity 0.2s ease;
        }}
        
        .social-links a:hover {{
            opacity: 1;
        }}
        
        @media (max-width: 600px) {{
            .container {{
                margin: 10px;
                border-radius: 4px;
            }}
            
            .header {{
                padding: 30px 15px;
            }}
            
            .content {{
                padding: 30px 20px;
            }}
            
            .header h1 {{
                font-size: 24px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {settings.DOMAIN}</h1>
            <p>We're excited to have you on board!</p>
        </div>
        
        <div class="content">
            <div class="welcome-message">
                Hello {name}! 👋
            </div>
            
            <div class="description">
                Thank you for joining us! We're thrilled to welcome you to our platform. 
                You're now part of a community that values innovation, quality, and user experience.
            </div>
            
            <div class="features">
                <h3>What you can do now:</h3>
                <ul>
                    <li>Explore our features and capabilities</li>
                    <li>Complete your profile setup</li>
                    <li>Start using our services</li>
                    <li>Connect with our support team</li>
                </ul>
            </div>
            
            <div style="text-align: center;">
                <a href="{settings.FRONTEND_URL}/dashboard" class="cta-button">
                    Get Started
                </a>
            </div>
        </div>
        
        <div class="footer">
            <img src="{logo_url}" alt="{settings.DOMAIN} Logo">
            <p>&copy; 2025 {settings.DOMAIN}. All rights reserved.</p>
            <p>Thank you for choosing us!</p>
            
            <div class="social-links">
                <a href="{settings.FRONTEND_URL}">Website</a> |
                <a href="{settings.FRONTEND_URL}/support">Support</a> |
                <a href="{settings.FRONTEND_URL}/docs">Documentation</a>
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html
