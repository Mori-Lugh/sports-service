from fastapi import FastAPI

# Создаём приложение нашего сервиса.
app = FastAPI(title="Sports Service")


# По этому адресу проверяем, работает ли сервер.
@app.get("/health")
def health():
    return {"status": "ok"}
