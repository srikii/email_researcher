from app.gmail.client import authorize_gmail


if __name__ == "__main__":
    # Run this once after placing credentials.json in the project root.
    # It opens Google's OAuth flow and writes token.json.
    authorize_gmail()
    print("Gmail authorization complete. token.json has been created or refreshed.")
