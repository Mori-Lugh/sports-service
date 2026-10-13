from fastapi import FastAPI, HTTPException, Query

from app.sample_data import MATCHES
from app.schemas import Match, Score
from app.statistics import team_statistics, standings
from app.events import EVENTS, create_event

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
    # Событие открытия прогнозов нужно только для запланированного матча.
    if new_match.status == "scheduled":
        EVENTS.append(create_event(new_match, "match.scheduled"))
    return new_match


@app.get("/teams/{team_id}/stats")
def get_team_statistics(team_id: int, season_id: int = Query(gt=0)):
    result = team_statistics(MATCHES, team_id, season_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Команда не найдена в этом сезоне")
    return result


@app.get("/standings")
def get_standings(season_id: int = Query(gt=0)):
    return standings(MATCHES, season_id)


def save_match_change(match: Match, changes: dict, event_type: str):
    # Сначала проверяем новую версию матча, затем заменяем старую.
    data = match.model_dump()
    data.update(changes)
    updated_match = Match.model_validate(data)
    event = create_event(updated_match, event_type)

    for index, old_match in enumerate(MATCHES):
        if old_match.match_id == match.match_id:
            MATCHES[index] = updated_match
            break
    EVENTS.append(event)
    return updated_match


@app.post("/matches/{match_id}/start", response_model=Match)
def start_match(match_id: int):
    match = get_match(match_id)
    if match.status != "scheduled":
        raise HTTPException(status_code=409, detail="Начать можно только запланированный матч")
    return save_match_change(match, {"status": "live", "score": {"home": 0, "away": 0}},
                             "match.started")


@app.post("/matches/{match_id}/finish", response_model=Match)
def finish_match(match_id: int, score: Score):
    match = get_match(match_id)
    if match.status != "live":
        raise HTTPException(status_code=409, detail="Завершить можно только начатый матч")
    return save_match_change(match, {"status": "finished", "score": score.model_dump()},
                             "match.finished")


@app.post("/matches/{match_id}/cancel", response_model=Match)
def cancel_match(match_id: int):
    match = get_match(match_id)
    if match.status not in ["scheduled", "live"]:
        raise HTTPException(status_code=409, detail="Этот матч уже завершён или отменён")
    return save_match_change(match, {"status": "cancelled"}, "match.cancelled")


@app.post("/matches/{match_id}/correct-result", response_model=Match)
def correct_result(match_id: int, score: Score):
    match = get_match(match_id)
    if match.status != "finished":
        raise HTTPException(status_code=409, detail="Исправить можно только завершённый матч")
    if match.score == score:
        raise HTTPException(status_code=409, detail="Счёт не изменился")
    return save_match_change(match, {"score": score.model_dump()}, "match.result_corrected")


@app.get("/events")
def list_events():
    #адрес для проверки прототипа. Это ещё не отправка в Kafka.
    return EVENTS
