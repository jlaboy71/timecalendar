#!/usr/bin/env python
"""
Generate a self-signed SSL certificate for TJM Time Calendar.

This creates a certificate suitable for internal/development use.
For production with external access, use a proper CA-signed certificate.

Usage:
    python scripts/generate_ssl_cert.py

Output:
    certs/server.crt - Certificate file
    certs/server.key - Private key file
"""
import subprocess
import sys
from pathlib import Path


def generate_self_signed_cert(
    cert_dir: str = "certs",
    days_valid: int = 365,
    common_name: str = "tjm-calendar.local"
):
    """
    Generate a self-signed certificate using OpenSSL CLI.

    Args:
        cert_dir: Directory to store certificate files
        days_valid: Number of days the certificate is valid
        common_name: Common name (CN) for the certificate
    """
    cert_path = Path(cert_dir)
    cert_path.mkdir(exist_ok=True)

    key_file = cert_path / "server.key"
    cert_file = cert_path / "server.crt"

    # OpenSSL command to generate self-signed certificate
    cmd = [
        "openssl", "req",
        "-x509",
        "-newkey", "rsa:2048",
        "-keyout", str(key_file),
        "-out", str(cert_file),
        "-days", str(days_valid),
        "-nodes",  # No password on private key
        "-subj", f"/C=US/ST=Illinois/L=Chicago/O=TJM Holdings/OU=Haventech/CN={common_name}"
    ]

    print(f"Generating self-signed certificate...")
    print(f"  Common Name: {common_name}")
    print(f"  Valid for: {days_valid} days")
    print()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"[OK] Certificate generated successfully!")
        print(f"  Certificate: {cert_file}")
        print(f"  Private Key: {key_file}")
        print()
        print("To enable HTTPS, add these to your .env file:")
        print(f"  TJM_SSL_CERT={cert_file}")
        print(f"  TJM_SSL_KEY={key_file}")
        print()
        print("NOTE: Browsers will show a security warning for self-signed certificates.")
        print("      This is expected for internal use. Click 'Advanced' > 'Proceed' to continue.")
        return True

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to generate certificate:")
        print(f"  {e.stderr}")
        return False

    except FileNotFoundError:
        print("[ERROR] OpenSSL not found. Please install OpenSSL and try again.")
        print("  Windows: Install from https://slproweb.com/products/Win32OpenSSL.html")
        print("  Or use Git Bash which includes OpenSSL")
        return False


if __name__ == "__main__":
    # Run from project root
    project_root = Path(__file__).parent.parent

    success = generate_self_signed_cert(
        cert_dir=str(project_root / "certs"),
        days_valid=365,
        common_name="tjm-calendar.local"
    )

    sys.exit(0 if success else 1)
