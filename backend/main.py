from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import requests
import re

app = FastAPI()

REMOTE = "github"

def validate_github_repo(v: str) -> str:
    if not re.match(r'^[^/]+/[^/]+$', v):
        raise ValueError('githubRepo must be of the form "<username>/<repoName>"')
    return v

class RepoIndexRequest(BaseModel):
    apiKey: str
    githubToken: str
    githubRepo: str
    githubBranch: str

    _validate_github_repo = validator('githubRepo', allow_reuse=True)(validate_github_repo)

class CreatePRRequest(BaseModel):
    githubToken: str
    githubRepo: str
    baseBranch: str
    headBranch: str
    title: str
    body: str

    _validate_github_repo = validator('githubRepo', allow_reuse=True)(validate_github_repo)

class QueryCodeRequest(BaseModel):
    apiKey: str
    githubToken: str
    githubRepo: str
    githubBranch: str
    query: str

    _validate_github_repo = validator('githubRepo', allow_reuse=True)(validate_github_repo)

@app.post("/index-repo")
async def index_repo(request: RepoIndexRequest):
    url = "https://api.greptile.com/v2/repositories"
    payload = {
        "remote": REMOTE,
        "repository": request.githubRepo,
        "branch": request.githubBranch,
        "reload": True,
        "notify": True
    }
    headers = {
        "Authorization": f"Bearer {request.apiKey}",
        "X-GitHub-Token": request.githubToken,
        "Content-Type": "application/json"
    }
    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    return response.json()

@app.post("/query-code")
async def query_code(request: QueryCodeRequest):
    url = "https://api.greptile.com/v2/query"
    payload = {
        "messages": [
            {
                "id": "1",
                "content": request.query,
                "role": "user"
            }
        ],
        "repositories": [
            {
                "remote": REMOTE,
                "branch": request.githubBranch,
                "repository": request.githubRepo
            }
        ],
        # TODO: use below three params
        # "sessionId": request.sessionId,
        # "stream": True,
        # "genius": True
    }
    headers = {
        "Authorization": f"Bearer {request.apiKey}",
        "X-GitHub-Token": request.githubToken,
        "Content-Type": "application/json"
    }
    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    return response.json()

@app.post("/create-pr")
async def create_pr(request: CreatePRRequest):
    url = f"https://api.github.com/repos/{request.githubRepo}/pulls"
    payload = {
        "title": request.title,
        "body": request.body,
        "head": request.headBranch,
        "base": request.baseBranch
    }
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {request.githubToken}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    if response.status_code != 201:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    return response.json()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)