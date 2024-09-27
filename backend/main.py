from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import requests
import re
from typing import List

app = FastAPI()

REMOTE = "github"
GITHUB_API_URL = "https://api.github.com"

def validate_github_repo(v: str) -> str:
    if not re.match(r'^[^/]+/[^/]+$', v):
        raise ValueError('githubRepo must be of the form "<username>/<repoName>"')
    return v

def github_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

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

class FileChange(BaseModel):
    filePath: str
    newContent: str

class ModifyRepoRequest(BaseModel):
    githubToken: str
    githubRepo: str
    baseBranch: str
    newBranch: str
    commitMessage: str
    fileChanges: List[FileChange]

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
        # TODO: use below three params?
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

@app.post("/modify-repo")
async def modify_repo(request: ModifyRepoRequest):
    # get base sha
    url = f"{GITHUB_API_URL}/repos/{request.githubRepo}/git/refs/heads/{request.baseBranch}"
    response = requests.get(url, headers=github_headers(request.githubToken))
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    base_sha = response.json()["object"]["sha"]

    # create branch
    url = f"{GITHUB_API_URL}/repos/{request.githubRepo}/git/refs"
    payload = {
        "ref": f"refs/heads/{request.newBranch}",
        "sha": base_sha
    }
    response = requests.post(url, headers=github_headers(request.githubToken), json=payload)
    if response.status_code != 201:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    # create tree with multiple file changes
    tree = []
    for fileChange in request.fileChanges:
        # Check if the file exists
        tree.append({
            "path": fileChange.filePath,
            "mode": "100644",
            "type": "blob",
            "content": fileChange.newContent
        })

    url = f"{GITHUB_API_URL}/repos/{request.githubRepo}/git/trees"
    payload = {
        "base_tree": base_sha,
        "tree": tree
    }
    response = requests.post(url, headers=github_headers(request.githubToken), json=payload)
    if response.status_code != 201:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    tree_sha = response.json()["sha"]

    # create commit
    url = f"{GITHUB_API_URL}/repos/{request.githubRepo}/git/commits"
    payload = {
        "message": request.commitMessage,
        "tree": tree_sha,
        "parents": [base_sha]
    }
    response = requests.post(url, headers=github_headers(request.githubToken), json=payload)
    if response.status_code != 201:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    commit_sha = response.json()["sha"]

    # update branch to point to new commit
    url = f"{GITHUB_API_URL}/repos/{request.githubRepo}/git/refs/heads/{request.newBranch}"
    payload = {
        "sha": commit_sha
    }
    response = requests.patch(url, headers=github_headers(request.githubToken), json=payload)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    return {"message": "Files updated and pushed to new branch successfully"}

@app.post("/create-pr")
async def create_pr(request: CreatePRRequest):
    url = f"https://api.github.com/repos/{request.githubRepo}/pulls"
    payload = {
        "title": request.title,
        "body": request.body,
        "head": request.headBranch,
        "base": request.baseBranch
    }
    response = requests.post(
        url,
        headers=github_headers(request.githubToken),
        json=payload
    )

    if response.status_code != 201:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    return response.json()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)