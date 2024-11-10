from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
from typing import List
import requests

# Inicjalizacja aplikacji FastAPI
app = FastAPI()

# MongoDB URI
mongo_uri = "mongodb+srv://poznanred:jaC8aDjsKqI1rxzj@klakierzyc.uyah9.mongodb.net/?retryWrites=true&w=majority&appName=klakierzyc"

# Połączenie z MongoDB
client = MongoClient(mongo_uri)
db = client.get_database("bans")
bans_collection = db.get_collection("bans")

# Model danych dla odpowiedzi API
class BannedPlayer(BaseModel):
    player_id: int
    reason: str

# Funkcja do zapisu bana w MongoDB
def ban_user_in_db(player_id, reason, duration, permban, universe_id=None):
    ban_data = {
        'player_id': player_id,
        'reason': reason,
        'duration': duration,
        'permban': permban,
        'universe_id': universe_id
    }
    try:
        bans_collection.insert_one(ban_data)
        print(f"Zapisano bana do MongoDB dla gracza {player_id}, Universe: {universe_id}")
    except Exception as e:
        print(f"Błąd przy zapisie bana w MongoDB: {e}")

# Funkcja do pobierania ID gracza na podstawie nazwy gracza
def get_roblox_user_id(username: str) -> int:
    url = f"https://users.roblox.com/v1/users/{username}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Sprawdzamy, czy odpowiedź HTTP jest poprawna (status 200)
        data = response.json()

        # Sprawdzamy, czy API zwróciło ID użytkownika
        if 'id' in data:
            return data['id']
        else:
            raise ValueError(f"Gracz o nazwie {username} nie został znaleziony w Roblox.")
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            raise ValueError(f"Gracz o nazwie {username} nie istnieje w Roblox.")  # Dostosowanie komunikatu
        else:
            raise ValueError(f"Błąd przy pobieraniu gracza: {e}")
    except requests.RequestException as e:
        raise ValueError(f"Nieznany błąd przy komunikacji z API Roblox: {e}")

# Endpoint API do zbanowanych graczy
@app.get("/getBannedPlayers", response_model=List[BannedPlayer])
def get_banned_players():
    banned_players = list(bans_collection.find({}, {'_id': 0, 'player_id': 1, 'reason': 1}))
    return banned_players

# Endpoint API do banowania gracza
@app.post("/banPlayer")
def ban_player(player: str, reason: str, duration: int, permban: bool, universe_id: str = None):
    try:
        # Sprawdzamy, czy 'player' to ID (liczba) czy nazwa gracza
        try:
            player_id = int(player)
        except ValueError:
            # Jeśli to nazwa gracza, pobieramy ID z Roblox API
            player_id = get_roblox_user_id(player)

        # Zapisujemy bana w MongoDB
        ban_user_in_db(player_id, reason, duration, permban, universe_id)
        return {"message": f"Gracz {player} został zbanowany. Powód: {reason}. Typ bana: {'permanentny' if permban else 'czasowy'}. Universe ID: {universe_id or 'brak'}.", "player_id": player_id}
    except ValueError as e:
        return {"error": str(e)}
