import json
import sys

import requests


BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def checked_json(response):
    if not response.ok:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
    return response.json()


def main():
    with requests.Session() as client:
        login = checked_json(client.post(
            f"{BASE_URL}/auth/login",
            data={
                "username": "jorge@correo.ulpgc.es",
                "password": "supersecreta123",
            },
            timeout=TIMEOUT,
        ))
        client.headers.update({
            "Authorization": f"Bearer {login['access_token']}"
        })

        game = checked_json(client.post(
            f"{BASE_URL}/game/start/1", timeout=TIMEOUT,
        ))
        session_id = game["session_id"]
        questions = game["questions"]
        if not questions:
            raise RuntimeError("La partida no contiene preguntas.")
        question_id = questions[0]["id"]

        # El backend exige una respuesta por cada pregunta de la partida.
        answers = [{"question_id": question_id, "selected_index": 2}]
        answers.extend(
            {"question_id": question["id"], "selected_index": 2}
            for question in questions[1:]
        )
        result = checked_json(client.post(
            f"{BASE_URL}/game/submit/{session_id}",
            json={"answers": answers},
            timeout=TIMEOUT,
        ))
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, RuntimeError, KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
