#!/usr/bin/env python3
"""
Generate a secure SECRET_KEY for Flask sessions
This key will ensure session persistence across serverless restarts
"""

import secrets
import string

def generate_secure_secret_key():
    """Generate a cryptographically secure secret key"""
    
    # Generate a 32-byte (256-bit) random key
    secret_key = secrets.token_hex(32)
    
    print("🔐 SECURE SECRET_KEY GENERATED")
    print("=" * 50)
    print(f"SECRET_KEY={secret_key}")
    print("=" * 50)
    print()
    print("📋 COPY THIS TO YOUR VERCEL ENVIRONMENT VARIABLES:")
    print(f"SECRET_KEY={secret_key}")
    print()
    print("🔧 HOW TO SET IN VERCEL:")
    print("1. Go to your Vercel dashboard")
    print("2. Select your project")
    print("3. Go to Settings → Environment Variables")
    print("4. Add new variable: SECRET_KEY")
    print("5. Paste the value above")
    print("6. Deploy your project")
    print()
    print("✅ After setting this, your sessions will persist!")
    print("✅ No more 401 errors during operations!")
    print("✅ Users will stay logged in until manual logout!")
    
    return secret_key

if __name__ == "__main__":
    generate_secure_secret_key()
