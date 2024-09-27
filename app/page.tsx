'use client'
import { FormControl, FormLabel, Input, Button } from '@chakra-ui/react';
import { useState } from 'react';
import axios from 'axios';

export default function Page() {
  const [apiKey, setApiKey] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [githubRepo, setGithubRepo] = useState('');
  const [githubBranch, setGithubBranch] = useState('');
  const [newBranch, setNewBranch] = useState('');
  const [commitMessage, setCommitMessage] = useState('');
  const [prTitle, setPrTitle] = useState('');
  const [prBody, setPrBody] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      // Step 1: Query Code
      const queryResponse = await axios.post('http://localhost:8000/query-code', {
        apiKey,
        githubToken,
        githubRepo,
        githubBranch,
      });
      console.log(queryResponse);
      const queryData = queryResponse.data;
      const fileChanges = JSON.parse(queryData.message).fileChanges;
      console.log(fileChanges);

      console.log({
        githubToken,
        githubRepo,
        githubBranch,
        newBranch,
        commitMessage,
        fileChanges,
      })

      // Step 2: Modify Repo
      const modifyResponse = await axios.post('http://localhost:8000/modify-repo', {
        githubToken,
        githubRepo,
        githubBranch,
        newBranch,
        commitMessage,
        fileChanges,
      });
      console.log(modifyResponse);

      // Step 3: Create PR
      const prResponse = await axios.post('http://localhost:8000/create-pr', {
        githubToken,
        githubRepo,
        githubBranch,
        headBranch: newBranch,
        title: prTitle,
        body: prBody,
      });
      console.log(prResponse);

    } catch (error) {
      console.error('Error:', error);
    }
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
        <FormControl mt={4}>
          <FormLabel htmlFor="newBranch">New Branch:</FormLabel>
          <Input type="text" id="newBranch" name="newBranch" value={newBranch} onChange={(e) => setNewBranch(e.target.value)} />
        </FormControl>
        <FormControl mt={4}>
          <FormLabel htmlFor="commitMessage">Commit Message:</FormLabel>
          <Input type="text" id="commitMessage" name="commitMessage" value={commitMessage} onChange={(e) => setCommitMessage(e.target.value)} />
        </FormControl>
        <FormControl mt={4}>
          <FormLabel htmlFor="prTitle">PR Title:</FormLabel>
          <Input type="text" id="prTitle" name="prTitle" value={prTitle} onChange={(e) => setPrTitle(e.target.value)} />
        </FormControl>
        <FormControl mt={4}>
          <FormLabel htmlFor="prBody">PR Body:</FormLabel>
          <Input type="text" id="prBody" name="prBody" value={prBody} onChange={(e) => setPrBody(e.target.value)} />
        </FormControl>
        <Button type="submit" colorScheme="blue" mt={4}>
          Submit
        </Button>
      </form>
    </div>
  )
}