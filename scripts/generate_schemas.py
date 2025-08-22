# scripts/generate_schemas.py
import json
from pathlib import Path

# Импортируем все модели, для которых нужны схемы
from apps.gateway.rest.auth.dto import (
    ApiLoginResponse,
    ApiRegisterResponse,
    ApiValidateResponse,
)

# Определяем, где лежат модели и куда сохранять схемы
SCHEMAS_DIR = Path(__file__).parent.parent / "libs/domain/schemas/v1"
MODELS_TO_GENERATE = {
    "auth_login_response.v1.json": ApiLoginResponse,
    "auth_register_response.v1.json": ApiRegisterResponse,
    "auth_validate_response.v1.json": ApiValidateResponse,
}


def generate_schemas():
    """
    Генерирует и сохраняет JSON-схемы для Pydantic-моделей.
    """
    print(f"📁 Сохраняем схемы в: {SCHEMAS_DIR}")
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)

    for filename, model in MODELS_TO_GENERATE.items():
        schema_path = SCHEMAS_DIR / filename
        print(f"  -> Генерируем {filename}...")

        # Получаем схему из модели
        schema_content = model.model_json_schema()

        # Сохраняем в файл с красивым форматированием
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema_content, f, ensure_ascii=False, indent=2)
            f.write("\n")  # Добавляем перенос строки в конце файла

    print("✅ Все схемы успешно сгенерированы!")


if __name__ == "__main__":
    generate_schemas()
