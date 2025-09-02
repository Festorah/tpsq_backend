# Create this as debug_env.py in your project root

import os
import sys
from pathlib import Path


def debug_environment():
    print("=" * 60)
    print("ENVIRONMENT VARIABLES DEBUG")
    print("=" * 60)

    # Check current working directory
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[0]}")

    print("\n" + "=" * 40)
    print("DATABASE-RELATED ENVIRONMENT VARIABLES")
    print("=" * 40)

    # Check all DATABASE related env vars
    db_vars = {k: v for k, v in os.environ.items() if "DATABASE" in k.upper()}
    if db_vars:
        for key, value in db_vars.items():
            print(f"{key}: {value}")
    else:
        print("No DATABASE environment variables found")

    print("\n" + "=" * 40)
    print("ALL ENVIRONMENT FILES IN PROJECT")
    print("=" * 40)

    # Look for .env files
    project_root = Path.cwd()
    env_files = list(project_root.glob("**/.env*"))

    if env_files:
        for env_file in env_files:
            print(f"Found: {env_file}")
            try:
                with open(env_file, "r") as f:
                    content = f.read()
                    if "DATABASE_URL" in content:
                        print(f"  ↳ Contains DATABASE_URL")
                        lines = content.split("\n")
                        for line in lines:
                            if line.startswith("DATABASE_URL"):
                                print(f"    {line}")
            except Exception as e:
                print(f"  ↳ Could not read: {e}")
    else:
        print("No .env files found")

    print("\n" + "=" * 40)
    print("PYTHON-DECOUPLE DEBUG")
    print("=" * 40)

    try:
        from decouple import config

        database_url = config("DATABASE_URL", default="NOT_FOUND")
        print(f"python-decouple DATABASE_URL: {database_url}")
    except ImportError:
        print("python-decouple not installed")
    except Exception as e:
        print(f"Error with python-decouple: {e}")

    print("\n" + "=" * 40)
    print("DJANGO SETTINGS DEBUG")
    print("=" * 40)

    try:
        # Add the current directory to Python path
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())

        # Try to import Django settings
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tpsq_backend.settings")

        import django
        from django.conf import settings

        django.setup()

        databases = getattr(settings, "DATABASES", {})
        if "default" in databases:
            db_config = databases["default"]
            print("Django DATABASES['default']:")
            for key, value in db_config.items():
                print(f"  {key}: {value}")
        else:
            print("No default database configuration found")

    except Exception as e:
        print(f"Error loading Django settings: {e}")


if __name__ == "__main__":
    debug_environment()
