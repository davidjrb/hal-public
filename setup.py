#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess

def prompt_user(question, default=None):
    prompt = f"{question} [{default}]: " if default else f"{question}: "
    response = input(prompt).strip()
    return response if response else default

def check_opencode():
    print("\n--- Checking Dependencies ---")
    opencode_path = shutil.which("opencode")
    if not opencode_path:
        print("WARNING: 'opencode' CLI not found in PATH.")
        print("Please install it: npm install -g @opencode-ai/cli")
    else:
        print(f"Found opencode at: {opencode_path}")
        # Check auth status?
        print("REMINDER: Ensure you have authenticated via 'opencode auth login'.")

def main():
    print("=== HAL WhatsApp Agent Setup ===")
    print("This script will generate the necessary configuration files.\n")

    check_opencode()

    # 1. Gather Info
    print("\n--- Organization Info ---")
    org_name = prompt_user("Organization/Project Name", "My Org")

    print("\n--- Server/VM Info ---")
    server_ip = prompt_user("Target Server IP", "192.168.1.100")
    ssh_user = prompt_user("SSH Username", "ubuntu")

    print("\n--- Twilio Credentials ---")
    print("(Found at console.twilio.com)")
    account_sid = prompt_user("Account SID")
    auth_token = prompt_user("Auth Token")
    whatsapp_from = prompt_user("WhatsApp From Number", "whatsapp:+14155238886")

    print("\n--- OpenAI / LLM ---")
    openai_key = prompt_user("OpenAI API Key (Leave empty if using opencode OAuth)", "")

    # 2. Write config/twilio.env
    config_dir = "config"
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    env_content = (
        f"TWILIO_ACCOUNT_SID={account_sid}\n"
        f"TWILIO_AUTH_TOKEN={auth_token}\n"
        f"TWILIO_WHATSAPP_FROM={whatsapp_from}\n"
    )
    if openai_key:
        env_content += f"OPENAI_API_KEY={openai_key}\n"

    with open(os.path.join(config_dir, "twilio.env"), "w") as f:
        f.write(env_content)
    print(f"\nCreated {os.path.join(config_dir, 'twilio.env')}")

    # 3. Update Identity
    identity_file = os.path.join("whatsapp", "HAL_IDENTITY.md")
    if os.path.exists(identity_file):
        with open(identity_file, "r") as f:
            content = f.read()
        
        content = content.replace("<YOUR_ORG_NAME>", org_name)
        
        with open(identity_file, "w") as f:
            f.write(content)
        print(f"Updated {identity_file} with Org Name: {org_name}")

    # 4. Instructions
    print("\n=== Setup Complete ===")
    print(f"1. Copy this repo to your server: rsync -av . {ssh_user}@{server_ip}:~/hal-agent")
    print(f"2. SSH into server: ssh {ssh_user}@{server_ip}")
    print("3. Run: ./scripts/apply_whatsapp_poller.sh")
    print("\nDon't forget to star the repo!")

if __name__ == "__main__":
    main()
