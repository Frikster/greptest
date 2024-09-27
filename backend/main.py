from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import requests
import re
from typing import List
from fastapi.middleware.cors import CORSMiddleware

# from fastapi import Depends
# import json

app = FastAPI()
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

REMOTE = "github"
GITHUB_API_URL = "https://api.github.com"

PROMPT = """
Investigate the codebase and write unit tests for the project for files where you have identified it would be important to have unit tests and they are missing.

Return ONLY a response in JSON format with the following schema:
{
    "fileChanges": [
        {
            "filePath": "path/to/file.test.ext",
            "newContent": "file.test.ext content with new content you have added"
        }
    ]
}

IT MUST BE RETURNED AS A VALID JSON IN THE FORMAT ABOVE - DO NOT RETURN ANY OTHER TEXT

Note that you CAN create new files. Therefore filePath can point to a file that does not exist.
Use your understanding of the codebase structure to determine where new files should be created.
You should however prefer to modify existing files if you find files that already have unit tests.
In such cases you should look for missing edge cases.

The project may use different technology stacks. Identify the stack used in the repository and use appropriate testing frameworks and libraries for writing the tests. For example:
- For a Next.js project using TypeScript, use Jest and React Testing Library.
- For a Python project, use unittest or pytest.
- For a Java project, use JUnit.

Do note that you can include multiple files and contents in your response.
"""

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

class BaseRequest(BaseModel):
    githubToken: str
    githubRepo: str
    githubBranch: str
    _validate_github_repo = validator('githubRepo', allow_reuse=True)(validate_github_repo)

class RepoIndexRequest(BaseRequest):
    apiKey: str

class QueryCodeRequest(BaseRequest):
    apiKey: str

class FileChange(BaseModel):
    filePath: str
    newContent: str

class ModifyRepoRequest(BaseRequest):
    newBranch: str
    commitMessage: str
    fileChanges: List[FileChange]

class CreatePRRequest(BaseRequest):
    headBranch: str
    title: str
    body: str

# class CombinedRequest(BaseModel):
#     query_request: QueryCodeRequest
#     modify_request: ModifyRepoRequest
#     create_pr_request: CreatePRRequest

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
                "content": PROMPT,
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
        "genius": True
        # TODO: use below three params?
        # "sessionId": request.sessionId,
        # "stream": True,
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
    url = f"{GITHUB_API_URL}/repos/{request.githubRepo}/git/refs/heads/{request.githubBranch}"
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
        "base": request.githubBranch
    }
    response = requests.post(
        url,
        headers=github_headers(request.githubToken),
        json=payload
    )

    if response.status_code != 201:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    return response.json()

# @app.post("/query-and-modify-repo-and-create-pr")
# async def query_and_modify_repo_and_create_pr(request: CombinedRequest):
#     # Call query_code and get the result
#     query_result = await query_code(request.query_request)

#     # Extract file changes from the query result
#     file_changes_str = query_result.message.get("fileChanges", [])  # TODO: add error handling
#     json_file_changes = json.loads(file_changes_str)
#     request.modify_request.fileChanges = [FileChange(**fc) for fc in json_file_changes]

#     # Call modify_repo with the updated modify_request
#     await modify_repo(request.modify_request)

#     # Call create_pr now that we have the new branch
#     create_pr_result = await create_pr(request.create_pr_request)

#     return create_pr_result


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)