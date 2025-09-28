#!/usr/bin/env python3
"""
Simple launcher for AutoGLMUI
"""
import os
import sys
import subprocess

def main():
    """Main launcher"""
    print("AutoGLMUI Launcher")
    print("=================")
    print()

    # Check if token is set
    if not os.getenv("AUTOGLM_AUTOGLM_API_TOKEN"):
        print("Warning: AUTOGLM_AUTOGLM_API_TOKEN environment variable not set!")
        print("Please set your API token:")
        print("  Windows: set AUTOGLM_AUTOGLM_API_TOKEN=your_token")
        print("  Linux/Mac: export AUTOGLM_AUTOGLM_API_TOKEN=your_token")
        print()

    # Ask user what to run
    while True:
        choice = input("What would you like to run?\n1. Web Server\n2. CLI Client\n3. Exit\n> ")

        if choice == "1":
            print("\nStarting web server...")
            print("Open http://localhost:8000 in your browser\n")
            subprocess.run([sys.executable, "main.py"])
            break
        elif choice == "2":
            print("\nStarting CLI client...")
            print("Type 'quit' to exit\n")
            subprocess.run([sys.executable, "auto.py"])
            break
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.\n")

if __name__ == "__main__":
    main()