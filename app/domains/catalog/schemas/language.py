from pydantic import BaseModel, ConfigDict


class LanguageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    language_code: str
    language_name: str
    language_status: str
