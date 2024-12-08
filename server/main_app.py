from fastapi import FastAPI
from server import api_route, api_login

app = FastAPI()
app.include_router(api_route.api_router, prefix= "")
app.mount("/authorizate",api_login.app_login)

if __name__ == "__main__":


    import uvicorn
    uvicorn.run(app)