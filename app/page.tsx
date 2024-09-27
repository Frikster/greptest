'use client'
import { FormControl, FormLabel, Input, Button } from '@chakra-ui/react';
import { useState } from 'react';

export default function Page() {
  const [apiKey, setApiKey] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [githubRepo, setGithubRepo] = useState('');
  const [githubBranch, setGithubBranch] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const response = await fetch('http://localhost:8000/index-repo', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        apiKey,
        githubToken,
        githubRepo,
        githubBranch,
      }),
    });
    const data = await response.json();
    console.log(data);
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <FormControl>
          <FormLabel htmlFor="apiKey">Greptile API Key:</FormLabel>
          <Input type="text" id="apiKey" name="apiKey" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
        </FormControl>
        <FormControl mt={4}>
          <FormLabel htmlFor="githubToken">GitHub Token:</FormLabel>
          <Input type="text" id="githubToken" name="githubToken" value={githubToken} onChange={(e) => setGithubToken(e.target.value)} />
        </FormControl>
        <FormControl mt={4}>
          <FormLabel htmlFor="githubRepo">GitHub Repo:</FormLabel>
          <Input type="text" id="githubRepo" name="githubRepo" value={githubRepo} onChange={(e) => setGithubRepo(e.target.value)} />
        </FormControl>
        <FormControl mt={4}>
          <FormLabel htmlFor="githubBranch">GitHub Branch:</FormLabel>
          <Input type="text" id="githubBranch" name="githubBranch" value={githubBranch} onChange={(e) => setGithubBranch(e.target.value)} />
        </FormControl>
        <Button type="submit" colorScheme="blue" mt={4}>
          Submit
        </Button>
      </form>
    </div>
  )
}