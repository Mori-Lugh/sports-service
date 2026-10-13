from fastapi import FastAPI, HTTPException, Query

from app.sample_data import MATCHES
from app.schemas import Match

app = FastAPI(title="Sports Service")#создание приложения


@app.get("/health")
def health():
    return {"status": "ok"}     #проверка работы сервера


@app.get("/matches", response_model=list[Match])
def list_matches(season_id: int | None = Query(default=None, gt=0)):
    if season_id is None:     #если сезон не указан, то возвращаем все матчи
        return MATCHES

    result = []    #собирются все матчи только нужного сезона
    for match in MATCHES:
        if match.season_id == season_id:
            result.append(match)
    return result


@app.get("/matches/{match_id}", response_model=Match)
def get_match(match_id: int):
    # Ищем матч по его номеру.
    for match in MATCHES:
        if match.match_id == match_id:
            return match

    raise HTTPException(status_code=404, detail="Матч не найден")


@app.post("/matches", response_model=Match, status_code=201)
def add_match(new_match: Match):
    #FastAPI проверяет данные по модели Match до вызова функции. Матчи имеют разные номера
    for match in MATCHES:
        if match.match_id == new_match.match_id:
            raise HTTPException(status_code=409, detail="Такой номер матча уже есть")

    MATCHES.append(new_match)
    return new_match
