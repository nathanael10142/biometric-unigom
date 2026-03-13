#!/usr/bin/env python3
"""
Script de test pour vérifier si le backend est accessible
sur le serveur de production 95.216.18.174:8000
"""

import requests
import sys
from datetime import datetime

def test_backend_connection():
    """Tester la connexion au backend de production"""
    
    base_url = "http://95.216.18.174:8000"
    
    print(f"🔍 Test de connexion au backend : {base_url}")
    print("=" * 50)
    
    # Test 1: Endpoint racine
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"✅ Endpoint / : {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        else:
            print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Endpoint / : {e}")
    
    # Test 2: Health check
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"✅ Endpoint /health : {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        else:
            print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Endpoint /health : {e}")
    
    # Test 3: API docs
    try:
        response = requests.get(f"{base_url}/docs", timeout=10)
        print(f"✅ Endpoint /docs : {response.status_code}")
        if response.status_code == 200:
            print("   ✅ API Documentation accessible")
        else:
            print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Endpoint /docs : {e}")
    
    # Test 4: Auth endpoint (sans login)
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/token",
            data={"username": "test", "password": "test"},
            timeout=10
        )
        print(f"✅ Endpoint /api/v1/auth/token : {response.status_code}")
        if response.status_code in [401, 422]:
            print("   ✅ Endpoint répond (erreur d'auth normal)")
        else:
            print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Endpoint /api/v1/auth/token : {e}")
    
    print("=" * 50)
    print(f"📅 Test effectué à : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Recommandations
    print("\n🔧 Si les tests échouent :")
    print("1. Vérifiez que le backend tourne sur 95.216.18.174:8000")
    print("2. Vérifiez le firewall (port 8000 ouvert)")
    print("3. Vérifiez que NGINX est configuré correctement")
    print("4. Vérifiez les logs du backend")

if __name__ == "__main__":
    test_backend_connection()
