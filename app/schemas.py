from pydantic import BaseModel

class APIDocumentationCreate(BaseModel):
    title: str
    section: str
    content: str
    example_code: dict

class APIDocumentationUpdate(BaseModel):
    title: str
    section: str
    content: str
    # example_code: str = None
    example_code: dict

class APIDocumentation(BaseModel):
    id: int
    title: str
    section: str
    content: str
    example_code: dict

    

class UserCreateRequest(BaseModel):
    name: str
    email: str
    password: str | None = None
    city: str | None = None

class SignInSchema(BaseModel):
    email: str
    password: str