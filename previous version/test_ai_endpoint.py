#!/usr/bin/env python3
"""
Test script for AI response generation endpoint
"""

import requests
import json

def test_ai_endpoint():
    """Test the AI response display endpoint"""
    
    # Test data - simplified to only ticket_id and ai_response
    test_data = {
        "ticket_id": "TEST-001",
        "ai_response": "Hello John Doe,\n\nThank you for contacting AutoAssistGroup support.\n\nI can see you're inquiring about a warranty claim. Let me help you with that.\n\nTo process your warranty claim efficiently, I'll need the following information:\n• Original purchase receipt or invoice\n• Warranty registration details\n• Clear photos of the issue/defect\n• Description of when the problem first occurred\n\nOnce I receive this information, I'll review your claim and provide you with the next steps.\n\nIf you have any questions or need immediate assistance, please don't hesitate to contact us.\n\nBest regards,\nAutoAssistGroup Support Team"
    }
    
    # API endpoint
    url = "https://auto-assit-group-woad.vercel.app/api/ai/display-response"
    
    try:
        print("Testing AI response generation endpoint...")
        print(f"URL: {url}")
        print(f"Data: {json.dumps(test_data, indent=2)}")
        print("-" * 50)
        
        # Make POST request
        response = requests.post(url, json=test_data, headers={'Content-Type': 'application/json'})
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS: AI response generated successfully!")
            ai_response = response.json().get('ai_response', '')
            print(f"\nGenerated AI Response:\n{ai_response}")
        else:
            print(f"\n❌ ERROR: Request failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    test_ai_endpoint()
