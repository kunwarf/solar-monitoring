#!/usr/bin/env python3
"""
API Key Management CLI Tool
Allows users to store, retrieve, and manage API keys for weather providers.
"""

import argparse
import sys
import os
from solarhub.api_key_manager import get_api_key_manager

def main():
    parser = argparse.ArgumentParser(description="Manage API keys for weather providers")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Store API key command
    store_parser = subparsers.add_parser('store', help='Store an API key')
    store_parser.add_argument('service', help='Service name (e.g., weatherapi, openmeteo)')
    store_parser.add_argument('key', help='API key to store')
    store_parser.add_argument('--description', help='Description of the API key')
    
    # List API keys command
    list_parser = subparsers.add_parser('list', help='List all stored API keys')
    
    # Get API key command
    get_parser = subparsers.add_parser('get', help='Get an API key')
    get_parser.add_argument('service', help='Service name')
    
    # Delete API key command
    delete_parser = subparsers.add_parser('delete', help='Delete an API key')
    delete_parser.add_argument('service', help='Service name')
    
    # Deactivate API key command
    deactivate_parser = subparsers.add_parser('deactivate', help='Deactivate an API key')
    deactivate_parser.add_argument('service', help='Service name')
    
    # Interactive setup command
    setup_parser = subparsers.add_parser('setup', help='Interactive setup for common weather providers')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = get_api_key_manager()
    
    if args.command == 'store':
        success = manager.store_api_key(args.service, args.key, args.description or "")
        if success:
            print(f"✅ API key stored successfully for {args.service}")
        else:
            print(f"❌ Failed to store API key for {args.service}")
            sys.exit(1)
    
    elif args.command == 'list':
        api_keys = manager.list_api_keys()
        if api_keys:
            print("📋 Stored API Keys:")
            print("-" * 50)
            for service, key_info in api_keys.items():
                status = "🟢 Active" if key_info.is_active else "🔴 Inactive"
                print(f"Service: {service}")
                print(f"  Status: {status}")
                print(f"  Description: {key_info.description}")
                print()
        else:
            print("📭 No API keys stored")
    
    elif args.command == 'get':
        key = manager.get_api_key(args.service)
        if key:
            print(f"🔑 API key for {args.service}: {key}")
        else:
            print(f"❌ No API key found for {args.service}")
            sys.exit(1)
    
    elif args.command == 'delete':
        success = manager.delete_api_key(args.service)
        if success:
            print(f"✅ API key deleted for {args.service}")
        else:
            print(f"❌ Failed to delete API key for {args.service}")
            sys.exit(1)
    
    elif args.command == 'deactivate':
        success = manager.deactivate_api_key(args.service)
        if success:
            print(f"✅ API key deactivated for {args.service}")
        else:
            print(f"❌ Failed to deactivate API key for {args.service}")
            sys.exit(1)
    
    elif args.command == 'setup':
        interactive_setup(manager)

def interactive_setup(manager):
    """Interactive setup for common weather providers."""
    print("🌤️  Weather Provider API Key Setup")
    print("=" * 40)
    
    providers = {
        "weatherapi": {
            "name": "WeatherAPI.com",
            "url": "https://www.weatherapi.com/",
            "description": "Free tier: 1M calls/month"
        },
        "openmeteo": {
            "name": "Open-Meteo",
            "url": "https://open-meteo.com/",
            "description": "Free, no API key required"
        },
        "openweather": {
            "name": "OpenWeatherMap",
            "url": "https://openweathermap.org/",
            "description": "Free tier: 1000 calls/day"
        }
    }
    
    print("\nAvailable weather providers:")
    for i, (key, info) in enumerate(providers.items(), 1):
        print(f"{i}. {info['name']} - {info['description']}")
        print(f"   URL: {info['url']}")
    
    while True:
        try:
            choice = input("\nEnter provider number (1-3) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                break
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(providers):
                provider_key = list(providers.keys())[choice_num - 1]
                provider_info = providers[provider_key]
                
                print(f"\nSetting up {provider_info['name']}...")
                
                if provider_key == "openmeteo":
                    print("✅ Open-Meteo doesn't require an API key!")
                    continue
                
                api_key = input(f"Enter your {provider_info['name']} API key: ").strip()
                if api_key:
                    description = input("Enter description (optional): ").strip()
                    success = manager.store_api_key(provider_key, api_key, description)
                    if success:
                        print(f"✅ API key stored successfully for {provider_info['name']}")
                    else:
                        print(f"❌ Failed to store API key for {provider_info['name']}")
                else:
                    print("❌ API key cannot be empty")
            else:
                print("❌ Invalid choice. Please enter 1-3 or 'q'")
        
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q'")
        except KeyboardInterrupt:
            print("\n👋 Setup cancelled")
            break
    
    print("\n🎉 Setup complete!")

if __name__ == "__main__":
    main()
