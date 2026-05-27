from app.gmail.client import authorize_gmail


if __name__ == "__main__":
    authorize_gmail()
    print("Gmail authorization complete. token.json has been created or refreshed.")
