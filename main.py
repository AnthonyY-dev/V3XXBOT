import nextcord
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv  # For loading .env files

# Load environment variables from .env file
load_dotenv()

# Initialize Discord client
client = nextcord.Client(intents=nextcord.Intents.all())

# Helper function to check if a date is in the future
is_future_date = lambda date_string: datetime.fromisoformat(date_string.replace("Z", "+00:00")) > datetime.now(timezone.utc)

# Initialize Firebase only if not already initialized
def initialize_firebase():
    if not firebase_admin._apps:
        # Firebase credentials from environment variables
        firebase_config = {
            "type": os.getenv("FIREBASE_TYPE"),
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),  # Ensure newlines are handled
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
        }
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)

# Function to get Firestore client
def get_firestore_client():
    initialize_firebase()
    return firestore.client()

# Fetch UID based on a verification code
async def get_uid_from_code(verification_code):
    db = get_firestore_client()
    codes_ref = db.collection('verificationCodes')
    query = codes_ref.where('code', '==', str(verification_code)).limit(1)
    results = query.stream()
    
    for doc in results:
        data = doc.to_dict()
        if data.get('used') == False and is_future_date(data.get("expiresAt")):
            return [data.get('userId'), doc]
        else:
            return "N/A"
    return "N/A"

# Delete specific user data
async def delete_user_data(collection, uid, field):
    db = get_firestore_client()
    user_ref = db.collection(collection).document(uid)
    user_ref.update({field: firestore.DELETE_FIELD})

# Delete documents by username
def delete_fbdocs_by_username(name):
    db = firestore.client()
    codes_ref = db.collection('verificationCodes')
    query = codes_ref.where('robloxUsername', '==', str(name)).limit(1)
    results = query.stream()
    
    for doc in results:
        doc.reference.update({"robloxUsername": firestore.DELETE_FIELD})

# Set data in Firestore
async def set_data(collection, uid, data):
    db = get_firestore_client()
    user_ref = db.collection(collection).document(uid)
    user_ref.set(data)

# Update data in Firestore
async def update_data(collection, uid, data):
    db = get_firestore_client()
    user_ref = db.collection(collection).document(uid)
    user_ref.update(data)

# Retrieve Roblox username via Rover API
async def get_roblox_username(dcid):
    response = requests.get(
        f"https://registry.rover.link/api/guilds/1301005755050360904/discord-to-roblox/{str(dcid)}",
        headers={"Authorization": f"Bearer {os.getenv('ROVERTOKEN')}"}
    )
    return json.loads(response.content)["cachedUsername"]

# Discord command for account connection
@client.slash_command(name="connect", description="Connect your roblox account to the website.")
async def connect(interaction: nextcord.Interaction, code: int):
    response = await get_uid_from_code(code)
    if response != "N/A":
        try:
            rbxUser = await get_roblox_username(interaction.user.id)
            await update_data("verificationCodes", response[1].id, {"used": True})
            delete_fbdocs_by_username(rbxUser)
            await update_data("users", response[0], {"robloxUsername": rbxUser})
            await interaction.send("Successfully binded accounts.", ephemeral=True)
        except KeyError:
            await interaction.send(embed=nextcord.Embed(title="Please verify with RoVer first.", color=nextcord.Color.red()), ephemeral=True)
    else:
        await interaction.send(embed=nextcord.Embed(title="Invalid Code", color=nextcord.Color.red()), ephemeral=True)

# Event handler when bot is ready
@client.event
async def on_ready():
    print("Ready!")

# Run the Discord client using the token from environment variables
if(os.getenv("MODE") == "DEV"):
    client.run("DVT")
elif(os.getenv("MODE")=="PROD"):
    client.run(os.getenv("TOKEN"))
else:
    print("Invalid Mode")