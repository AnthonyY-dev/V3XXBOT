import nextcord
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import json
from datetime import datetime, timezone

client = nextcord.Client(
    intents=nextcord.Intents.all()
)

is_future_date = lambda date_string: datetime.fromisoformat(date_string.replace("Z", "+00:00")) > datetime.now(timezone.utc)

# Function to initialize Firebase if not already initialized
def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate('key.json')
        firebase_admin.initialize_app(cred)

# Function to get Firestore client
def get_firestore_client():
    initialize_firebase()
    return firestore.client()

async def get_uid_from_code(verification_code):
    """
    Retrieve the user ID (UID) associated with a given verification code.
    """
    db = get_firestore_client()
    codes_ref = db.collection('verificationCodes')
    query = codes_ref.where(f'code', '==', str(verification_code)).limit(1)
    results = query.stream()
    
    for doc in results:
        data = doc.to_dict()
        if data.get('used') == False and is_future_date(data.get("expiresAt")):
            return [data.get('userId'), doc]
        else:
            return "N/A"

    return "N/A"
async def delete_user_data(collection, uid, field):
    db = get_firestore_client()
    user_ref = db.collection(collection).document(uid)
    user_ref.update({field: firestore.DELETE_FIELD})
def delete_fbdocs_by_username(name):
    """
    Retrieve and delete the 'robloxUsername' field for documents associated with the given username.
    """
    db = firestore.client()
    codes_ref = db.collection('verificationCodes')
    query = codes_ref.where('robloxUsername', '==', str(name)).limit(1)
    results = query.stream()  # Firebase Admin SDK streams synchronously

    # Iterate through results and update the document
    for doc in results:
        doc.reference.update({"robloxUsername": firestore.DELETE_FIELD})
async def set_data(collection, uid, data):
    db = get_firestore_client()
    user_ref = db.collection(collection).document(uid)
    user_ref.set(data)
async def update_data(collection, uid, data):
    db = get_firestore_client()
    user_ref = db.collection(collection).document(uid)
    user_ref.update(data)

async def get_roblox_username(dcid):
     response = requests.get(f"https://registry.rover.link/api/guilds/1301005755050360904/discord-to-roblox/{str(dcid)}", headers={"Authorization": "Bearer rvr2g09vu81svztoi05vst0nltku0957vsvjpcm2dmzfvo90m0i3vvkfa9dy97l9u09l"})
     return json.loads(response.content)["cachedUsername"]

@client.slash_command(name="connect", description="Connect your roblox account to the website.")
async def connect(interaction: nextcord.Interaction, code: int):
    response = await get_uid_from_code(code)
    if response != "N/A":
        try:
            rbxUser = await get_roblox_username(interaction.user.id)
            await update_data("verificationCodes", response[1].id, {"used": True})
            delete_fbdocs_by_username(rbxUser)
            await update_data("users", response[0], {"robloxUsername": rbxUser})
            await interaction.send(f"Successfully binded accounts.", ephemeral=True)
        except KeyError:
            await interaction.send(embed=nextcord.Embed(title="Please verify with RoVer first.", color=nextcord.Color.red()), ephemeral=True)
    else:
        await interaction.send(embed=nextcord.Embed(title="Invalid Code", color=nextcord.Color.red()), ephemeral=True)

@client.event
async def on_ready():
    print("Ready!")

client.run("MTMwMzIwNzEzODkxODc5NzQwMA.GcvP2d.Rxe3zQsrfEI0H2Bey2BWfRD89qvHg1V24oooQY")
